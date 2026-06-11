from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from itertools import combinations

import pandas as pd
from sqlalchemy.orm import Session

from app.repository import bars_dataframe, get_symbol, list_alerts, list_symbols, news_for_symbol
from app.services.indicators import compute_indicators
from app.services.macro import macro_snapshot
from app.services.sec import filing_digest, filings_for_symbol


DEFAULT_SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "BTCUSD", "GLD"]


def strategy_builder_payload(session: Session, symbol: str, mode: str = "demo") -> dict:
    context = _indicator_context(session, symbol)
    rules = [
        {
            "name": "Trend continuation",
            "rule": "CLOSE > EMA50 AND MACD > MACD_SIGNAL AND RSI > 50 AND ADX > 18",
            "intent": "Pine-style long filter using trend, momentum, and regime strength.",
        },
        {
            "name": "Mean reversion bounce",
            "rule": "RSI < 35 AND CLOSE < BB_LOWER",
            "intent": "Oversold setup that waits for price outside the lower Bollinger Band.",
        },
        {
            "name": "Volume breakout",
            "rule": "CLOSE > RESISTANCE AND VOLUME_RATIO > 1.2 AND SENTIMENT >= 0",
            "intent": "Breakout candidate requiring participation and no negative news drag.",
        },
    ]
    return {
        "symbol": symbol,
        "mode": mode,
        "language": "Pine-lite deterministic rule builder",
        "limitations": [
            "This is not TradingView Pine Script. It supports a safe subset for local rule prototyping and demo use.",
            "Rules are evaluated on cached app data and do not place orders.",
            "Backtest timing still uses next-bar assumptions in the strategy tester.",
        ],
        "supportedFields": sorted(context["values"].keys()),
        "operators": [">", ">=", "<", "<=", "==", "AND"],
        "context": context,
        "templates": [{**rule, "evaluation": evaluate_strategy_rule(rule["rule"], context["values"])} for rule in rules],
    }


def evaluate_strategy_rule(rule: str, values: dict[str, float | str | None]) -> dict:
    clauses = [part.strip() for part in re.split(r"\s+AND\s+", rule.upper()) if part.strip()]
    results = []
    all_passed = bool(clauses)
    for clause in clauses:
        match = re.fullmatch(r"([A-Z_]+)\s*(>=|<=|==|>|<)\s*([A-Z_]+|-?\d+(?:\.\d+)?)", clause)
        if not match:
            all_passed = False
            results.append({"clause": clause, "passed": False, "detail": "Unsupported syntax. Use FIELD OP VALUE joined by AND."})
            continue
        left_key, operator, right_token = match.groups()
        left = values.get(left_key)
        right = values.get(right_token) if right_token in values else _to_float(right_token)
        passed = _compare(left, right, operator)
        all_passed = all_passed and passed
        results.append(
            {
                "clause": clause,
                "passed": passed,
                "left": _rounded(left),
                "right": _rounded(right),
                "detail": f"{left_key} {operator} {right_token}",
            }
        )
    return {
        "passed": all_passed,
        "matchedClauses": sum(1 for item in results if item["passed"]),
        "totalClauses": len(results),
        "confidenceHint": round(sum(1 for item in results if item["passed"]) / max(len(results), 1), 3),
        "conditions": results,
        "decisionUse": "Use as a scanner/backtest candidate only. The governed signal engine still decides BUY or SELL with confidence and risk flags.",
    }


def multi_chart_payload(session: Session, symbols: list[str] | None = None, timeframe: str = "1d") -> dict:
    symbols = _valid_symbols(session, symbols or DEFAULT_SYMBOLS)[:8]
    charts = []
    for symbol in symbols:
        frame = bars_dataframe(session, symbol, timeframe)
        if frame.empty:
            continue
        meta = get_symbol(session, symbol)
        tail = frame.tail(90).copy()
        first_close = float(tail["close"].iloc[0]) or 1.0
        latest = tail.iloc[-1]
        charts.append(
            {
                "symbol": symbol,
                "name": meta.name,
                "assetClass": meta.asset_class,
                "lastPrice": round(float(latest["close"]), 4),
                "changePct": round((float(latest["close"]) / first_close - 1) * 100, 2),
                "series": [
                    {
                        "time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
                        "close": round(float(row.close), 4),
                        "normalised": round((float(row.close) / first_close - 1) * 100, 3),
                    }
                    for row in tail.itertuples()
                ],
            }
        )
    return {
        "timeframe": timeframe,
        "layoutOptions": ["2x2", "3x2", "4-grid", "focus-plus-mini"],
        "activeLayout": "3x2" if len(charts) > 4 else "2x2",
        "charts": charts,
        "comparison": comparison_payload(session, symbols),
    }


