from __future__ import annotations

import asyncio
import math
import re
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import BacktestRun, Bar, NewsArticle, SecFiling, SignalRecord
from app.repository import (
    bars_dataframe,
    get_symbol,
    list_alerts,
    list_reports,
    list_symbols,
    latest_signal_record,
    news_for_symbol,
    recent_audit,
    record_audit_event,
    save_backtest,
    save_report,
    save_signal,
    toggle_alert,
)
from app.schemas import (
    AlertResponse,
    AssetDetailResponse,
    BacktestRequest,
    BacktestResponse,
    DashboardResponse,
    ReportRequest,
    ReportResponse,
    ScannerResponse,
    SystemStatusResponse,
    PortfolioResponse,
    WorkspaceResponse,
)
from app.services.backtest import PRESETS, run_backtest
from app.services.indicators import compute_indicators
from app.services.insights import (
    backtest_robustness,
    data_quality_score,
    portfolio_risk_heatmap,
    provider_fallback_plan,
    replay_scenarios,
    signal_waterfall,
    system_readiness,
)
from app.services.live_refresh import provider_budget_snapshot, schedule_live_symbol_refresh
from app.services.macro import macro_signal_contribution, macro_snapshot
from app.services.observability import observability_status
from app.services.portfolio import portfolio_snapshot
from app.services.providers import provider_badges, provider_health, provider_matrix
from app.services.provider_checks import run_provider_checks
from app.services.pro_features import pro_terminal_payload
from app.services.sec import filing_digest, filing_event_flags, filings_for_symbol
from app.services.alerts import alert_center
from app.services.signals import generate_signal
from app.services.signal_diff import signal_diff
from app.services.terminal_features import (
    alert_builder_payload,
    chart_workspace_payload,
    comparison_payload,
    evaluate_strategy_rule,
    events_calendar_payload,
    market_replay_lab_payload,
    multi_chart_payload,
    pattern_payload,
    ranked_opportunities_payload,
    scanner_columns_payload,
    strategy_builder_payload,
    tear_sheet_payload,
)
from app.services.workspace import workspace_snapshot


router = APIRouter(prefix="/api/v1")
_DASHBOARD_CACHE_SECONDS = 300.0
_LIVE_DASHBOARD_CACHE_SECONDS = 60.0
_dashboard_cache: dict[tuple[str, str], tuple[datetime, dict]] = {}
_ASSET_CACHE_SECONDS = 180.0
_asset_cache: dict[tuple[str, str], tuple[datetime, dict]] = {}
_SCANNER_CACHE_SECONDS = 180.0
_LIVE_SCANNER_CACHE_SECONDS = 180.0
_scanner_cache: dict[tuple[str, str | None, float], tuple[datetime, dict]] = {}
_BACKTEST_CACHE_SECONDS = 300.0
_backtest_cache: dict[tuple, tuple[datetime, dict]] = {}
_QUALITY_CACHE_SECONDS = 180.0
_quality_cache: dict[str, tuple[datetime, dict]] = {}


def _public_report_path(raw_path: str) -> str:
    filename = Path(raw_path).name or "investment-note.pdf"
    return f"artefacts/exports/{filename}"


def _report_download_url(report_id: str) -> str:
    return f"/api/v1/reports/{report_id}/download"


def _report_response(report) -> dict:
    return {
        "reportId": report.id,
        "symbol": report.symbol,
        "mode": report.mode,
        "path": _public_report_path(report.path),
        "downloadUrl": _report_download_url(report.id),
        "createdAt": report.created_at,
    }


def _visible_reports(raw_reports: list) -> list:
    timestamped = [
        report
        for report in raw_reports
        if re.search(r"-investment-note-\d{8}-\d{6}\.pdf$", Path(report.path).name, re.IGNORECASE)
    ]
    return timestamped if timestamped else raw_reports
_STRATEGY_MATRIX_CACHE_SECONDS = 300.0
_strategy_matrix_cache: dict[tuple[str, str], tuple[datetime, dict]] = {}
_PRO_TERMINAL_CACHE_SECONDS = 180.0
_pro_terminal_cache: dict[str, tuple[datetime, dict]] = {}
_CHART_CACHE_SECONDS = 300.0
_chart_cache: dict[tuple, tuple[datetime, dict]] = {}


