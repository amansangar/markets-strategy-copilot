from __future__ import annotations

from datetime import datetime, timezone
from math import exp, isfinite

import pandas as pd

from app.services.indicators import compute_indicators
from app.services.policy import evaluate_policy


def _signal_action(score: float, *, strong_threshold: float = 2.8, directional_threshold: float = 0.85) -> str:
    if score >= strong_threshold:
        return "STRONG_BUY"
    if score >= directional_threshold:
        return "BUY"
    if score <= -strong_threshold:
        return "STRONG_SELL"
    if score <= -directional_threshold:
        return "SELL"
    return "HOLD"


def build_news_snapshot(articles: list, now: datetime) -> dict:
    if not articles:
        return {"sentiment": 0.0, "relevance": 0.0, "articleCount": 0, "citations": []}

    weighted_scores: list[float] = []
    weighted_relevance: list[float] = []
    citations: list[str] = []
    for article in articles:
        published_at = article.published_at
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        age_hours = max((now - published_at).total_seconds() / 3600, 0.0)
        decay = exp(-age_hours / 72)
        score = article.raw_sentiment * article.relevance * decay
        weighted_scores.append(score)
        weighted_relevance.append(article.relevance * decay)
        citations.append(article.title)

    sentiment = sum(weighted_scores) / max(sum(weighted_relevance), 1e-9)
    relevance = sum(weighted_relevance) / len(weighted_relevance)
    return {
        "sentiment": round(sentiment, 4),
        "relevance": round(relevance, 4),
        "articleCount": len(articles),
        "citations": citations[:3],
    }


def detect_regime(row: pd.Series) -> str:
    if row["atr_pct"] > 0.025 and row["close"] < row["ema_50"]:
        return "RISK_OFF"
    if row["close"] > row["ema_21"] > row["ema_50"] and row["adx"] >= 20:
        return "TRENDING_BULL"
    if row["close"] < row["ema_21"] < row["ema_50"] and row["adx"] >= 20:
        return "TRENDING_BEAR"
    if row["adx"] < 18:
        return "RANGE_BOUND"
    return "MEAN_REVERTING"


def _reason(code: str, label: str, weight: float, detail: str) -> dict:
    return {"code": code, "label": label, "weight": round(weight, 4), "detail": detail}


def _risk(code: str, severity: str, message: str) -> dict:
    return {"code": code, "severity": severity, "message": message}


_BUY_ACTIONS = {"BUY", "STRONG_BUY"}
_SELL_ACTIONS = {"SELL", "STRONG_SELL"}
_DIRECTIONAL_ACTIONS = _BUY_ACTIONS | _SELL_ACTIONS


def _sanitized_trade_levels(action: str, current_price: float, atr: float) -> dict[str, float] | None:
    """Return trade levels only when they make directional sense.

    A BUY with a stop above the current price, or a SELL with a stop below it,
    is more dangerous than no level at all. In that case the signal engine
    should wait rather than publish unsafe guidance.
    """

    if action not in _DIRECTIONAL_ACTIONS:
        return None
    if not (isfinite(current_price) and current_price > 0 and isfinite(atr) and atr > 0):
        return None

    if action in _BUY_ACTIONS:
        stop = current_price - 1.5 * atr
        take_low = current_price + 2.0 * atr
        take_high = current_price + 3.0 * atr
        if stop < current_price < take_low <= take_high:
            return {"stop": stop, "takeLow": take_low, "takeHigh": take_high}
        return None

    stop = current_price + 1.5 * atr
    target_one = current_price - 2.0 * atr
    target_two = current_price - 3.0 * atr
    take_low = min(target_one, target_two)
    take_high = max(target_one, target_two)
    if take_low <= take_high < current_price < stop:
        return {"stop": stop, "takeLow": take_low, "takeHigh": take_high}
    return None


def _session_adjusted_freshness(
    *,
    asset_class: str,
    latest_time: datetime,
    now: datetime,
    raw_freshness: float,
) -> float:
    """Treat expected market closures differently from broken data feeds.

    Equities, ETFs, commodities, FX pairs, and indices do not print continuously
    through every weekend/overnight window. A Friday/previous-session bar can be
    the freshest legitimate bar, while crypto remains a 24/7 freshness check.
    """

    normalized_class = (asset_class or "").strip().lower()
    if normalized_class == "crypto":
        return raw_freshness

    if now.weekday() >= 5 and raw_freshness <= 72 * 60 * 60:
        return min(raw_freshness, 300.0)

    if latest_time.date() == now.date() and raw_freshness <= 16 * 60 * 60:
        return min(raw_freshness, 300.0)

    if now.weekday() < 5 and raw_freshness <= 20 * 60 * 60 and now.hour < 14:
        return min(raw_freshness, 300.0)

    return raw_freshness