def chart_workspace_payload(session: Session, symbol: str) -> dict:
    context = _indicator_context(session, symbol)
    values = context["values"]
    close = float(values.get("CLOSE") or 0)
    support = float(values.get("SUPPORT") or close * 0.97)
    resistance = float(values.get("RESISTANCE") or close * 1.03)
    atr = float(values.get("ATR") or max(close * 0.015, 1))
    return {
        "symbol": symbol,
        "savedLayouts": [
            {"name": "Guided demo", "timeframes": ["1d", "1h"], "indicators": ["EMA 21/50", "VWAP", "RSI", "MACD"]},
            {"name": "Breakout desk", "timeframes": ["15m", "1h", "1d"], "indicators": ["Volume MA", "ATR", "Support/Resistance"]},
            {"name": "Macro swing", "timeframes": ["4h", "1d"], "indicators": ["Ichimoku", "ADX/DMI", "Supertrend"]},
        ],
        "drawings": [
            {"kind": "support", "label": "20-bar support", "price": round(support, 4), "confidence": 0.78},
            {"kind": "resistance", "label": "20-bar resistance", "price": round(resistance, 4), "confidence": 0.8},
            {"kind": "trendline", "label": "Auto trendline", "from": round(close - 2 * atr, 4), "to": round(close, 4), "confidence": 0.66},
            {"kind": "fib", "label": "Auto Fibonacci zone", "levels": _fib_levels(support, resistance), "confidence": 0.62},
        ],
        "patterns": pattern_payload(session, symbol),
        "note": "Drawings are deterministic research overlays. They are not predictive guarantees.",
    }


def alert_builder_payload(session: Session) -> dict:
    existing = [
        {"id": alert.id, "symbol": alert.symbol, "name": alert.name, "kind": alert.kind, "enabled": alert.enabled, "rule": alert.rule_json}
        for alert in list_alerts(session)
    ]
    templates = [
        {
            "name": "Signal upgrade",
            "rule": {"when": "signal.action changes to BUY or STRONG_BUY", "cooldownMinutes": 45, "requiresFreshData": True},
            "deliveries": ["in-app", "browser"],
        },
        {
            "name": "Breakout confluence",
            "rule": {"when": "CLOSE > RESISTANCE AND VOLUME_RATIO > 1.3 AND ADX > 20", "cooldownMinutes": 60},
            "deliveries": ["in-app", "browser", "email-if-configured"],
        },
        {
            "name": "Provider outage",
            "rule": {"when": "provider.status in degraded,missing and source is required", "cooldownMinutes": 120},
            "deliveries": ["in-app"],
        },
        {
            "name": "Filing event risk",
            "rule": {"when": "new 8-K, 10-Q, or risk-marked filing appears", "cooldownMinutes": 240},
            "deliveries": ["in-app", "browser", "email-if-configured"],
        },
    ]
    return {
        "templates": templates,
        "existingAlerts": existing,
        "deliveryPolicy": {
            "browser": "enabled by default when the browser grants permission",
            "email": "disabled unless Resend and a safe recipient policy are configured",
            "webhook": "unavailable in this version; no broker/order execution hooks",
        },
    }


