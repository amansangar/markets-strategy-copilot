from __future__ import annotations

from datetime import timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.repository import list_reports, list_workspace_preferences


def workspace_snapshot(session: Session, workspace_id: str = "local") -> dict:
    settings = get_settings()
    auth_enabled = bool(settings.next_public_clerk_publishable_key and settings.clerk_secret_key)
    preferences = list_workspace_preferences(session, workspace_id)
    reports = list_reports(session)
    grouped: dict[str, list[dict]] = {}
    for item in preferences:
        grouped.setdefault(item.kind, []).append(
            {
                "id": item.id,
                "name": item.name,
                "payload": item.payload_json,
                "updatedAt": item.updated_at.replace(tzinfo=timezone.utc).isoformat(),
            }
        )
    return {
        "workspaceId": workspace_id,
        "auth": {
            "mode": "clerk" if auth_enabled else "guest_local",
            "roles": ["guest/local"] if not auth_enabled else ["member", "admin"],
            "detail": "Clerk is configured." if auth_enabled else "Clerk keys are missing; app remains open in local guest mode.",
        },
        "savedWatchlists": grouped.get("watchlist", []),
        "savedScanners": grouped.get("scanner", []),
        "chartLayouts": grouped.get("chart_layout", []),
        "symbolNotes": grouped.get("symbol_note", []),
        "reportHistory": [
            {"reportId": report.id, "symbol": report.symbol, "mode": report.mode, "path": report.path, "createdAt": report.created_at.replace(tzinfo=timezone.utc).isoformat()}
            for report in reports[:12]
        ],
    }