def _chart_payload(
    symbol: str,
    timeframe: str,
    raw_bars,
    markers: list[dict] | None = None,
    history_bars=None,
) -> dict:
    marker_signature = tuple((item.get("time"), item.get("position"), item.get("text")) for item in (markers or [])[:20])
    if not raw_bars.empty:
        latest = raw_bars.iloc[-1]
        history_signature = None
        if history_bars is not None and not history_bars.empty:
            latest_history = history_bars.iloc[-1]
            history_signature = (
                len(history_bars),
                str(latest_history["time"]),
                round(float(latest_history["close"]), 8),
            )
        cache_key = (
            symbol,
            timeframe,
            len(raw_bars),
            str(latest["time"]),
            round(float(latest["close"]), 8),
            marker_signature,
            history_signature,
        )
        cached = _chart_cache.get(cache_key)
        if cached:
            cached_at, payload = cached
            if (datetime.now(timezone.utc) - cached_at).total_seconds() <= _CHART_CACHE_SECONDS:
                return deepcopy(payload)
            _chart_cache.pop(cache_key, None)
    else:
        cache_key = None

    window = 360 if timeframe == "5m" else 760
    enriched = compute_indicators(raw_bars.tail(window)).tail(320 if timeframe == "5m" else 620)
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": [
            {
                "time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
                "open": round(float(row.open), 4),
                "high": round(float(row.high), 4),
                "low": round(float(row.low), 4),
                "close": round(float(row.close), 4),
                "volume": round(float(row.volume), 2),
            }
            for row in enriched.itertuples()
        ],
        "overlays": {
            "ema21": [{"time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(), "value": round(float(row.ema_21), 4) if row.ema_21 == row.ema_21 else None} for row in enriched.itertuples()],
            "ema50": [{"time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(), "value": round(float(row.ema_50), 4) if row.ema_50 == row.ema_50 else None} for row in enriched.itertuples()],
            "vwap": [{"time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(), "value": round(float(row.vwap), 4) if row.vwap == row.vwap else None} for row in enriched.itertuples()],
            "bbUpper": [{"time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(), "value": round(float(row.bb_upper), 4) if row.bb_upper == row.bb_upper else None} for row in enriched.itertuples()],
            "bbLower": [{"time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(), "value": round(float(row.bb_lower), 4) if row.bb_lower == row.bb_lower else None} for row in enriched.itertuples()],
        },
        "oscillators": {
            "rsi": [{"time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(), "value": round(float(row.rsi), 2) if row.rsi == row.rsi else None} for row in enriched.itertuples()],
            "macd": [{"time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(), "value": round(float(row.macd), 4) if row.macd == row.macd else None, "signal": round(float(row.macd_signal), 4) if row.macd_signal == row.macd_signal else None} for row in enriched.itertuples()],
        },
        "markers": markers or [],
        "attribution": "Charts by TradingView Lightweight Charts",
        "attributionUrl": "https://www.tradingview.com/lightweight-charts/",
    }
    if history_bars is not None and not history_bars.empty:
        payload["history"] = _chart_payload(symbol, "1d", history_bars.tail(760), markers=markers)
    if cache_key is not None:
        _chart_cache[cache_key] = (datetime.now(timezone.utc), deepcopy(payload))
    return payload


def _system_status(mode: str) -> dict:
    health = provider_health(mode)
    technical_only = any(item["name"] in {"openai", "openai-enrichment"} and item["status"] in {"offline", "disabled"} for item in health)
    return {
        "mode": mode,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "technicalOnlyMode": technical_only,
        "health": health,
        "providers": provider_matrix(mode),
        "observability": observability_status(),
        "message": "Live providers are configured; use Check connections for a fresh verification." if mode == "live" and not technical_only else "Demo mode is reproducible and live degradations are surfaced honestly.",
    }


def _cached_dashboard(mode: str, symbol: str) -> dict | None:
    cached = _dashboard_cache.get((mode, symbol))
    if not cached:
        return None
    cached_at, payload = cached
    ttl = _LIVE_DASHBOARD_CACHE_SECONDS if mode == "live" else _DASHBOARD_CACHE_SECONDS
    if (datetime.now(timezone.utc) - cached_at).total_seconds() > ttl:
        _dashboard_cache.pop((mode, symbol), None)
        return None
    return _sanitize_visible_actions(deepcopy(payload))


def _store_dashboard_cache(mode: str, symbol: str, payload: dict) -> None:
    _dashboard_cache[(mode, symbol)] = (datetime.now(timezone.utc), deepcopy(payload))


def _cached_asset_detail(mode: str, symbol: str) -> dict | None:
    cached = _asset_cache.get((mode, symbol))
    if not cached:
        return None
    cached_at, payload = cached
    ttl = _LIVE_DASHBOARD_CACHE_SECONDS if mode == "live" else _ASSET_CACHE_SECONDS
    if (datetime.now(timezone.utc) - cached_at).total_seconds() > ttl:
        _asset_cache.pop((mode, symbol), None)
        return None
    return _sanitize_visible_actions(deepcopy(payload))


def _store_asset_cache(mode: str, symbol: str, payload: dict) -> None:
    if mode in {"demo", "live"}:
        _asset_cache[(mode, symbol)] = (datetime.now(timezone.utc), deepcopy(payload))


def _cached_scanner(mode: str, action: str | None, min_confidence: float) -> dict | None:
    cached = _scanner_cache.get((mode, action, min_confidence))
    if not cached:
        return None
    created_at, payload = cached
    age = (datetime.now(timezone.utc) - created_at).total_seconds()
    ttl = _LIVE_SCANNER_CACHE_SECONDS if mode == "live" else _SCANNER_CACHE_SECONDS
    if age > ttl:
        return None
    return _sanitize_visible_actions(deepcopy(payload))


def _store_scanner_cache(mode: str, action: str | None, min_confidence: float, payload: dict) -> None:
    _scanner_cache[(mode, action, min_confidence)] = (datetime.now(timezone.utc), deepcopy(payload))


def _fast_watchlist_signal(intraday) -> dict:
    closes = intraday["close"].tail(50)
    volumes = intraday["volume"].tail(50)
    return _fast_watchlist_signal_from_values([float(value) for value in closes], [float(value) for value in volumes])


def _fast_watchlist_signal_from_values(closes: list[float], volumes: list[float]) -> dict:
    last = float(closes[-1])
    prev = float(closes[-2])
    sma20 = sum(closes[-20:]) / min(len(closes), 20)
    sma50 = sum(closes[-50:]) / min(len(closes), 50)
    momentum = (last / prev) - 1.0
    volume_tail = volumes[-20:] if volumes else [1.0]
    volume_ratio = float((volumes[-1] if volumes else 1.0) / max(sum(volume_tail) / len(volume_tail), 1.0))

    score = 0.0
    if last > sma20 > sma50:
        score += 1.35
    elif last < sma20 < sma50:
        score -= 1.35
    if momentum > 0.004:
        score += 0.75
    elif momentum < -0.004:
        score -= 0.75
    if volume_ratio > 1.25:
        score += 0.35 if momentum >= 0 else -0.35

    if score >= 2.0:
        action = "STRONG_BUY"
    elif score >= 0.55:
        action = "BUY"
    elif score <= -2.0:
        action = "STRONG_SELL"
    elif score <= -0.55:
        action = "SELL"
    else:
        action = "HOLD"

    if last > sma20 > sma50:
        regime = "TRENDING_BULL"
    elif last < sma20 < sma50:
        regime = "TRENDING_BEAR"
    else:
        regime = "RANGE_BOUND"

    return {
        "action": action,
        "confidence": round(max(0.18, min(0.9, 0.42 + abs(score) * 0.18)), 4),
        "regime": regime,
        "sentiment": 0.0,
        "volumeRatio": volume_ratio,
    }


def _all_intraday_bar_rows(session: Session) -> dict[str, list[Bar]]:
    grouped: dict[str, list[Bar]] = {}
    for listed in list_symbols(session):
        rows = list(
            session.scalars(
                select(Bar)
                .where(Bar.symbol == listed.symbol, Bar.timeframe == "5m")
                .order_by(Bar.time.desc())
                .limit(120)
            )
        )
        rows.reverse()
        if rows:
            grouped[listed.symbol] = rows
    return grouped


def _dashboard_signal_context(session: Session, symbol: str, mode: str) -> tuple[object, dict, list, object]:
    meta = get_symbol(session, symbol)
    intraday = bars_dataframe(session, symbol, "5m", limit=420)
    news = news_for_symbol(session, symbol)
    record = latest_signal_record(session, symbol)
    if mode != "live" and record and record.payload_json:
        signal = _sanitize_visible_actions(deepcopy(record.payload_json))
        signal["mode"] = mode
        health = provider_health(mode)
        signal["dataQuality"] = data_quality_score(signal, health, mode)
        signal["waterfall"] = signal_waterfall(signal)
        return meta, signal, news, intraday

    _, signal, news, intraday, _daily = _signal_and_context(session, symbol, mode)
    return meta, signal, news, intraday


def _finite_float(value: object, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback
    return numeric if math.isfinite(numeric) else fallback


def _fast_scanner_row(session: Session, listed) -> dict:
    intraday = bars_dataframe(session, listed.symbol, "5m", limit=160)
    fast_signal = _fast_watchlist_signal(intraday)
    enriched = compute_indicators(intraday).iloc[-1]
    articles = news_for_symbol(session, listed.symbol)
    relevance_total = sum(max(float(item.relevance), 0.0) for item in articles)
    sentiment = (
        sum(float(item.raw_sentiment) * max(float(item.relevance), 0.0) for item in articles) / relevance_total
        if relevance_total
        else 0.0
    )
    rsi = _finite_float(enriched.get("rsi"), 50.0)
    macd = _finite_float(enriched.get("macd"))
    macd_signal = _finite_float(enriched.get("macd_signal"))
    vwap = _finite_float(enriched.get("vwap"), _finite_float(enriched.get("close")))
    close = _finite_float(enriched.get("close"))
    adx = _finite_float(enriched.get("adx"))
    volume_ratio = _finite_float(fast_signal["volumeRatio"], 1.0)

    why: list[str] = []
    if fast_signal["regime"] == "TRENDING_BULL":
        why.append("Price structure is above short and medium trend filters")
    elif fast_signal["regime"] == "TRENDING_BEAR":
        why.append("Price structure is below short and medium trend filters")
    else:
        why.append("Range-bound structure keeps conviction moderated")
    why.append("MACD bullish" if macd > macd_signal else "MACD bearish")
    why.append("Above VWAP" if close > vwap else "Below VWAP")
    if volume_ratio > 1.4:
        why.append("Volume spike confirmation")
    if abs(sentiment) > 0.15:
        why.append("News sentiment context")

    return {
        "symbol": listed.symbol,
        "action": fast_signal["action"],
        "confidence": fast_signal["confidence"],
        "regime": fast_signal["regime"],
        "rsi": round(rsi, 2),
        "macdState": "bullish" if macd > macd_signal else "bearish",
        "priceVsVwap": "above" if close > vwap else "below",
        "adx": round(adx, 2),
        "volumeSpike": volume_ratio > 1.4,
        "sentiment": round(sentiment, 4),
        "whyThisAppeared": ", ".join(why[:3]),
    }


def _scanner_row_from_cached_rows(session: Session, listed, rows: list[Bar]) -> dict | None:
    if len(rows) < 2:
        return None
    recent = rows[-120:]
    closes = [float(row.close) for row in recent]
    highs = [float(row.high) for row in recent]
    lows = [float(row.low) for row in recent]
    volumes = [float(row.volume) for row in recent]
    fast_signal = _fast_watchlist_signal_from_values(closes, volumes)
    record = latest_signal_record(session, listed.symbol)
    signal_payload = record.payload_json if record and record.payload_json else {}
    news_snapshot = signal_payload.get("newsSnapshot") if isinstance(signal_payload, dict) else {}
    sentiment = _finite_float(news_snapshot.get("sentiment") if isinstance(news_snapshot, dict) else None, 0.0)

    rsi = _quick_rsi(closes)
    macd, macd_signal = _quick_macd(closes)
    vwap = _quick_vwap(closes, volumes)
    close = closes[-1]
    adx = _quick_adx(highs, lows, closes)
    volume_ratio = _finite_float(fast_signal["volumeRatio"], 1.0)

    why: list[str] = []
    if fast_signal["regime"] == "TRENDING_BULL":
        why.append("Price is above short and medium trend filters")
    elif fast_signal["regime"] == "TRENDING_BEAR":
        why.append("Price is below short and medium trend filters")
    else:
        why.append("Range-bound structure keeps conviction moderated")
    why.append("MACD bullish" if macd > macd_signal else "MACD bearish")
    why.append("Above VWAP" if close > vwap else "Below VWAP")

    return {
        "symbol": listed.symbol,
        "action": fast_signal["action"],
        "confidence": fast_signal["confidence"],
        "regime": fast_signal["regime"],
        "rsi": round(rsi, 2),
        "macdState": "bullish" if macd > macd_signal else "bearish",
        "priceVsVwap": "above" if close > vwap else "below",
        "adx": round(adx, 2),
        "volumeSpike": volume_ratio > 1.4,
        "sentiment": round(sentiment, 4),
        "whyThisAppeared": ", ".join(why[:3]),
    }


def _quick_rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) <= period:
        return 50.0
    deltas = [closes[index] - closes[index - 1] for index in range(len(closes) - period, len(closes))]
    gains = [max(delta, 0.0) for delta in deltas]
    losses = [abs(min(delta, 0.0)) for delta in deltas]
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    avg_gain = sum(gains) / period
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _quick_ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1)
    ema = values[0]
    for value in values[1:]:
        ema = value * alpha + ema * (1 - alpha)
    return ema


def _quick_macd(closes: list[float]) -> tuple[float, float]:
    macd_series: list[float] = []
    for index in range(max(1, len(closes) - 35), len(closes) + 1):
        window = closes[:index]
        macd_series.append(_quick_ema(window, 12) - _quick_ema(window, 26))
    return macd_series[-1], _quick_ema(macd_series, 9)


def _quick_vwap(closes: list[float], volumes: list[float]) -> float:
    window_closes = closes[-78:]
    window_volumes = volumes[-78:]
    total_volume = sum(window_volumes)
    if total_volume <= 0:
        return window_closes[-1]
    return sum(price * volume for price, volume in zip(window_closes, window_volumes, strict=False)) / total_volume


def _quick_adx(highs: list[float], lows: list[float], closes: list[float]) -> float:
    window_high = max(highs[-14:])
    window_low = min(lows[-14:])
    close = max(abs(closes[-1]), 1.0)
    return min(60.0, max(5.0, ((window_high - window_low) / close) * 100.0))


def _backtest_key(request: BacktestRequest) -> tuple:
    return (
        request.symbol,
        request.timeframe,
        request.preset,
        round(float(request.feesBps), 6),
        round(float(request.spreadBps), 6),
        round(float(request.slippageBps), 6),
        bool(request.longShort),
        request.ablation,
    )


def _cached_backtest(request: BacktestRequest) -> dict | None:
    cached = _backtest_cache.get(_backtest_key(request))
    if not cached:
        return None
    cached_at, payload = cached
    if (datetime.now(timezone.utc) - cached_at).total_seconds() > _BACKTEST_CACHE_SECONDS:
        _backtest_cache.pop(_backtest_key(request), None)
        return None
    return deepcopy(payload)


def _store_backtest_cache(request: BacktestRequest, payload: dict) -> None:
    _backtest_cache[_backtest_key(request)] = (datetime.now(timezone.utc), deepcopy(payload))


def _cached_quality(mode: str) -> dict | None:
    cached = _quality_cache.get(mode)
    if not cached:
        return None
    cached_at, payload = cached
    if (datetime.now(timezone.utc) - cached_at).total_seconds() > _QUALITY_CACHE_SECONDS:
        _quality_cache.pop(mode, None)
        return None
    return deepcopy(payload)


def _store_quality_cache(mode: str, payload: dict) -> None:
    _quality_cache[mode] = (datetime.now(timezone.utc), deepcopy(payload))


def _cached_strategy_matrix(mode: str, symbol: str) -> dict | None:
    cached = _strategy_matrix_cache.get((mode, symbol))
    if not cached:
        return None
    cached_at, payload = cached
    if (datetime.now(timezone.utc) - cached_at).total_seconds() > _STRATEGY_MATRIX_CACHE_SECONDS:
        _strategy_matrix_cache.pop((mode, symbol), None)
        return None
    return deepcopy(payload)


def _store_strategy_matrix(mode: str, symbol: str, payload: dict) -> None:
    _strategy_matrix_cache[(mode, symbol)] = (datetime.now(timezone.utc), deepcopy(payload))


def _cached_pro_terminal(mode: str) -> dict | None:
    cached = _pro_terminal_cache.get(mode)
    if not cached:
        return None
    cached_at, payload = cached
    if (datetime.now(timezone.utc) - cached_at).total_seconds() > _PRO_TERMINAL_CACHE_SECONDS:
        _pro_terminal_cache.pop(mode, None)
        return None
    return deepcopy(payload)


def _store_pro_terminal(mode: str, payload: dict) -> None:
    _pro_terminal_cache[mode] = (datetime.now(timezone.utc), deepcopy(payload))


def _payload_directional_score(payload: dict | None) -> float:
    if not isinstance(payload, dict):
        return 0.0
    score = 0.0
    for reason in payload.get("reasonCodes", []) or []:
        if isinstance(reason, dict):
            score += _finite_float(reason.get("weight"))
    snapshot = payload.get("indicatorSnapshot", {}) or {}
    current_price = _finite_float(payload.get("currentPrice"))
    ema21 = _finite_float(snapshot.get("ema21"))
    ema50 = _finite_float(snapshot.get("ema50"))
    macd = _finite_float(snapshot.get("macd"))
    macd_signal = _finite_float(snapshot.get("macdSignal"))
    vwap = _finite_float(snapshot.get("vwap"))
    if current_price and ema21 and ema50:
        score += 0.5 if current_price >= ema21 >= ema50 else -0.5
    if macd or macd_signal:
        score += 0.3 if macd >= macd_signal else -0.3
    if current_price and vwap:
        score += 0.2 if current_price >= vwap else -0.2
    news = payload.get("newsSnapshot", {}) or {}
    score += _finite_float(news.get("sentiment")) * 0.75
    return score


def _visible_signal_action(action: object, payload: dict | None = None) -> str:
    allowed = {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL", "NO_SIGNAL"}
    action_text = str(action or "")
    if action_text in allowed:
        return action_text
    score = _payload_directional_score(payload)
    if score >= 2.4:
        return "STRONG_BUY"
    if score >= 0.65:
        return "BUY"
    if score <= -2.4:
        return "STRONG_SELL"
    if score <= -0.65:
        return "SELL"
    return "HOLD"


def _sanitize_visible_actions(payload):
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if key in {"action", "signal"} and isinstance(value, str):
                sanitized[key] = _visible_signal_action(value, payload)
            else:
                sanitized[key] = _sanitize_visible_actions(value)
        return sanitized
    if isinstance(payload, list):
        return [_sanitize_visible_actions(item) for item in payload]
    return payload


def _default_backtest_request(symbol: str) -> BacktestRequest:
    return BacktestRequest(
        symbol=symbol,
        timeframe="1d",
        preset="Mean Reversion",
        feesBps=2.0,
        spreadBps=2.0,
        slippageBps=1.0,
        longShort=False,
        ablation="technical_news_tca",
    )


def _adapt_cached_dashboard_for_live(session: Session, symbol: str, cached: dict) -> dict:
    payload = deepcopy(cached)
    health = provider_health("live")
    payload["mode"] = "live"
    payload["connectionSummary"] = "Live provider status active; warmed research view reused for fast display"
    payload["health"] = health
    payload["providerBadges"] = provider_badges("live")
    payload["readiness"] = system_readiness(session, "live")
    payload["fallbackPlan"] = provider_fallback_plan("live")
    if payload.get("signal"):
        payload["signal"]["dataQuality"] = data_quality_score(payload["signal"], health, "live")
        payload["signal"]["waterfall"] = signal_waterfall(payload["signal"])
        payload["signal"].setdefault("provenance", {})["liveDisplay"] = "Fast live dashboard adapted from warmed deterministic research payload; provider health is live-mode aware."
    payload = _sanitize_visible_actions(payload)
    _store_dashboard_cache("live", symbol, payload)
    return payload


def _quick_live_dashboard(symbol: str, session: Session) -> dict:
    meta, signal, news, intraday = _dashboard_signal_context(session, symbol, "live")
    daily_history = bars_dataframe(session, symbol, "1d")
    macro = macro_snapshot(session, "live")
    portfolio = portfolio_snapshot(session, "live")
    symbols = list_symbols(session)
    rows = []
    strongest_buy = "None"
    strongest_sell = "None"
    buy_score = -1.0
    sell_score = -1.0

    grouped_intraday = _all_intraday_bar_rows(session)

    for listed in symbols:
        if listed.symbol == symbol:
            last = intraday.iloc[-1]
            prev = intraday.iloc[-2]
        else:
            listed_intraday_rows = grouped_intraday.get(listed.symbol)
            if not listed_intraday_rows or len(listed_intraday_rows) < 2:
                continue
            last = listed_intraday_rows[-1]
            prev = listed_intraday_rows[-2]
        if listed.symbol == symbol:
            row_action = signal["action"]
            row_confidence = signal["confidence"]
            row_regime = signal["regime"]
            row_sentiment = signal["newsSnapshot"]["sentiment"]
            row_volume_ratio = signal["indicatorSnapshot"]["volumeRatio"]
        else:
            record = latest_signal_record(session, listed.symbol)
            closes = [float(row.close) for row in listed_intraday_rows[-50:]]
            volumes = [float(row.volume) for row in listed_intraday_rows[-50:]]
            fast_signal = _fast_watchlist_signal_from_values(closes, volumes)
            row_action = _visible_signal_action(record.action if record else fast_signal["action"])
            row_confidence = record.confidence if record else fast_signal["confidence"]
            row_regime = record.regime if record else fast_signal["regime"]
            row_sentiment = fast_signal["sentiment"]
            row_volume_ratio = fast_signal["volumeRatio"]

        row = {
            "symbol": listed.symbol,
            "name": listed.name,
            "lastPrice": round(float(last["close"] if hasattr(last, "__getitem__") else last.close), 4),
            "changePct": round(float((last["close"] if hasattr(last, "__getitem__") else last.close) / (prev["close"] if hasattr(prev, "__getitem__") else prev.close) - 1), 4),
            "signal": row_action,
            "confidence": round(float(row_confidence), 2),
            "regime": row_regime,
            "sentiment": round(float(row_sentiment), 4),
            "volumeNote": "Volume spike" if row_volume_ratio > 1.4 else "Normal liquidity",
            "assetClass": listed.asset_class,
        }
        rows.append(row)
        if row_action in {"BUY", "STRONG_BUY"} and row_confidence > buy_score:
            strongest_buy = listed.symbol
            buy_score = row_confidence
        if row_action in {"SELL", "STRONG_SELL"} and row_confidence > sell_score:
            strongest_sell = listed.symbol
            sell_score = row_confidence

    health = provider_health("live")
    backtest = _cached_backtest(_default_backtest_request(symbol))
    backtest_summary = backtest["metrics"] if backtest else {
        "status": "not precomputed",
        "note": "Run Strategy Tester for full live-session metrics. Dashboard skips heavy backtest recomputation for faster live loading.",
    }

    payload = {
        "mode": "live",
        "trackedAssets": len(rows),
        "alertCount": len(list_alerts(session)),
        "strongestBuy": strongest_buy,
        "strongestSell": strongest_sell,
        "marketRegimeSummary": f"{sum(1 for row in rows if row['regime'] == 'TRENDING_BULL')} bullish, {sum(1 for row in rows if row['regime'] == 'RISK_OFF')} risk-off",
        "connectionSummary": "Fast live-status dashboard; provider health and freshness shown below",
        "health": health,
        "providerBadges": provider_badges("live"),
        "macro": macro,
        "portfolioSummary": portfolio["summary"],
        "watchlist": sorted(rows, key=lambda item: item["confidence"], reverse=True),
        "chart": _chart_payload(symbol, "5m", intraday, history_bars=daily_history),
        "signal": signal,
        "news": [
            {
                "title": item.title,
                "source": item.source,
                "publishedAt": item.published_at.replace(tzinfo=timezone.utc).isoformat(),
                "url": item.url,
                "sentiment": item.raw_sentiment,
                "relevance": item.relevance,
            }
            for item in news
        ],
        "audit": [
            {
                "createdAt": event.created_at.replace(tzinfo=timezone.utc).isoformat(),
                "action": _visible_signal_action(event.action),
                "confidence": event.confidence,
                "policyPass": event.policy_pass,
                "reasonCodes": event.reason_codes_json,
                "riskFlags": event.risk_flags_json,
            }
            for event in recent_audit(session, symbol)
        ],
        "backtestSummary": backtest_summary,
        "signalDiff": signal_diff(session, symbol),
        "readiness": system_readiness(session, "live"),
        "fallbackPlan": provider_fallback_plan("live"),
    }
    payload = _sanitize_visible_actions(payload)
    _store_dashboard_cache("live", symbol, payload)
    return payload


def _signal_and_context(
    session: Session,
    symbol: str,
    mode: str,
    *,
    persist_audit: bool = True,
) -> tuple[object, dict, list, object, object]:
    meta = get_symbol(session, symbol)
    intraday = bars_dataframe(session, symbol, "5m", limit=420)
    daily = bars_dataframe(session, symbol, "1d")
    news = news_for_symbol(session, symbol)
    intraday_window = intraday.tail(280)
    daily_window = daily.tail(260)
    signal = generate_signal(
        symbol_meta=meta,
        intraday_bars=intraday_window,
        daily_bars=daily_window,
        articles=news,
        mode=mode,
    )
    macro = macro_snapshot(session, mode)
    macro_reason = macro_signal_contribution(macro)
    signal["reasonCodes"].append(macro_reason)
    signal["provenance"]["macro"] = "FRED/default deterministic macro regime overlay"
    filing_flags = filing_event_flags(filings_for_symbol(session, symbol))
    if filing_flags:
        signal["riskFlags"].extend(filing_flags)
        signal["provenance"]["filings"] = "SEC EDGAR/demo filing event risk overlay"
    health = provider_health(mode)
    signal["dataQuality"] = data_quality_score(signal, health, mode)
    signal["waterfall"] = signal_waterfall(signal)
    if persist_audit:
        save_signal(session, signal)
        record_audit_event(
            session,
            symbol=symbol,
            event_type="signal",
            mode=mode,
            action=signal["action"],
            confidence=signal["confidence"],
            reason_codes=signal["reasonCodes"],
            indicator_values=signal["indicatorSnapshot"],
            headlines=[{"title": item.title, "url": item.url, "source": item.source} for item in news],
            policy_pass=not signal["policyBlockers"],
            risk_flags=signal["riskFlags"],
            freshness_seconds=signal["dataFreshnessSeconds"],
            provenance=signal["provenance"],
        )
    return meta, signal, news, intraday_window, daily_window


@router.get("/system/status", response_model=SystemStatusResponse)
def system_status(mode: str = Query(default="demo", pattern="^(demo|live)$")) -> dict:
    return _system_status(mode)


@router.get("/providers/status")
def providers_status(mode: str = Query(default="demo", pattern="^(demo|live)$")) -> dict:
    return {"mode": mode, "providers": provider_matrix(mode), "observability": observability_status(), "fallbackPlan": provider_fallback_plan(mode)}


@router.get("/providers/failover-timeline")
def providers_failover_timeline(mode: str = Query(default="demo", pattern="^(demo|live)$")) -> dict:
    providers = {row["name"]: row for row in provider_matrix(mode)}
    plan = provider_fallback_plan(mode)
    generated_at = datetime.now(timezone.utc).isoformat()
    events: list[dict] = [
        {
            "time": generated_at,
            "kind": "mode",
            "status": "active",
            "title": f"{mode.title()} mode selected",
            "detail": "Demo is used first on a fresh browser session; Live remains an explicit opt-in with honest fallback states.",
        }
    ]

    for group in plan:
        primary = group["providers"][0]
        primary_status = primary["status"]
        if primary_status in {"healthy", "configured"}:
            events.append(
                {
                    "time": generated_at,
                    "kind": "primary",
                    "status": primary_status,
                    "title": f"{group['category']}: {primary['label']} primary",
                    "detail": primary["detail"],
                }
            )
            continue

        fallback = next((item for item in group["providers"][1:] if item["status"] in {"healthy", "configured", "degraded"}), None)
        events.append(
            {
                "time": generated_at,
                "kind": "fallback",
                "status": primary_status,
                "title": f"{group['category']}: primary degraded",
                "detail": f"{primary['label']} is {primary_status}. "
                + (f"Next usable source: {fallback['label']}." if fallback else "No configured fallback provider is currently usable; the frontend keeps Live selected and labels any local fallback clearly."),
            }
        )

    critical = []
    for name in ("polygon", "newsapi"):
        status = providers.get(name, {}).get("status")
        if status in {"offline", "degraded"}:
            critical.append(name)

    return {
        "mode": mode,
        "generatedAt": generated_at,
        "criticalFallbackLikely": bool(critical),
        "criticalProviders": critical,
        "events": events,
        "policy": "Critical live API failures are shown to the user; Live stays selected while any local fallback data is clearly labelled and retried.",
    }


@router.get("/providers/checks")
async def providers_checks() -> dict:
    return await run_provider_checks()


@router.get("/providers/budget")
def providers_budget() -> dict:
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "budgets": provider_budget_snapshot(),
        "policy": "External provider refreshes are throttled and cached so live mode stays usable without burning free-tier limits.",
    }


@router.get("/macro/regime")
def macro_regime(mode: str = Query(default="demo", pattern="^(demo|live)$"), session: Session = Depends(get_session)) -> dict:
    return macro_snapshot(session, mode)


@router.get("/system/readiness")
def readiness(mode: str = Query(default="demo", pattern="^(demo|live)$"), session: Session = Depends(get_session)) -> dict:
    return system_readiness(session, mode)


@router.get("/system/setup-guide")
def setup_guide(mode: str = Query(default="demo", pattern="^(demo|live)$"), session: Session = Depends(get_session)) -> dict:
    symbols = list_symbols(session)
    reports = list_reports(session)
    alerts = list_alerts(session)
    providers = provider_matrix(mode)
    readiness = system_readiness(session, mode)
    required_live = [row for row in providers if row["name"] in {"polygon", "newsapi", "openai"}]
    required_ready = all(row["status"] in {"healthy", "configured", "degraded"} for row in required_live)

    return {
        "mode": mode,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "headline": "Live-first, demo-safe setup",
        "summary": "The app starts in Live mode, then visibly uses safe demo-data fallbacks if critical APIs or internet access fail.",
        "checks": [
            {"label": "Backend API", "status": "ready", "detail": "This setup guide was served by FastAPI, so the API is reachable."},
            {"label": "Database and demo seed", "status": "ready" if len(symbols) >= 4 else "attention", "detail": f"{len(symbols)} instrument(s) are available."},
            {"label": "Live provider keys", "status": "ready" if required_ready else "attention", "detail": "Core live providers are configured or degraded honestly; missing keys never appear in the browser."},
            {"label": "PDF exports", "status": "ready" if reports else "attention", "detail": f"{len(reports)} report export(s) are recorded."},
            {"label": "Alerts", "status": "ready" if alerts else "attention", "detail": f"{len(alerts)} explainable alert rule(s) are available."},
            {"label": "System readiness", "status": readiness["status"], "detail": f"Readiness score {readiness['score']}/100."},
        ],
        "tutorial": [
            {"step": 1, "title": "Start on Dashboard", "detail": "Demo mode opens first for a safe, repeatable walkthrough. Switch to Live only when you want provider-backed refreshes and fallback banners."},
            {"step": 2, "title": "Open a signal", "detail": "Use the watchlist or scanner to open an asset and inspect reasons, risk flags, filings, news, and the signal-change panel."},
            {"step": 3, "title": "Prove no fake performance", "detail": "Run Strategy Tester and compare gross/net metrics, TCA costs, drawdown, and walk-forward windows."},
            {"step": 4, "title": "Check system health", "detail": "Use Settings and this Setup page to verify provider status, failover order, and release safety without exposing secrets."},
            {"step": 5, "title": "Export a note", "detail": "Generate a PDF investment note from Reports for a clean research summary."},
        ],
        "commands": [
            {"label": "Start backend", "command": "npm run dev:api"},
            {"label": "Start frontend", "command": "npm run dev:web"},
            {"label": "Run checks", "command": "npm run check"},
            {"label": "Package release", "command": "npm run package:release"},
        ],
        "routes": [
            {"route": "/", "label": "Dashboard", "purpose": "Live-first command centre and fallback banner."},
            {"route": "/quality", "label": "Signal Quality", "purpose": "Signal distribution, confidence bands, risk reasons, and audit coverage."},
            {"route": "/settings", "label": "Settings", "purpose": "Provider matrix and failover timeline."},
            {"route": "/setup", "label": "Setup Guide", "purpose": "Beginner-friendly setup, tutorial, and command reference."},
        ],
    }


@router.get("/signals/quality")
def signal_quality(mode: str = Query(default="demo", pattern="^(demo|live)$"), session: Session = Depends(get_session)) -> dict:
    cached = _cached_quality(mode)
    if cached:
        return cached

    rows: list[dict] = []
    action_counter: Counter[str] = Counter()
    risk_counter: Counter[str] = Counter()
    blocker_counter: Counter[str] = Counter()
    confidence_values: list[float] = []
    data_quality_values: list[float] = []
    audit_covered = 0
    health = provider_health(mode)
    provider_penalty = sum(10 if item["status"] == "offline" else 5 if item["status"] == "degraded" else 0 for item in health)

    for listed in list_symbols(session):
        try:
            latest_record = latest_signal_record(session, listed.symbol)
            intraday = bars_dataframe(session, listed.symbol, "5m", limit=160)
            fast_signal = _fast_watchlist_signal(intraday)
            signal = _sanitize_visible_actions(latest_record.payload_json) if latest_record and latest_record.payload_json else {}
            action = _visible_signal_action(signal.get("action") or fast_signal["action"])
            confidence = float(signal.get("confidence") or fast_signal["confidence"])
            data_quality = float(signal.get("dataQuality", {}).get("score") or max(45, 92 - provider_penalty))
            audits = recent_audit(session, listed.symbol, limit=1)
            if audits:
                audit_covered += 1
            action_counter[action] += 1
            confidence_values.append(confidence)
            data_quality_values.append(data_quality)
            for flag in signal.get("riskFlags", []):
                risk_counter[flag.get("code", "risk_flag")] += 1
            for blocker in signal.get("policyBlockers", []):
                blocker_counter[blocker] += 1
            reason_codes = signal.get("reasonCodes") or [
                {
                    "code": "FAST_TECHNICAL_SUMMARY",
                    "label": "Fast technical summary",
                    "weight": 0.0,
                    "detail": "Quality dashboard reused the fast watchlist signal to avoid expensive full-pipeline recomputation.",
                }
            ]
            rows.append(
                {
                    "symbol": listed.symbol,
                    "assetClass": listed.asset_class,
                    "action": action,
                    "confidence": round(confidence, 4),
                    "dataQuality": round(data_quality, 2),
                    "regime": str(signal.get("regime") or fast_signal["regime"]),
                    "freshnessSeconds": signal.get("dataFreshnessSeconds"),
                    "riskFlags": signal.get("riskFlags", []),
                    "policyBlockers": signal.get("policyBlockers", []),
                    "topReasons": reason_codes[:3],
                    "auditCovered": bool(audits),
                }
            )
        except Exception as exc:  # noqa: BLE001 - quality dashboard should report partial failures.
            rows.append(
                {
                    "symbol": listed.symbol,
                    "assetClass": listed.asset_class,
                    "action": "NO_SIGNAL",
                    "confidence": 0.05,
                    "dataQuality": 0,
                    "regime": "RISK_OFF",
                    "freshnessSeconds": None,
                    "riskFlags": [{"code": "QUALITY_PIPELINE_ERROR", "severity": "high", "message": str(exc)}],
                    "policyBlockers": ["quality pipeline unavailable"],
                    "topReasons": [],
                    "auditCovered": False,
                }
            )
            action_counter["NO_SIGNAL"] += 1
            blocker_counter["quality pipeline unavailable"] += 1

    total = len(rows)
    avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
    avg_quality = sum(data_quality_values) / len(data_quality_values) if data_quality_values else 0.0
    hold_back_reasons = [
        {"label": label, "count": count}
        for label, count in (risk_counter + blocker_counter).most_common(8)
    ]
    if not hold_back_reasons:
        hold_back_reasons = [{"label": "No active blockers in current signal set", "count": 0}]

    payload = {
        "mode": mode,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "totalSignals": total,
            "averageConfidence": round(avg_confidence, 4),
            "averageDataQuality": round(avg_quality, 2),
            "auditCoveragePct": round((audit_covered / total) * 100, 2) if total else 0,
            "directionalPct": round((sum(action_counter.get(action, 0) for action in ("STRONG_BUY", "BUY", "SELL", "STRONG_SELL")) / total) * 100, 2) if total else 0,
            "holdPct": round((sum(action_counter.get(action, 0) for action in ("HOLD", "NO_SIGNAL")) / total) * 100, 2) if total else 0,
        },
        "actionDistribution": [{"action": action, "count": action_counter.get(action, 0)} for action in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL", "NO_SIGNAL")],
        "holdBackReasons": hold_back_reasons,
        "qualityBands": [
            {"label": "High confidence", "count": sum(1 for row in rows if row["confidence"] >= 0.7)},
            {"label": "Medium confidence", "count": sum(1 for row in rows if 0.45 <= row["confidence"] < 0.7)},
            {"label": "Low confidence", "count": sum(1 for row in rows if row["confidence"] < 0.45)},
            {"label": "Data-quality watch", "count": sum(1 for row in rows if row["dataQuality"] < 75)},
        ],
        "rows": sorted(rows, key=lambda item: (item["dataQuality"], item["confidence"]), reverse=True),
        "caveat": "This dashboard is evidence and governance, not a promise of future returns. Signals remain deterministic, confidence-scored, and risk-gated, including HOLD and NO SIGNAL when evidence is weak or stale.",
    }
    _store_quality_cache(mode, payload)
    return payload


@router.get("/signals/governance/{symbol}")
def signal_governance(symbol: str, mode: str = Query(default="demo", pattern="^(demo|live)$"), session: Session = Depends(get_session)) -> dict:
    meta = get_symbol(session, symbol)
    intraday = bars_dataframe(session, symbol, "5m", limit=420)
    daily = bars_dataframe(session, symbol, "1d")
    articles = news_for_symbol(session, symbol)
    health = provider_health(mode)
    macro = macro_snapshot(session, mode)
    filings = filings_for_symbol(session, symbol)

    variants: list[dict] = []
    definitions = [
        ("technical_only", "Technical only", "Indicators, policy, risk gates, and market regime. News, macro, and filings removed."),
        ("technical_news", "Technical + news", "Adds mapped headline sentiment/relevance. OpenAI may enrich text server-side but never decides action."),
        ("full_governed", "Technical + news + macro + filings", "Adds macro regime contribution and SEC/event risk context."),
    ]

    for key, label, description in definitions:
        signal = generate_signal(
            symbol_meta=meta,
            intraday_bars=intraday,
            daily_bars=daily,
            articles=[] if key == "technical_only" else articles,
            mode=mode,
        )
        if key == "full_governed":
            signal["reasonCodes"].append(macro_signal_contribution(macro))
            filing_flags = filing_event_flags(filings)
            if filing_flags:
                signal["riskFlags"].extend(filing_flags)
                signal["provenance"]["filings"] = "SEC EDGAR/demo filing event risk overlay"
        signal["dataQuality"] = data_quality_score(signal, health, mode)
        signal["waterfall"] = signal_waterfall(signal)
        variants.append(
            {
                "key": key,
                "label": label,
                "description": description,
                "action": signal["action"],
                "confidence": signal["confidence"],
                "regime": signal["regime"],
                "reasonCodes": signal["reasonCodes"][:6],
                "riskFlags": signal["riskFlags"],
                "policyBlockers": signal["policyBlockers"],
                "newsSnapshot": signal["newsSnapshot"],
                "dataQuality": signal["dataQuality"],
                "waterfall": signal["waterfall"],
                "provenance": signal["provenance"],
            }
        )

    base = variants[0]
    comparisons = []
    for item in variants[1:]:
        confidence_delta = round(float(item["confidence"]) - float(base["confidence"]), 4)
        new_risks = sorted({flag["code"] for flag in item["riskFlags"]} - {flag["code"] for flag in base["riskFlags"]})
        added_reasons = sorted({reason["code"] for reason in item["reasonCodes"]} - {reason["code"] for reason in base["reasonCodes"]})
        comparisons.append(
            {
                "from": base["key"],
                "to": item["key"],
                "confidenceDelta": confidence_delta,
                "actionChanged": item["action"] != base["action"],
                "addedReasons": added_reasons,
                "newRiskFlags": new_risks,
                "headline": f"{item['label']} {'changed' if item['action'] != base['action'] else 'kept'} action at {round(item['confidence'] * 100)}% confidence.",
            }
        )

    return {
        "symbol": symbol,
        "mode": mode,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "variants": variants,
        "comparisons": comparisons,
        "caveat": "Governance comparison explains inputs and risk gates. It is not a model-selection promise or a performance claim.",
    }


@router.get("/universe")
def universe(session: Session = Depends(get_session)) -> dict:
    symbols = list_symbols(session)
    groups = {
        "All": [item.symbol for item in symbols],
        "Equities": [item.symbol for item in symbols if item.asset_class == "equity"],
        "ETFs": [item.symbol for item in symbols if item.asset_class == "etf"],
        "FX": [item.symbol for item in symbols if item.asset_class == "fx"],
        "Crypto": [item.symbol for item in symbols if item.asset_class == "crypto"],
        "Commodities": [item.symbol for item in symbols if item.asset_class == "commodity"],
    }
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "total": len(symbols),
        "groups": [{"name": name, "symbols": values, "count": len(values)} for name, values in groups.items()],
        "symbols": [
            {
                "symbol": item.symbol,
                "name": item.name,
                "assetClass": item.asset_class,
                "venue": item.venue,
                "currency": item.currency,
                "description": item.description,
            }
            for item in symbols
        ],
        "storagePolicy": "Selected universes are persisted locally in the browser; no auth is required.",
    }


@router.get("/data/coverage")
def data_coverage(session: Session = Depends(get_session)) -> dict:
    rows = []
    for item in list_symbols(session):
        daily_bars = session.query(Bar).filter(Bar.symbol == item.symbol, Bar.timeframe == "1d").count()
        intraday_bars = session.query(Bar).filter(Bar.symbol == item.symbol, Bar.timeframe == "5m").count()
        news_count = session.query(NewsArticle).filter(NewsArticle.symbols_csv.like(f"%{item.symbol}%")).count()
        filing_count = session.query(SecFiling).filter(SecFiling.symbol == item.symbol).count()
        signal_count = session.query(SignalRecord).filter(SignalRecord.symbol == item.symbol).count()
        backtest_count = session.query(BacktestRun).filter(BacktestRun.symbol == item.symbol).count()
        score = 0
        score += 25 if daily_bars >= 200 else 10 if daily_bars else 0
        score += 20 if intraday_bars >= 150 else 8 if intraday_bars else 0
        score += 15 if news_count else 0
        score += 15 if signal_count else 0
        score += 15 if backtest_count else 0
        score += 10 if filing_count else 0
        rows.append(
            {
                "symbol": item.symbol,
                "assetClass": item.asset_class,
                "dailyBars": daily_bars,
                "intradayBars": intraday_bars,
                "news": news_count,
                "filings": filing_count,
                "signals": signal_count,
                "backtests": backtest_count,
                "coverageScore": score,
                "status": "excellent" if score >= 85 else "good" if score >= 65 else "watch" if score >= 40 else "thin",
            }
        )
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "symbols": len(rows),
            "averageCoverage": round(sum(row["coverageScore"] for row in rows) / max(len(rows), 1), 2),
            "excellent": sum(1 for row in rows if row["status"] == "excellent"),
            "watchOrThin": sum(1 for row in rows if row["status"] in {"watch", "thin"}),
        },
        "rows": sorted(rows, key=lambda row: (row["coverageScore"], row["symbol"]), reverse=True),
        "caveat": "Coverage shows what evidence is available locally; it does not imply signal accuracy.",
    }


@router.get("/backtests/compare")
def backtests_compare(
    symbol: str = Query(default="SPY"),
    mode: str = Query(default="demo", pattern="^(demo|live)$"),
    session: Session = Depends(get_session),
) -> dict:
    cached = _cached_strategy_matrix(mode, symbol)
    if cached:
        return cached
    meta = get_symbol(session, symbol)
    daily = bars_dataframe(session, symbol, "1d").tail(260)
    news = news_for_symbol(session, symbol)
    rows = []
    for preset in PRESETS:
        result = run_backtest(
            symbol=symbol,
            bars=daily,
            articles=news,
            preset=preset,
            fees_bps=2.0,
            spread_bps=float(meta.avg_spread_bps),
            slippage_bps=1.5,
            allow_short=False,
            ablation="technical_news_tca",
        )
        robustness = backtest_robustness(result)
        metrics = result["metrics"]
        rows.append(
            {
                "preset": preset,
                "totalReturn": metrics.get("totalReturn"),
                "grossReturn": metrics.get("grossReturn"),
                "sharpe": metrics.get("sharpe"),
                "maxDrawdown": metrics.get("maxDrawdown"),
                "hitRate": metrics.get("hitRate"),
                "turnover": metrics.get("turnover"),
                "tradeCount": len(result.get("tradeList", [])),
                "robustnessScore": robustness["score"],
                "warnings": robustness["warnings"],
            }
        )
    ranked = sorted(
        rows,
        key=lambda row: (float(row["robustnessScore"]), float(row["sharpe"] or 0), float(row["totalReturn"] or 0)),
        reverse=True,
    )
    payload = {
        "symbol": symbol,
        "mode": mode,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "rows": ranked,
        "bestPreset": ranked[0]["preset"] if ranked else None,
        "caveat": "The matrix is deterministic demo/research evidence, not optimisation advice. Do not pick a preset solely from one sample.",
    }
    _store_strategy_matrix(mode, symbol, payload)
    return payload


@router.post("/assistant/research")
async def research_assistant(payload: dict, session: Session = Depends(get_session)) -> dict:
    question = str(payload.get("question", "")).strip()[:800]
    symbol = str(payload.get("symbol", "SPY")).upper().strip() or "SPY"
    mode = str(payload.get("mode", "demo"))
    if mode not in {"demo", "live"}:
        mode = "demo"
    if not question:
        question = "Summarise the current signal and risk context."

    meta = get_symbol(session, symbol)
    _, signal, news, _, _ = _signal_and_context(session, symbol, mode, persist_audit=False)
    governance_comparisons = [
        {
            "headline": "Signal action comes from deterministic indicators, risk gates, news context, macro context, and filing/event checks.",
            "confidenceDelta": 0,
            "actionChanged": False,
            "newRiskFlags": [flag["code"] for flag in signal["riskFlags"][:3]],
        }
    ]
    context = {
        "symbol": symbol,
        "assetName": meta.name,
        "mode": mode,
        "signal": {
            "action": signal["action"],
            "confidence": signal["confidence"],
            "regime": signal["regime"],
            "reasons": signal["reasonCodes"][:4],
            "riskFlags": signal["riskFlags"],
            "policyBlockers": signal["policyBlockers"],
            "dataQuality": signal.get("dataQuality", {}),
        },
        "news": [{"title": item.title, "source": item.source, "sentiment": item.raw_sentiment, "relevance": item.relevance} for item in news[:4]],
        "governanceComparisons": governance_comparisons,
    }

    deterministic_answer = (
        f"{symbol} is currently {signal['action'].replace('_', ' ')} at {round(signal['confidence'] * 100)}% confidence in a "
        f"{signal['regime'].replace('_', ' ').lower()} regime. The main evidence is "
        f"{', '.join(reason['label'] for reason in signal['reasonCodes'][:3]) or 'limited technical evidence'}. "
        f"Risk flags: {', '.join(flag['code'] for flag in signal['riskFlags']) or 'none active'}. "
        "This assistant is read-only and does not place orders."
    )

    settings = get_settings()
    source = "deterministic_local"
    answer = deterministic_answer
    if settings.openai_api_key and mode == "live":
        try:
            from openai import OpenAI

            def _request_openai_answer() -> object:
                client = OpenAI(api_key=settings.openai_api_key, timeout=6.0, max_retries=0)
                return client.responses.create(
                    model=settings.resolved_openai_model,
                    input=[
                        {
                            "role": "system",
                            "content": "You are a read-only market research assistant. Use only the provided JSON context. Do not predict prices or recommend real-money trading. Be concise and cite signal, risk, news, and governance evidence.",
                        },
                        {"role": "user", "content": f"Question: {question}\nContext JSON: {context}"},
                    ],
                    max_output_tokens=420,
                )

            response = await asyncio.wait_for(asyncio.to_thread(_request_openai_answer), timeout=7.0)
            text = getattr(response, "output_text", None)
            if text:
                answer = text
                source = "openai_server_side"
        except Exception:  # noqa: BLE001 - assistant must degrade gracefully.
            answer = f"{deterministic_answer} The AI enrichment provider was slow or unavailable, so this answer used deterministic local context only."
            source = "deterministic_fallback"

    return {
        "symbol": symbol,
        "mode": mode,
        "question": question,
        "answer": answer,
        "source": source,
        "citations": [item.title for item in news[:3]],
        "provenance": {
            "decisionBoundary": "read-only research assistant; no order execution",
            "usesOpenAI": source == "openai_server_side",
            "pricePrediction": False,
        },
    }


@router.get("/demo/briefing")
def demo_briefing(session: Session = Depends(get_session)) -> dict:
    symbols = list_symbols(session)
    alerts = list_alerts(session)
    reports = list_reports(session)
    macro = macro_snapshot(session, "demo")
    portfolio = portfolio_snapshot(session, "demo")
    return {
        "title": "Guided Research Walkthrough",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "readinessScore": system_readiness(session, "demo"),
        "readiness": [
            {"label": "Deterministic demo data", "status": "ready", "detail": f"{len(symbols)} seeded multi-asset instruments are available."},
            {"label": "Provider transparency", "status": "ready", "detail": "Settings shows configured, degraded, disabled, and manual-check-needed states without exposing secrets."},
            {"label": "Export pack", "status": "ready" if reports else "attention", "detail": "PDF export, screenshots, seeded metrics, and audit extract can be regenerated locally."},
            {"label": "Decision-support guardrail", "status": "ready", "detail": "No real-money order execution is implemented; portfolio actions are local/paper only."},
        ],
        "routeSequence": [
            {"route": "/", "label": "Dashboard", "goal": "Show macro strip, watchlist, chart, signal card, and audit tabs."},
            {"route": "/asset/SPY", "label": "Asset Detail", "goal": "Show replay, signal diff, SEC filing timeline, news timeline, and audit trail."},
            {"route": "/scanner", "label": "Scanner", "goal": "Filter explainable opportunities and open a selected symbol."},
            {"route": "/strategy-tester", "label": "Strategy Tester", "goal": "Run a deterministic TCA-aware backtest and inspect metrics."},
            {"route": "/reports", "label": "Reports", "goal": "Export a clean PDF investment note."},
            {"route": "/settings", "label": "Settings", "goal": "Show provider matrix, live health checks, security, and limitations."},
        ],
        "talkingPoints": [
            "Signals are deterministic and explainable; OpenAI is never the direct buy/sell decision source.",
            "Demo mode works with zero external keys and is the safest fast local walkthrough path.",
            "Live mode surfaces stale, degraded, missing, and manual-check-needed states honestly.",
            "Backtests include costs, spread, slippage, drawdown, turnover, and walk-forward views.",
        ],
        "checklist": [
            {"label": "Open Dashboard", "route": "/", "durationSeconds": 45, "proof": "Macro strip, data quality, signal waterfall, watchlist, and chart load."},
            {"label": "Open Asset Detail", "route": "/asset/SPY", "durationSeconds": 55, "proof": "Replay scenarios, SEC filings, signal change, and news timeline render."},
            {"label": "Run Strategy Tester", "route": "/strategy-tester", "durationSeconds": 60, "proof": "Backtest metrics, walk-forward, robustness, and trade list render."},
            {"label": "Export Report", "route": "/reports", "durationSeconds": 35, "proof": "PDF investment note is created under artefacts/exports."},
            {"label": "Show Settings", "route": "/settings", "durationSeconds": 35, "proof": "Provider fallback order and health matrix show without secrets."},
        ],
        "metrics": {
            "trackedAssets": len(symbols),
            "alerts": len(alerts),
            "reports": len(reports),
            "macroRegime": macro["regime"],
            "paperPositions": portfolio["summary"].get("openPositions", 0),
        },
    }


@router.post("/demo/warmup")
def demo_warmup(session: Session = Depends(get_session)) -> dict:
    """Prime deterministic demo caches before a presentation.

    This endpoint deliberately uses demo-mode data only. It does not perform
    live provider checks, send emails, execute trades, or expose credentials.
    """

    started = datetime.now(timezone.utc)
    warmed: list[str] = []
    errors: list[dict] = []

    def run_step(label: str, callback) -> None:
        try:
            callback()
            warmed.append(label)
        except Exception as exc:  # noqa: BLE001 - warmup should report partial readiness.
            errors.append({"step": label, "message": str(exc)})

    run_step("demo briefing", lambda: demo_briefing(session))
    run_step("dashboard SPY", lambda: dashboard(mode="demo", symbol="SPY", session=session))
    run_step("live dashboard shell", lambda: dashboard(mode="live", symbol="SPY", session=session))
    run_step("asset detail SPY", lambda: asset_detail(symbol="SPY", mode="demo", session=session))
    run_step("scanner default", lambda: scanner(mode="demo", action=None, min_confidence=0.0, session=session))
    run_step(
        "default strategy tester",
        lambda: backtests_run(
            BacktestRequest(
                symbol="SPY",
                timeframe="1d",
                preset="Mean Reversion",
                feesBps=2.0,
                spreadBps=2.0,
                slippageBps=1.0,
                longShort=False,
                ablation="technical_news_tca",
            ),
            session=session,
        ),
    )
    run_step("portfolio", lambda: portfolio(mode="demo", session=session))
    run_step("workspace", lambda: workspace(session=session))

    duration_ms = round((datetime.now(timezone.utc) - started).total_seconds() * 1000, 2)
    return {
        "status": "ready" if not errors else "partial",
        "mode": "demo",
        "durationMs": duration_ms,
        "warmed": warmed,
        "errors": errors,
        "cacheTtlSeconds": {
            "dashboard": _DASHBOARD_CACHE_SECONDS,
            "liveDashboard": _LIVE_DASHBOARD_CACHE_SECONDS,
            "assetDetail": _ASSET_CACHE_SECONDS,
            "scanner": _SCANNER_CACHE_SECONDS,
            "backtest": _BACKTEST_CACHE_SECONDS,
        },
        "message": "Demo caches primed. Open http://127.0.0.1:3000/demo first, then follow the checklist.",
    }


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    mode: str = Query(default="demo", pattern="^(demo|live)$"),
    symbol: str = Query(default="SPY"),
    session: Session = Depends(get_session),
) -> dict:
    if mode == "live":
        schedule_live_symbol_refresh(symbol)
    cached = _cached_dashboard(mode, symbol)
    if cached:
        return cached
    if mode == "live":
        return _quick_live_dashboard(symbol, session)
    meta, signal, news, intraday = _dashboard_signal_context(session, symbol, mode)
    daily_history = bars_dataframe(session, symbol, "1d")
    macro = macro_snapshot(session, mode)
    portfolio = portfolio_snapshot(session, mode)
    rows = []
    strongest_buy = "None"
    strongest_sell = "None"
    buy_score = -1.0
    sell_score = -1.0

    symbols = list_symbols(session)
    grouped_intraday = _all_intraday_bar_rows(session)

    for listed in symbols:
        if listed.symbol == symbol:
            listed_signal = signal
            last = intraday.iloc[-1]
            prev = intraday.iloc[-2]
            row_action = listed_signal["action"]
            row_confidence = listed_signal["confidence"]
            row_regime = listed_signal["regime"]
            row_sentiment = listed_signal["newsSnapshot"]["sentiment"]
            row_volume_ratio = listed_signal["indicatorSnapshot"]["volumeRatio"]
        else:
            listed_intraday_rows = grouped_intraday.get(listed.symbol)
            if not listed_intraday_rows or len(listed_intraday_rows) < 2:
                continue
            closes = [float(row.close) for row in listed_intraday_rows[-50:]]
            volumes = [float(row.volume) for row in listed_intraday_rows[-50:]]
            fast_signal = _fast_watchlist_signal_from_values(closes, volumes)
            last = listed_intraday_rows[-1]
            prev = listed_intraday_rows[-2]
            row_action = fast_signal["action"]
            row_confidence = fast_signal["confidence"]
            row_regime = fast_signal["regime"]
            row_sentiment = fast_signal["sentiment"]
            row_volume_ratio = fast_signal["volumeRatio"]
        row = {
            "symbol": listed.symbol,
            "name": listed.name,
            "lastPrice": round(float(last["close"] if hasattr(last, "__getitem__") else last.close), 4),
            "changePct": round(float((last["close"] if hasattr(last, "__getitem__") else last.close) / (prev["close"] if hasattr(prev, "__getitem__") else prev.close) - 1), 4),
            "signal": row_action,
            "confidence": row_confidence,
            "regime": row_regime,
            "sentiment": round(float(row_sentiment), 4),
            "volumeNote": "Volume spike" if row_volume_ratio > 1.4 else "Normal liquidity",
            "assetClass": listed.asset_class,
        }
        rows.append(row)
        score = row_confidence
        if row_action in {"BUY", "STRONG_BUY"} and score > buy_score:
            strongest_buy = listed.symbol
            buy_score = score
        if row_action in {"SELL", "STRONG_SELL"} and score > sell_score:
            strongest_sell = listed.symbol
            sell_score = score

    watchlist = sorted(rows, key=lambda item: item["confidence"], reverse=True)
    latest_audit = [
        {
            "createdAt": event.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "action": _visible_signal_action(event.action),
            "confidence": event.confidence,
            "policyPass": event.policy_pass,
            "reasonCodes": event.reason_codes_json,
            "riskFlags": event.risk_flags_json,
        }
        for event in recent_audit(session, symbol)
    ]
    cached_backtest = _cached_backtest(_default_backtest_request(symbol))
    backtest_summary = (
        cached_backtest["metrics"]
        if cached_backtest
        else {
            "status": "not precomputed",
            "note": "Run Strategy Tester for full metrics. Dashboard skips cold backtest recomputation so demo mode opens quickly.",
        }
    )

    payload = {
        "mode": mode,
        "trackedAssets": len(watchlist),
        "alertCount": len(list_alerts(session)),
        "strongestBuy": strongest_buy,
        "strongestSell": strongest_sell,
        "marketRegimeSummary": f"{sum(1 for row in watchlist if row['regime'] == 'TRENDING_BULL')} bullish, {sum(1 for row in watchlist if row['regime'] == 'RISK_OFF')} risk-off",
        "connectionSummary": "Deterministic demo feed active" if mode == "demo" else "Live feed status shown below",
        "health": provider_health(mode),
        "providerBadges": provider_badges(mode),
        "macro": macro,
        "portfolioSummary": portfolio["summary"],
        "watchlist": watchlist,
        "chart": _chart_payload(symbol, "5m", intraday, history_bars=daily_history),
        "signal": signal,
        "news": [
            {
                "title": item.title,
                "source": item.source,
                "publishedAt": item.published_at.replace(tzinfo=timezone.utc).isoformat(),
                "url": item.url,
                "sentiment": item.raw_sentiment,
                "relevance": item.relevance,
            }
            for item in news
        ],
        "audit": latest_audit,
        "backtestSummary": backtest_summary,
        "signalDiff": signal_diff(session, symbol),
        "readiness": system_readiness(session, mode),
        "fallbackPlan": provider_fallback_plan(mode),
    }
    payload = _sanitize_visible_actions(payload)
    _store_dashboard_cache(mode, symbol, payload)
    return payload


@router.get("/assets/{symbol}", response_model=AssetDetailResponse)
def asset_detail(
    symbol: str,
    mode: str = Query(default="demo", pattern="^(demo|live)$"),
    session: Session = Depends(get_session),
) -> dict:
    if mode == "live":
        schedule_live_symbol_refresh(symbol)
    cached = _cached_asset_detail(mode, symbol)
    if cached:
        return cached
    # Asset detail is a read-heavy research view. Dashboard/scanner/report flows
    # already persist recommendations, so avoid creating audit-write contention
    # every time a user opens a chart from the scanner.
    meta, signal, news, intraday, daily = _signal_and_context(session, symbol, mode, persist_audit=False)
    filings = filings_for_symbol(session, symbol)
    history = []
    enriched_daily = compute_indicators(daily).tail(60)
    for row in enriched_daily.itertuples():
        history.append(
            {
                "time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
                "close": round(float(row.close), 4),
                "rsi": round(float(row.rsi), 2) if row.rsi == row.rsi else None,
                "macd": round(float(row.macd), 4) if row.macd == row.macd else None,
            }
        )
    payload = {
        "mode": mode,
        "symbol": symbol,
        "metadata": {
            "name": meta.name,
            "assetClass": meta.asset_class,
            "venue": meta.venue,
            "currency": meta.currency,
            "avgSpreadBps": meta.avg_spread_bps,
            "description": meta.description,
        },
        "chart": _chart_payload(symbol, "5m", intraday, history_bars=bars_dataframe(session, symbol, "1d")) if mode == "live" else _chart_payload(symbol, "1d", daily),
        "signal": signal,
        "signalHistory": history,
        "newsTimeline": [
            {
                "id": item.id,
                "title": item.title,
                "source": item.source,
                "publishedAt": item.published_at.replace(tzinfo=timezone.utc).isoformat(),
                "url": item.url,
                "sentiment": item.raw_sentiment,
                "relevance": item.relevance,
            }
            for item in news
        ],
        "auditTrail": [
            {
                "createdAt": event.created_at.replace(tzinfo=timezone.utc).isoformat(),
                "action": _visible_signal_action(event.action),
                "confidence": event.confidence,
                "policyPass": event.policy_pass,
                "headlines": event.headlines_json,
            }
            for event in recent_audit(session, symbol, limit=20)
        ],
        "health": _system_status(mode)["health"],
        "macro": macro_snapshot(session, mode),
        "filingTimeline": filings,
        "filingDigest": filing_digest(filings),
        "signalDiff": signal_diff(session, symbol),
        "replayScenarios": [] if mode == "live" else replay_scenarios(symbol),
    }
    payload = _sanitize_visible_actions(payload)
    _store_asset_cache(mode, symbol, payload)
    return payload


@router.get("/scanner", response_model=ScannerResponse)
def scanner(
    mode: str = Query(default="demo", pattern="^(demo|live)$"),
    action: str | None = None,
    min_confidence: float = 0.0,
    session: Session = Depends(get_session),
) -> dict:
    cached = _cached_scanner(mode, action, min_confidence)
    if cached is not None:
        return cached

    results = []
    grouped_rows = _all_intraday_bar_rows(session)
    for listed in list_symbols(session):
        row = _scanner_row_from_cached_rows(session, listed, grouped_rows.get(listed.symbol, []))
        if row is None:
            row = _fast_scanner_row(session, listed)
        if action and row["action"] != action:
            continue
        if row["confidence"] < min_confidence:
            continue
        results.append(row)
    payload = {"mode": mode, "results": sorted(results, key=lambda item: item["confidence"], reverse=True), "filtersApplied": {"action": action, "minConfidence": min_confidence}}
    _store_scanner_cache(mode, action, min_confidence, payload)
    return payload


@router.post("/backtests/run", response_model=BacktestResponse)
def backtests_run(request: BacktestRequest, session: Session = Depends(get_session)) -> dict:
    cached = _cached_backtest(request)
    if cached:
        return cached
    try:
        meta = get_symbol(session, request.symbol)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    bars = bars_dataframe(session, request.symbol, request.timeframe)
    news = news_for_symbol(session, request.symbol)
    result = run_backtest(
        symbol=request.symbol,
        bars=bars,
        articles=news,
        preset=request.preset,
        fees_bps=request.feesBps,
        spread_bps=request.spreadBps or float(meta.avg_spread_bps),
        slippage_bps=request.slippageBps,
        allow_short=request.longShort,
        ablation=request.ablation,
    )
    result["robustness"] = backtest_robustness(result)
    save_backtest(session, result, request.model_dump())
    _store_backtest_cache(request, result)
    return result


@router.get("/alerts", response_model=list[AlertResponse])
def alerts(session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "id": alert.id,
            "symbol": alert.symbol,
            "kind": alert.kind,
            "name": alert.name,
            "enabled": alert.enabled,
            "rule": alert.rule_json,
            "history": alert.history_json,
        }
        for alert in list_alerts(session)
    ]


@router.get("/alerts/center")
def alerts_center(session: Session = Depends(get_session)) -> dict:
    return alert_center(session)


@router.post("/alerts/{alert_id}/toggle", response_model=AlertResponse)
def alerts_toggle(alert_id: str, session: Session = Depends(get_session)) -> dict:
    try:
        alert = toggle_alert(session, alert_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": alert.id, "symbol": alert.symbol, "kind": alert.kind, "name": alert.name, "enabled": alert.enabled, "rule": alert.rule_json, "history": alert.history_json}


@router.get("/reports", response_model=list[ReportResponse])
def reports(session: Session = Depends(get_session)) -> list[dict]:
    return [_report_response(report) for report in _visible_reports(list_reports(session))]


@router.get("/reports/{report_id}/download")
def reports_download(report_id: str, session: Session = Depends(get_session)) -> FileResponse:
    report = next((item for item in list_reports(session) if item.id == report_id), None)
    if report is None:
        raise HTTPException(status_code=404, detail="Report export was not found")
    path = Path(report.path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Report PDF is no longer available. Export it again from Reports.")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.get("/portfolio", response_model=PortfolioResponse)
def portfolio(mode: str = Query(default="demo", pattern="^(demo|live)$"), session: Session = Depends(get_session)) -> dict:
    payload = portfolio_snapshot(session, mode)
    payload["riskHeatmap"] = portfolio_risk_heatmap(payload)
    return payload


@router.get("/workspace", response_model=WorkspaceResponse)
def workspace(session: Session = Depends(get_session)) -> dict:
    return workspace_snapshot(session)


@router.get("/signals/{symbol}/diff")
def signals_diff(symbol: str, session: Session = Depends(get_session)) -> dict:
    return signal_diff(session, symbol)


@router.get("/filings/{symbol}")
def filings(symbol: str, session: Session = Depends(get_session)) -> dict:
    items = filings_for_symbol(session, symbol)
    return {"symbol": symbol, "filings": items, "digest": filing_digest(items)}


@router.get("/replay/{symbol}")
def replay(
    symbol: str,
    cursor: int = 120,
    timeframe: str = Query(default="1d"),
    mode: str = Query(default="demo", pattern="^(demo|live)$"),
    session: Session = Depends(get_session),
) -> dict:
    from app.services.replay import replay_payload

    effective_timeframe = "5m" if mode == "live" and timeframe == "1d" else timeframe
    if mode == "live":
        schedule_live_symbol_refresh(symbol)
    return replay_payload(session, symbol, cursor=cursor, timeframe=effective_timeframe, mode=mode)


@router.get("/strategy-builder/{symbol}")
def strategy_builder(symbol: str, mode: str = Query(default="demo", pattern="^(demo|live)$"), session: Session = Depends(get_session)) -> dict:
    try:
        return strategy_builder_payload(session, symbol, mode)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/strategy-builder/evaluate")
def strategy_builder_evaluate(body: dict, session: Session = Depends(get_session)) -> dict:
    symbol = str(body.get("symbol", "SPY")).upper()
    rule = str(body.get("rule", ""))
    try:
        context = strategy_builder_payload(session, symbol, str(body.get("mode", "demo")))["context"]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"symbol": symbol, "rule": rule, "evaluation": evaluate_strategy_rule(rule, context["values"]), "context": context}


@router.get("/terminal/multi-chart")
def terminal_multi_chart(symbols: str | None = None, timeframe: str = Query(default="1d"), session: Session = Depends(get_session)) -> dict:
    requested = _split_symbol_query(symbols)
    return multi_chart_payload(session, requested, timeframe)


@router.get("/chart-workspace/{symbol}")
def chart_workspace(symbol: str, session: Session = Depends(get_session)) -> dict:
    try:
        return chart_workspace_payload(session, symbol)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/alerts/builder")
def alerts_builder(session: Session = Depends(get_session)) -> dict:
    return alert_builder_payload(session)


@router.get("/replay-lab/{symbol}")
def replay_lab(symbol: str, cursor: int = 120, session: Session = Depends(get_session)) -> dict:
    try:
        return market_replay_lab_payload(session, symbol, cursor=cursor)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/scanner/columns")
def scanner_columns(session: Session = Depends(get_session)) -> dict:
    return scanner_columns_payload(session)


@router.get("/compare")
def compare(symbols: str | None = None, session: Session = Depends(get_session)) -> dict:
    return comparison_payload(session, _split_symbol_query(symbols))


@router.get("/events/calendar")
def events_calendar(mode: str = Query(default="demo", pattern="^(demo|live)$"), session: Session = Depends(get_session)) -> dict:
    return events_calendar_payload(session, mode)


@router.get("/tear-sheet/{symbol}")
def tear_sheet(symbol: str, mode: str = Query(default="demo", pattern="^(demo|live)$"), session: Session = Depends(get_session)) -> dict:
    try:
        return tear_sheet_payload(session, symbol, mode)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/patterns/{symbol}")
def patterns(symbol: str, session: Session = Depends(get_session)) -> dict:
    try:
        return pattern_payload(session, symbol)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/opportunities/ranked")
def opportunities_ranked(session: Session = Depends(get_session)) -> dict:
    return ranked_opportunities_payload(session)


@router.get("/pro-terminal")
def pro_terminal(mode: str = Query(default="demo", pattern="^(demo|live)$"), session: Session = Depends(get_session)) -> dict:
    cached = _cached_pro_terminal(mode)
    if cached:
        return cached
    payload = pro_terminal_payload(session, mode)
    _store_pro_terminal(mode, payload)
    return payload


@router.post("/reports/export", response_model=ReportResponse)
def export_report(request: ReportRequest, session: Session = Depends(get_session)) -> dict:
    from app.services.reporting import export_investment_note

    meta, signal, news, _, daily = _signal_and_context(session, request.symbol, request.mode)
    backtest = run_backtest(
        symbol=request.symbol,
        bars=daily,
        articles=news,
        preset=request.preset,
        fees_bps=2.0,
        spread_bps=float(meta.avg_spread_bps),
        slippage_bps=1.5,
        allow_short=False,
        ablation="technical_news_tca",
    )
    backtest["robustness"] = backtest_robustness(backtest)
    path = export_investment_note(
        symbol_meta=meta,
        signal=signal,
        backtest=backtest,
        news=[
            {
                "title": item.title,
                "source": item.source,
                "publishedAt": item.published_at.replace(tzinfo=timezone.utc).isoformat(),
            }
            for item in news
        ],
    )
    report = save_report(session, request.symbol, request.mode, str(path), {"preset": request.preset, "backtestRunId": backtest["runId"]})
    return _report_response(report)


@router.get("/audit/{symbol}")
def audit(symbol: str, session: Session = Depends(get_session)) -> list[dict]:
    return [
        {
            "createdAt": event.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "action": _visible_signal_action(event.action),
            "confidence": event.confidence,
            "policyPass": event.policy_pass,
            "reasonCodes": event.reason_codes_json,
            "headlines": event.headlines_json,
            "riskFlags": event.risk_flags_json,
            "freshnessSeconds": event.freshness_seconds,
            "provenance": event.provenance_json,
        }
        for event in recent_audit(session, symbol, limit=30)
    ]


def _split_symbol_query(symbols: str | None) -> list[str] | None:
    if not symbols:
        return None
    return [item.strip().upper() for item in symbols.split(",") if item.strip()]


def _stream_rows_snapshot() -> list[dict]:
    session = next(get_session())
    try:
        rows = []
        for listed in list_symbols(session):
            intraday = bars_dataframe(session, listed.symbol, "5m", limit=160)
            last = intraday.iloc[-1]
            fast_signal = _fast_watchlist_signal(intraday)
            rows.append(
                {
                    "symbol": listed.symbol,
                    "lastPrice": round(float(last["close"]), 4),
                    "signal": fast_signal["action"],
                    "confidence": fast_signal["confidence"],
                }
            )
        return rows
    finally:
        session.close()


async def stream_dashboard_snapshot(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            rows = await asyncio.to_thread(_stream_rows_snapshot)
            await websocket.send_json({"type": "market_snapshot", "timestamp": datetime.now(timezone.utc).isoformat(), "rows": rows, "health": provider_health("demo")})
            await asyncio.sleep(5.0)
    except WebSocketDisconnect:
        return