def market_replay_lab_payload(session: Session, symbol: str, cursor: int = 120) -> dict:
    frame = bars_dataframe(session, symbol, "1d")
    if frame.empty:
        return {"symbol": symbol, "cursor": cursor, "bars": [], "events": [], "signals": [], "warning": "No cached bars available."}
    cursor = min(max(cursor, 40), len(frame) - 1)
    visible = frame.iloc[: cursor + 1].tail(120)
    events = _events_for_symbol(session, symbol)
    cursor_time = frame.iloc[cursor]["time"].to_pydatetime().replace(tzinfo=timezone.utc)
    return {
        "symbol": symbol,
        "cursor": cursor,
        "cursorTime": cursor_time.isoformat(),
        "controls": {"speeds": ["1x", "5x", "15x"], "modes": ["bars-only", "bars-news-filings", "signal-debug"]},
        "bars": [
            {
                "time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
                "open": round(float(row.open), 4),
                "high": round(float(row.high), 4),
                "low": round(float(row.low), 4),
                "close": round(float(row.close), 4),
            }
            for row in visible.itertuples()
        ],
        "events": [event for event in events if datetime.fromisoformat(event["time"]) <= cursor_time][-12:],
        "signals": _replay_signals(frame.iloc[: cursor + 1]),
        "guardrail": "Replay only reveals events at or before the cursor, avoiding lookahead leakage.",
    }


def scanner_columns_payload(session: Session) -> dict:
    rows = []
    for symbol in _valid_symbols(session, None):
        context = _indicator_context(session, symbol)
        values = context["values"]
        technical_rank = _technical_rank(values)
        rows.append(
            {
                "symbol": symbol,
                "lastPrice": values.get("CLOSE"),
                "actionCandidate": _candidate_action(technical_rank),
                "technicalRank": technical_rank,
                "rsi": values.get("RSI"),
                "macdState": "bullish" if (values.get("MACD") or 0) > (values.get("MACD_SIGNAL") or 0) else "bearish",
                "vwapState": "above" if (values.get("CLOSE") or 0) > (values.get("VWAP") or 0) else "below",
                "volumeRatio": values.get("VOLUME_RATIO"),
                "whyMatched": _why_ranked(values, technical_rank),
            }
        )
    rows.sort(key=lambda item: item["technicalRank"], reverse=True)
    return {
        "availableColumns": [
            "symbol",
            "lastPrice",
            "actionCandidate",
            "technicalRank",
            "rsi",
            "macdState",
            "vwapState",
            "volumeRatio",
            "whyMatched",
        ],
        "defaultColumns": ["symbol", "actionCandidate", "technicalRank", "rsi", "macdState", "vwapState", "whyMatched"],
        "savedPresets": [
            {"name": "Momentum desk", "columns": ["symbol", "technicalRank", "macdState", "volumeRatio"], "filter": "technicalRank >= 65"},
            {"name": "Mean reversion watch", "columns": ["symbol", "rsi", "vwapState"], "filter": "RSI < 40"},
        ],
        "rankedOpportunities": rows[:12],
    }


def comparison_payload(session: Session, symbols: list[str] | None = None) -> dict:
    symbols = _valid_symbols(session, symbols or ["SPY", "QQQ", "AAPL", "BTCUSD", "GLD"])[:8]
    closes = {}
    normalised = []
    for symbol in symbols:
        frame = bars_dataframe(session, symbol, "1d").tail(90)
        if frame.empty:
            continue
        series = frame[["time", "close"]].copy()
        first = float(series["close"].iloc[0]) or 1.0
        closes[symbol] = series["close"].pct_change().fillna(0).reset_index(drop=True)
        normalised.append(
            {
                "symbol": symbol,
                "points": [
                    {
                        "time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
                        "returnPct": round((float(row.close) / first - 1) * 100, 3),
                    }
                    for row in series.itertuples()
                ],
            }
        )
    matrix = []
    if closes:
        frame = pd.DataFrame(closes)
        corr = frame.corr().fillna(0)
        for left, right in combinations(corr.columns, 2):
            matrix.append({"pair": f"{left}/{right}", "correlation": round(float(corr.loc[left, right]), 3)})
    return {"symbols": symbols, "normalisedReturns": normalised, "correlations": sorted(matrix, key=lambda item: abs(item["correlation"]), reverse=True)}


def events_calendar_payload(session: Session, mode: str = "demo") -> dict:
    now = datetime.now(timezone.utc)
    events = [
        {"time": (now + timedelta(days=1)).isoformat(), "kind": "macro", "title": "FRED macro refresh window", "impact": "medium", "source": "FRED"},
        {"time": (now + timedelta(days=3)).isoformat(), "kind": "economic", "title": "Inflation and rates watchlist review", "impact": "high", "source": "macro regime"},
    ]
    for symbol in ["SPY", "AAPL", "MSFT", "NVDA", "TSLA", "BTCUSD"]:
        events.extend(_events_for_symbol(session, symbol, future=True)[:3])
    events.sort(key=lambda item: item["time"])
    return {
        "mode": mode,
        "events": events[:30],
        "macroRegime": macro_snapshot(session, mode),
        "caveat": "Earnings dates are demo/local calendar markers unless a live fundamentals provider supplies confirmed dates.",
    }


