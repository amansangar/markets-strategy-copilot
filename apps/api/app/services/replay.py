from __future__ import annotations

from datetime import timezone

from sqlalchemy.orm import Session

from app.repository import bars_dataframe, news_for_symbol
from app.services.indicators import compute_indicators


def replay_payload(session: Session, symbol: str, cursor: int = 120, timeframe: str = "1d", mode: str = "demo") -> dict:
    bars = compute_indicators(bars_dataframe(session, symbol, timeframe))
    if bars.empty:
        return {"symbol": symbol, "mode": mode, "timeframe": timeframe, "cursor": 0, "candles": [], "events": [], "signalTimeline": []}
    if mode == "live" and (cursor <= 120 or cursor >= 9999):
        safe_cursor = len(bars)
    else:
        safe_cursor = max(20, min(cursor, len(bars)))
    visible = bars.iloc[:safe_cursor].tail(160)
    last = visible.iloc[-1]
    news = news_for_symbol(session, symbol, limit=5)
    events = [
        {
            "time": item.published_at.replace(tzinfo=timezone.utc).isoformat(),
            "kind": "news",
            "title": item.title,
            "detail": f"{item.source} sentiment {item.raw_sentiment:.2f}",
        }
        for item in news
    ]
    signal_timeline = []
    for row in visible.tail(24).itertuples():
        score = 0.0
        score += 1.0 if row.close >= row.ema_21 else -1.0
        score += 0.7 if row.close >= row.ema_50 else -0.7
        score += 0.4 if row.rsi >= 50 else -0.4
        if row.rsi >= 76:
            score -= 0.6
        elif row.rsi <= 24:
            score += 0.6
        action = "STRONG_BUY" if score >= 1.6 else ("BUY" if score >= 0.45 else ("STRONG_SELL" if score <= -1.6 else ("SELL" if score <= -0.45 else "HOLD")))
        signal_timeline.append(
            {
                "time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
                "action": action,
                "confidence": round(0.55 + min(abs(float(row.close - row.ema_21)) / max(float(row.close), 1.0), 0.25), 3),
                "reason": "Replay uses only data available up to the cursor; future bars are hidden.",
            }
        )
    return {
        "symbol": symbol,
        "mode": mode,
        "timeframe": timeframe,
        "cursor": safe_cursor,
        "cursorTime": last["time"].to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
        "candles": [
            {
                "time": row.time.to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
                "open": round(float(row.open), 4),
                "high": round(float(row.high), 4),
                "low": round(float(row.low), 4),
                "close": round(float(row.close), 4),
                "volume": round(float(row.volume), 2),
            }
            for row in visible.itertuples()
        ],
        "events": events,
        "signalTimeline": signal_timeline,
        "lookaheadGuard": (
            "Live replay follows the latest cached/live bars and refreshes with the page every minute; stale providers remain visible in source health."
            if mode == "live"
            else "Replay payload truncates bars before computing the visible signal timeline."
        ),
    }