def generate_signal(
    *,
    symbol_meta,
    intraday_bars: pd.DataFrame,
    daily_bars: pd.DataFrame,
    articles: list,
    mode: str,
    stale_override_seconds: float | None = None,
) -> dict:
    intraday = compute_indicators(intraday_bars)
    daily = compute_indicators(daily_bars)
    now = datetime.now(timezone.utc)

    if intraday.empty or daily.empty:
        return {
            "symbol": symbol_meta.symbol,
            "mode": mode,
            "timeframe": "5m",
            "action": "NO_SIGNAL",
            "confidence": 0.05,
            "regime": "RANGE_BOUND",
            "horizon": "intraday",
            "currentPrice": 0.0,
            "stopLoss": None,
            "takeProfitLow": None,
            "takeProfitHigh": None,
            "positionSizePct": 0.0,
            "dataFreshnessSeconds": 9_999.0,
            "reasonCodes": [
                _reason(
                    "DATA_QUALITY_NO_SIGNAL",
                    "No signal until market data loads",
                    0.0,
                    "Required market data is unavailable, so the research signal stays neutral instead of forcing a buy or sell view.",
                )
            ],
            "riskFlags": [_risk("DATA_MISSING", "high", "Required market data is not available.")],
            "policyBlockers": ["DATA_MISSING"],
            "indicatorSnapshot": {},
            "newsSnapshot": {"sentiment": 0.0, "relevance": 0.0, "articleCount": 0, "citations": []},
            "lastUpdated": now.isoformat(),
            "provenance": {"signalEngine": "deterministic-v1", "newsLayer": "offline-or-empty"},
        }

    latest = intraday.iloc[-1]
    latest_daily = daily.iloc[-1]
    freshness = stale_override_seconds
    latest_time = latest["time"].to_pydatetime()
    if latest_time.tzinfo is None:
        latest_time = latest_time.replace(tzinfo=timezone.utc)
    if freshness is None:
        freshness = max((now - latest_time).total_seconds(), 0.0)
    if mode == "demo" and stale_override_seconds is None:
        freshness = 45.0
    elif mode == "live":
        freshness = _session_adjusted_freshness(
            asset_class=symbol_meta.asset_class,
            latest_time=latest_time,
            now=now,
            raw_freshness=float(freshness),
        )

    news_snapshot = build_news_snapshot(articles, now)
    regime = detect_regime(latest_daily)

    score = 0.0
    reasons: list[dict] = []
    risk_flags: list[dict] = []

    if latest["close"] > latest["ema_21"] > latest["ema_50"]:
        score += 1.8
        reasons.append(_reason("TREND_STACK_BULL", "Bullish EMA stack", 1.8, "Price is above the 21 and 50 EMAs."))
    elif latest["close"] < latest["ema_21"] < latest["ema_50"]:
        score -= 1.8
        reasons.append(_reason("TREND_STACK_BEAR", "Bearish EMA stack", -1.8, "Price is below the 21 and 50 EMAs."))

    if latest_daily["close"] > latest_daily["ema_21"] > latest_daily["ema_50"]:
        score += 1.0
        reasons.append(_reason("DAILY_TREND_BULL", "Daily trend confirms upside", 1.0, "Daily price structure is above the 21 and 50 EMA trend filters."))
    elif latest_daily["close"] < latest_daily["ema_21"] < latest_daily["ema_50"]:
        score -= 1.0
        reasons.append(_reason("DAILY_TREND_BEAR", "Daily trend confirms downside", -1.0, "Daily price structure is below the 21 and 50 EMA trend filters."))

    if latest["macd_hist"] > 0 and latest["macd"] > latest["macd_signal"]:
        score += 1.1
        reasons.append(_reason("MACD_UP", "MACD confirmation", 1.1, "MACD histogram is positive and rising."))
    elif latest["macd_hist"] < 0 and latest["macd"] < latest["macd_signal"]:
        score -= 1.1
        reasons.append(_reason("MACD_DOWN", "MACD weakness", -1.1, "MACD histogram remains below its signal line."))

    if latest["plus_di"] > latest["minus_di"] and latest["adx"] >= 18:
        score += 0.45
        reasons.append(_reason("DMI_BULL", "DMI supports buyers", 0.45, "+DI is above -DI with enough trend strength to support an upside bias."))
    elif latest["minus_di"] > latest["plus_di"] and latest["adx"] >= 18:
        score -= 0.45
        reasons.append(_reason("DMI_BEAR", "DMI supports sellers", -0.45, "-DI is above +DI with enough trend strength to support a downside bias."))

    if latest.get("supertrend_direction", 0) == 1:
        score += 0.55
        reasons.append(_reason("SUPERTREND_BULL", "Supertrend bullish", 0.55, "Supertrend direction is positive on the active chart timeframe."))
    elif latest.get("supertrend_direction", 0) == -1:
        score -= 0.55
        reasons.append(_reason("SUPERTREND_BEAR", "Supertrend bearish", -0.55, "Supertrend direction is negative on the active chart timeframe."))

    if 52 <= latest["rsi"] <= 68:
        score += 0.8
        reasons.append(_reason("RSI_SUPPORTIVE", "RSI supportive", 0.8, "RSI is in a constructive trend-following band."))
    elif latest["rsi"] < 32:
        score += 0.4
        reasons.append(_reason("RSI_OVERSOLD", "Oversold bounce potential", 0.4, "RSI is oversold, supporting a mean-reversion response."))
    elif latest["rsi"] > 72:
        score -= 0.6
        reasons.append(_reason("RSI_OVERBOUGHT", "Overbought caution", -0.6, "RSI is elevated and adds exhaustion risk."))

    if latest["close"] <= latest["bb_lower"] and latest["rsi"] < 45:
        score += 0.45
        reasons.append(_reason("BOLLINGER_REVERSION_BUY", "Lower-band reversal setup", 0.45, "Price is near the lower Bollinger Band with soft momentum, supporting a bounce bias."))
    elif latest["close"] >= latest["bb_upper"] and latest["rsi"] > 55:
        score -= 0.45
        reasons.append(_reason("BOLLINGER_REVERSION_SELL", "Upper-band fade setup", -0.45, "Price is near the upper Bollinger Band with stretched momentum, supporting a pullback bias."))

    if latest["close"] > latest["vwap"]:
        score += 0.7
        reasons.append(_reason("VWAP_ABOVE", "Above VWAP", 0.7, "Price is holding above session VWAP."))
    else:
        score -= 0.7
        reasons.append(_reason("VWAP_BELOW", "Below VWAP", -0.7, "Price is trading below session VWAP."))

    volume_ratio = (latest["volume"] / latest["volume_ma_20"]) if latest["volume_ma_20"] else 1.0
    if volume_ratio > 1.4 and latest["close"] > latest["resistance_20"] * 0.998:
        score += 0.9
        reasons.append(_reason("BREAKOUT_VOLUME", "Breakout with volume", 0.9, "Volume confirms a move into resistance."))
    elif volume_ratio < 0.65:
        risk_flags.append(_risk("THIN_PARTICIPATION", "medium", "Participation is light versus the 20-bar volume average."))

    score += news_snapshot["sentiment"] * 1.25
    if news_snapshot["articleCount"]:
        reasons.append(
            _reason(
                "NEWS_CONTEXT",
                "News sentiment context",
                news_snapshot["sentiment"] * 1.25,
                f"Weighted headline sentiment is {news_snapshot['sentiment']:.2f} across {news_snapshot['articleCount']} items.",
            )
        )

    if regime == "RISK_OFF" and score > 0:
        score *= 0.65
        risk_flags.append(_risk("RISK_OFF_REGIME", "high", "Risk-off regime dampens long conviction."))
    elif regime == "RANGE_BOUND" and abs(score) > 2:
        score *= 0.85
        risk_flags.append(_risk("RANGE_CONFLICT", "medium", "Strong directional signals are less reliable in a range-bound regime."))

    stale_minutes = freshness / 60
    if freshness > 600:
        risk_flags.append(_risk("STALE_DATA", "high", "Price feed is stale, so directional confidence is heavily reduced."))
        score *= 0.25

    if abs(score) < 0.35:
        reasons.append(
            _reason(
                "MIXED_EVIDENCE_HOLD",
                "Mixed evidence",
                0.0,
                "Trend, momentum, price position, and news context are too balanced for a clean directional signal.",
            )
        )

    force_action: str | None = None
    if freshness > 1800:
        force_action = "NO_SIGNAL"
        reasons.append(
            _reason(
                "STALE_FEED_NO_SIGNAL",
                "Feed too stale for a signal",
                0.0,
                f"The latest price data is about {stale_minutes:.0f} minutes old, so the app avoids a directional call.",
            )
        )
    elif freshness > 600:
        force_action = "HOLD"
        reasons.append(
            _reason(
                "STALE_FEED_HOLD",
                "Feed stale, wait for refresh",
                0.0,
                f"The latest price data is about {stale_minutes:.0f} minutes old, so the safest decision-support action is HOLD.",
            )
        )

    action = force_action or _signal_action(score)

    current_price = float(latest["close"])
    atr = float(latest.get("atr") or 0.0)
    levels = _sanitized_trade_levels(action, current_price, atr)
    if action in _DIRECTIONAL_ACTIONS and levels is None:
        action = "HOLD"
        risk_flags.append(
            _risk(
                "LEVEL_SANITY_BLOCK",
                "high",
                "Stop and target levels could not be validated against the current price.",
            )
        )
        reasons.append(
            _reason(
                "LEVELS_UNAVAILABLE_HOLD",
                "Wait for valid trade levels",
                0.0,
                "The stop or target band was unavailable or invalid, so the app keeps the decision-support action at HOLD.",
            )
        )

    stop_loss = levels["stop"] if levels else None
    take_low = levels["takeLow"] if levels else None
    take_high = levels["takeHigh"] if levels else None
    atr_pct = float(latest.get("atr_pct") or 0.0)
    position_size = 0.0 if action in {"HOLD", "NO_SIGNAL"} else min(symbol_meta.risk_limit, 0.12 if atr_pct <= 0 else min(symbol_meta.risk_limit, 0.02 / max(atr_pct, 0.005)))

    policy_pass, blockers = evaluate_policy(
        asset_class=symbol_meta.asset_class,
        action=action,
        freshness_seconds=float(freshness),
        spread_bps=float(symbol_meta.avg_spread_bps),
        position_size_pct=float(position_size),
    )

    if blockers:
        risk_flags.append(_risk("POLICY_BLOCK", "high", f"Policy blocked directional action: {', '.join(blockers)}"))
        if action in {"STRONG_BUY", "BUY", "SELL", "STRONG_SELL"}:
            action = "HOLD"
            stop_loss = None
            take_low = None
            take_high = None
            position_size = 0.0
            reasons.append(
                _reason(
                    "POLICY_HOLD",
                    "Policy gate says wait",
                    0.0,
                    "A policy or data-quality gate blocked the directional action, so the visible decision-support action is HOLD.",
                )
            )

    confidence_penalty = (0.18 if blockers else 0.0) + (0.18 if freshness > 600 else 0.0)
    confidence = max(0.05, min(0.96, 0.42 + min(abs(score) / 6, 0.48) - confidence_penalty))
    if action == "NO_SIGNAL":
        confidence = min(confidence, 0.24)
    elif action == "HOLD":
        confidence = min(max(confidence, 0.35), 0.62)

    return {
        "symbol": symbol_meta.symbol,
        "mode": mode,
        "timeframe": "5m",
        "action": action,
        "confidence": round(confidence, 4),
        "regime": regime,
        "horizon": "swing" if daily.iloc[-1]["return_20d"] and abs(daily.iloc[-1]["return_20d"]) > 0.08 else "intraday",
        "currentPrice": round(current_price, 4),
        "stopLoss": round(float(stop_loss), 4) if stop_loss else None,
        "takeProfitLow": round(float(take_low), 4) if take_low else None,
        "takeProfitHigh": round(float(take_high), 4) if take_high else None,
        "positionSizePct": round(float(position_size), 4),
        "dataFreshnessSeconds": round(float(freshness), 2),
        "reasonCodes": reasons,
        "riskFlags": risk_flags,
        "policyBlockers": blockers,
        "indicatorSnapshot": {
            "rsi": round(float(latest["rsi"]), 2),
            "macd": round(float(latest["macd"]), 4),
            "macdSignal": round(float(latest["macd_signal"]), 4),
            "adx": round(float(latest["adx"]), 2),
            "atrPct": round(float(latest["atr_pct"]), 4),
            "vwap": round(float(latest["vwap"]), 4),
            "ema21": round(float(latest["ema_21"]), 4),
            "ema50": round(float(latest["ema_50"]), 4),
            "volumeRatio": round(float(volume_ratio), 2),
        },
        "newsSnapshot": news_snapshot,
        "lastUpdated": latest_time.isoformat(),
        "provenance": {"signalEngine": "deterministic-v1", "newsLayer": "server-side", "policyVersion": "1"},
    }