def tear_sheet_payload(session: Session, symbol: str, mode: str = "demo") -> dict:
    meta = get_symbol(session, symbol)
    frame = compute_indicators(bars_dataframe(session, symbol, "1d"))
    context = _indicator_context(session, symbol)
    filings = filings_for_symbol(session, symbol)
    news = news_for_symbol(session, symbol, limit=5)
    if frame.empty:
        metrics = {}
    else:
        tail = frame.tail(252)
        close = float(tail["close"].iloc[-1])
        high = float(tail["high"].max())
        low = float(tail["low"].min())
        returns = tail["close"].pct_change().dropna()
        volatility = float(returns.std() * math.sqrt(252)) if not returns.empty else 0.0
        metrics = {
            "lastPrice": round(close, 4),
            "range52w": {"low": round(low, 4), "high": round(high, 4)},
            "distanceFromHighPct": round((close / high - 1) * 100, 2) if high else 0,
            "return90dPct": round((close / float(tail["close"].iloc[max(len(tail) - 90, 0)]) - 1) * 100, 2) if len(tail) > 5 else 0,
            "realisedVolatility": round(volatility, 3),
            "averageVolume20": round(float(tail["volume"].tail(20).mean()), 2),
        }
    return {
        "symbol": symbol,
        "mode": mode,
        "profile": {
            "name": meta.name,
            "assetClass": meta.asset_class,
            "venue": meta.venue,
            "currency": meta.currency,
            "description": meta.description,
            "spreadBps": meta.avg_spread_bps,
        },
        "marketMetrics": metrics,
        "fundamentalProxy": _fundamental_proxy(meta.asset_class, metrics),
        "indicatorContext": context,
        "macroSensitivity": _macro_sensitivity(meta.asset_class, macro_snapshot(session, mode)),
        "filings": filing_digest(filings),
        "news": [{"title": item.title, "source": item.source, "sentiment": round(item.raw_sentiment, 3), "relevance": round(item.relevance, 3)} for item in news],
        "caveat": "Fundamental fields are local/provider-derived research context and should be verified before investment use.",
    }


def pattern_payload(session: Session, symbol: str) -> dict:
    daily = compute_indicators(bars_dataframe(session, symbol, "1d"))
    if daily.empty:
        return {"symbol": symbol, "patterns": [], "confluence": [], "levels": []}
    latest = daily.iloc[-1]
    support = float(latest.get("support_20") or latest["low"])
    resistance = float(latest.get("resistance_20") or latest["high"])
    close = float(latest["close"])
    trend = "uptrend" if close > float(latest.get("ema_50") or close) else "downtrend"
    proximity = min(abs(close - support), abs(resistance - close)) / max(close, 1)
    patterns = [
        {"name": "Auto support/resistance box", "state": "active", "confidence": 0.78, "detail": f"Price is {proximity * 100:.2f}% from the nearest 20-bar level."},
        {"name": "Trendline slope", "state": trend, "confidence": 0.67, "detail": "Derived from price versus EMA50 and recent swing structure."},
        {"name": "Volatility squeeze", "state": "watch" if float(latest.get("atr_pct") or 0) < 0.018 else "inactive", "confidence": 0.58, "detail": "Uses ATR percent as a simple squeeze proxy."},
    ]
    confluence = [
        {"timeframe": "1d", "bias": "bullish" if close > float(latest.get("vwap") or close) else "bearish", "reason": "daily price versus VWAP"},
        {"timeframe": "4h", "bias": "neutral", "reason": "cached demo confluence example, no order execution"},
        {"timeframe": "15m", "bias": "bullish" if float(latest.get("rsi") or 50) >= 50 else "bearish", "reason": "momentum band proxy"},
    ]
    return {
        "symbol": symbol,
        "levels": [
            {"kind": "support", "price": round(support, 4)},
            {"kind": "resistance", "price": round(resistance, 4)},
        ],
        "patterns": patterns,
        "confluence": confluence,
        "warning": "Automated patterns are explainability aids, not guaranteed chart-pattern detection.",
    }


