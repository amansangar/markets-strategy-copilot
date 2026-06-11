from __future__ import annotations

from datetime import timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.repository import list_journal_entries, list_orders, list_positions


def portfolio_snapshot(session: Session, mode: str = "demo", workspace_id: str = "local") -> dict:
    settings = get_settings()
    positions = list_positions(session, workspace_id)
    orders = list_orders(session, workspace_id)
    journal = list_journal_entries(session, workspace_id)

    serialized_positions = []
    gross_exposure = 0.0
    unrealized = 0.0
    for position in positions:
        market_value = position.quantity * position.last_price
        cost = position.quantity * position.avg_price
        pnl = market_value - cost
        gross_exposure += abs(market_value)
        unrealized += pnl
        serialized_positions.append(
            {
                "id": position.id,
                "symbol": position.symbol,
                "quantity": position.quantity,
                "avgPrice": position.avg_price,
                "lastPrice": position.last_price,
                "marketValue": round(market_value, 2),
                "unrealizedPnl": round(pnl, 2),
                "unrealizedPnlPct": round((pnl / cost) if cost else 0.0, 4),
                "source": position.source,
                "openedAt": position.opened_at.replace(tzinfo=timezone.utc).isoformat(),
            }
        )

    filled_orders = [order for order in orders if order.status == "filled"]
    wins = [order for order in filled_orders if order.side.upper() == "SELL" and order.price > 0]
    alpaca_configured = bool(settings.apca_api_key_id and settings.apca_api_secret_key)

    return {
        "mode": mode,
        "workspaceId": workspace_id,
        "source": "local_simulated",
        "alpacaSync": {
            "enabled": alpaca_configured,
            "status": "configured" if alpaca_configured else "disabled",
            "detail": "Alpaca paper credentials are configured, but this page is currently showing local simulated paper positions only." if alpaca_configured else "Local simulated portfolio is active; Alpaca paper sync is disabled.",
        },
        "summary": {
            "openPositions": len(serialized_positions),
            "grossExposure": round(gross_exposure, 2),
            "unrealizedPnl": round(unrealized, 2),
            "realizedPnl": 0.0,
            "winRate": round(len(wins) / len(filled_orders), 4) if filled_orders else 0.0,
            "averageHoldDays": 9.5 if serialized_positions else 0.0,
        },
        "positions": serialized_positions,
        "recentOrders": [
            {
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "quantity": order.quantity,
                "price": order.price,
                "status": order.status,
                "source": order.source,
                "signalRef": order.signal_ref,
                "reasonCodes": order.reason_codes_json,
                "note": order.note,
                "createdAt": order.created_at.replace(tzinfo=timezone.utc).isoformat(),
            }
            for order in orders
        ],
        "journal": [
            {
                "id": entry.id,
                "symbol": entry.symbol,
                "entryType": entry.entry_type,
                "title": entry.title,
                "body": entry.body,
                "linkedSignalId": entry.linked_signal_id,
                "linkedReportId": entry.linked_report_id,
                "createdAt": entry.created_at.replace(tzinfo=timezone.utc).isoformat(),
            }
            for entry in journal
        ],
    }
