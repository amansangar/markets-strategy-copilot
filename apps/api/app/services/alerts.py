from __future__ import annotations

from datetime import timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.repository import list_alert_delivery_logs, list_alerts


def alert_center(session: Session) -> dict:
    settings = get_settings()
    alerts = list_alerts(session)
    logs = list_alert_delivery_logs(session)
    email_enabled = bool(settings.resend_api_key and settings.resend_from_email)
    channels = [
        {"name": "browser", "enabled": True, "detail": "Browser and in-app notifications are always available locally."},
        {"name": "email", "enabled": email_enabled, "detail": "Resend email delivery is enabled." if email_enabled else "Email disabled until RESEND_API_KEY and RESEND_FROM_EMAIL are configured."},
        {"name": "webhook", "enabled": False, "detail": "Webhook delivery is unavailable in this version; no outbound webhook is sent."},
    ]
    return {
        "summary": {
            "totalAlerts": len(alerts),
            "enabledAlerts": sum(1 for alert in alerts if alert.enabled),
            "emailEnabled": email_enabled,
            "cooldownPolicy": "Duplicate alert events use symbol/rule/channel dedupe keys and local cooldowns.",
        },
        "channels": channels,
        "deliveryLog": [
            {
                "id": log.id,
                "alertId": log.alert_id,
                "channel": log.channel,
                "status": log.status,
                "dedupeKey": log.dedupe_key,
                "detail": log.detail,
                "createdAt": log.created_at.replace(tzinfo=timezone.utc).isoformat(),
            }
            for log in logs
        ],
        "supportedAlertTypes": [
            "price",
            "indicator",
            "multi_factor_signal",
            "news",
            "macro_regime",
            "filing_event",
            "signal_strength_change",
            "stale_data",
            "provider_outage",
        ],
    }