def ranked_opportunities_payload(session: Session) -> dict:
    scanner = scanner_columns_payload(session)
    return {
        "ranked": scanner["rankedOpportunities"],
        "methodology": [
            "Ranks are deterministic from trend, RSI band, VWAP, MACD, ADX, and participation.",
            "News, filings, and macro context are shown as reasons but do not override risk gates.",
            "This list is for research triage and does not imply execution advice.",
        ],
    }


def _indicator_context(session: Session, symbol: str) -> dict:
    daily = compute_indicators(bars_dataframe(session, symbol, "1d"))
    articles = news_for_symbol(session, symbol)
    if daily.empty:
        return {"asOf": datetime.now(timezone.utc).isoformat(), "values": {}, "snapshot": {}}
    latest = daily.iloc[-1]
    volume_ma = float(latest.get("volume_ma_20") or latest["volume"] or 1)
    sentiment = sum(item.raw_sentiment * item.relevance for item in articles) / max(sum(item.relevance for item in articles), 1e-9) if articles else 0.0
    values = {
        "CLOSE": _float(latest.get("close")),
        "PRICE": _float(latest.get("close")),
        "RSI": _float(latest.get("rsi")),
        "MACD": _float(latest.get("macd")),
        "MACD_SIGNAL": _float(latest.get("macd_signal")),
        "ADX": _float(latest.get("adx")),
        "VWAP": _float(latest.get("vwap")),
        "EMA21": _float(latest.get("ema_21")),
        "EMA50": _float(latest.get("ema_50")),
        "BB_LOWER": _float(latest.get("bb_lower")),
        "BB_UPPER": _float(latest.get("bb_upper")),
        "ATR": _float(latest.get("atr")),
        "SUPPORT": _float(latest.get("support_20")),
        "RESISTANCE": _float(latest.get("resistance_20")),
        "VOLUME_RATIO": round(float(latest.get("volume") or 0) / max(volume_ma, 1), 4),
        "SENTIMENT": round(sentiment, 4),
    }
    return {
        "asOf": latest["time"].to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
        "values": values,
        "snapshot": {
            "trend": "above EMA50" if (values["CLOSE"] or 0) > (values["EMA50"] or 0) else "below EMA50",
            "momentum": "positive MACD" if (values["MACD"] or 0) > (values["MACD_SIGNAL"] or 0) else "negative MACD",
            "participation": "above average" if (values["VOLUME_RATIO"] or 0) > 1 else "below average",
        },
    }


def _events_for_symbol(session: Session, symbol: str, future: bool = False) -> list[dict]:
    events = []
    now = datetime.now(timezone.utc)
    for article in news_for_symbol(session, symbol, limit=5):
        published = article.published_at.replace(tzinfo=timezone.utc)
        events.append({"time": published.isoformat(), "kind": "news", "title": article.title, "impact": "medium", "source": article.source, "symbol": symbol})
    for filing in filings_for_symbol(session, symbol, limit=5):
        events.append({"time": filing["filedAt"], "kind": "filing", "title": f"{symbol} {filing['filingType']} filing", "impact": filing["riskLevel"], "source": "SEC", "symbol": symbol})
    if future and symbol not in {"BTCUSD", "ETHUSD", "SOLUSD", "EURUSD", "GBPUSD", "USDJPY"}:
        events.append({"time": (now + timedelta(days=7)).isoformat(), "kind": "earnings", "title": f"{symbol} earnings review window", "impact": "medium", "source": "local calendar", "symbol": symbol})
    return sorted(events, key=lambda item: item["time"])


