from __future__ import annotations

from app.repository import latest_signal_record
from sqlalchemy.orm import Session


def _visible_action(action: object) -> str:
    action_text = str(action or "BUY")
    return action_text if action_text in {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL", "NO_SIGNAL"} else "HOLD"


def signal_diff(session: Session, symbol: str) -> dict:
    current = latest_signal_record(session, symbol, offset=0)
    previous = latest_signal_record(session, symbol, offset=1)
    if not current or not previous:
        return {
            "available": False,
            "headline": "No previous signal snapshot is available yet.",
            "changes": [],
        }

    current_payload = current.payload_json
    previous_payload = previous.payload_json
    changes = []
    confidence_delta = round(float(current.confidence) - float(previous.confidence), 4)
    current_action = _visible_action(current.action)
    previous_action = _visible_action(previous.action)
    if current_action != previous_action:
        changes.append({"kind": "action", "label": "Action changed", "before": previous_action, "after": current_action})
    if abs(confidence_delta) >= 0.01:
        changes.append({"kind": "confidence", "label": "Confidence moved", "before": previous.confidence, "after": current.confidence, "delta": confidence_delta})
    if current.regime != previous.regime:
        changes.append({"kind": "regime", "label": "Technical regime changed", "before": previous.regime, "after": current.regime})

    current_indicators = current_payload.get("indicatorSnapshot", {})
    previous_indicators = previous_payload.get("indicatorSnapshot", {})
    for key in ("rsi", "macd", "macdSignal", "adx", "volumeRatio"):
        if key in current_indicators and key in previous_indicators:
            before = previous_indicators[key]
            after = current_indicators[key]
            if isinstance(before, (int, float)) and isinstance(after, (int, float)) and abs(after - before) > 0.05:
                changes.append({"kind": "indicator", "label": key, "before": round(before, 4), "after": round(after, 4), "delta": round(after - before, 4)})

    current_risk = {item.get("code") for item in current_payload.get("riskFlags", [])}
    previous_risk = {item.get("code") for item in previous_payload.get("riskFlags", [])}
    added_risk = sorted(current_risk - previous_risk)
    removed_risk = sorted(previous_risk - current_risk)
    if added_risk or removed_risk:
        changes.append({"kind": "risk", "label": "Risk blocker set changed", "added": added_risk, "removed": removed_risk})

    if not changes:
        changes.append({"kind": "stable", "label": "No material signal change", "detail": "Action, confidence, regime, and major risk flags are broadly unchanged."})

    return {
        "available": True,
        "headline": f"{symbol} changed by {confidence_delta:+.1%} confidence since the previous saved signal.",
        "currentSignalId": current.id,
        "previousSignalId": previous.id,
        "changes": changes,
    }