def _replay_signals(frame: pd.DataFrame) -> list[dict]:
    enriched = compute_indicators(frame)
    signals = []
    for index, row in enriched.tail(30).iterrows():
        score = 0.0
        score += 1.0 if row.get("close", 0) >= row.get("ema_21", 0) else -1.0
        score += 0.6 if row.get("macd", 0) >= row.get("macd_signal", 0) else -0.6
        score += 0.4 if row.get("rsi", 50) >= 50 else -0.4
        if row.get("rsi", 50) > 76:
            score -= 0.5
        elif row.get("rsi", 50) < 24:
            score += 0.5
        action = "STRONG_BUY" if score >= 1.6 else ("BUY" if score >= 0.45 else ("STRONG_SELL" if score <= -1.6 else ("SELL" if score <= -0.45 else "HOLD")))
        signals.append({"index": int(index), "time": row["time"].to_pydatetime().replace(tzinfo=timezone.utc).isoformat(), "action": action, "confidence": 0.68 if abs(score) >= 1.6 else 0.58})
    return signals


def _technical_rank(values: dict) -> float:
    score = 50.0
    if (values.get("CLOSE") or 0) > (values.get("EMA50") or 0):
        score += 12
    else:
        score -= 8
    if (values.get("MACD") or 0) > (values.get("MACD_SIGNAL") or 0):
        score += 10
    if 48 <= (values.get("RSI") or 50) <= 68:
        score += 9
    elif (values.get("RSI") or 50) > 75:
        score -= 8
    if (values.get("CLOSE") or 0) > (values.get("VWAP") or 0):
        score += 7
    if (values.get("ADX") or 0) > 20:
        score += 6
    if (values.get("VOLUME_RATIO") or 1) > 1.25:
        score += 5
    return round(max(0, min(100, score)), 2)


def _candidate_action(rank: float) -> str:
    if rank >= 78:
        return "STRONG_BUY_WATCH"
    if rank >= 62:
        return "BUY_WATCH"
    if rank <= 32:
        return "SELL_WATCH"
    return "NEUTRAL_WATCH"


def _why_ranked(values: dict, rank: float) -> str:
    reasons = []
    if (values.get("CLOSE") or 0) > (values.get("EMA50") or 0):
        reasons.append("above EMA50")
    if (values.get("MACD") or 0) > (values.get("MACD_SIGNAL") or 0):
        reasons.append("MACD bullish")
    if (values.get("VOLUME_RATIO") or 1) > 1.25:
        reasons.append("volume expansion")
    if not reasons:
        reasons.append("balanced technical score")
    return f"Rank {rank:.1f}: " + ", ".join(reasons[:3])


def _fundamental_proxy(asset_class: str, metrics: dict) -> dict:
    if asset_class in {"crypto", "fx"}:
        return {"status": "not_applicable", "items": [{"label": "Fundamentals", "value": "Use liquidity, volatility, macro and news context for this asset class."}]}
    return {
        "status": "provider_or_demo_proxy",
        "items": [
            {"label": "Quality", "value": "Requires FMP/EODHD/Twelve Data for verified fundamentals"},
            {"label": "Volatility proxy", "value": metrics.get("realisedVolatility")},
            {"label": "Liquidity proxy", "value": metrics.get("averageVolume20")},
        ],
    }


def _macro_sensitivity(asset_class: str, macro: dict) -> dict:
    mapping = {
        "equity": "Sensitive to risk appetite, rates, earnings revisions, and credit stress.",
        "etf": "Sensitive to index composition, rates, liquidity, and macro regime.",
        "crypto": "Highly sensitive to liquidity, risk appetite, and regulatory/news shocks.",
        "fx": "Sensitive to rate differentials, growth surprises, and central-bank communication.",
        "commodity": "Sensitive to inflation, USD, inventory cycles, and geopolitics.",
    }
    return {"regime": macro["regime"], "summary": mapping.get(asset_class, "Sensitive to macro conditions and liquidity."), "macroSummary": macro["summary"]}


def _fib_levels(low: float, high: float) -> list[dict]:
    spread = high - low
    return [{"level": level, "price": round(high - spread * level, 4)} for level in [0.236, 0.382, 0.5, 0.618, 0.786]]


def _valid_symbols(session: Session, requested: list[str] | None) -> list[str]:
    available = {item.symbol for item in list_symbols(session)}
    if requested:
        symbols = [symbol.upper() for symbol in requested if symbol.upper() in available]
        if symbols:
            return symbols
    return sorted(available)


def _compare(left, right, operator: str) -> bool:
    if left is None or right is None:
        return False
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    if operator == "==":
        return left == right
    return False


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _float(value) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _rounded(value):
    if isinstance(value, float):
        return round(value, 4)
    return value
