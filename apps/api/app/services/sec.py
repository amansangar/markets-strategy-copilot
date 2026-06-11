from __future__ import annotations

from datetime import timezone

from sqlalchemy.orm import Session

from app.repository import list_filings


def filings_for_symbol(session: Session, symbol: str, limit: int = 12) -> list[dict]:
    return [
        {
            "id": filing.id,
            "symbol": filing.symbol,
            "accessionNumber": filing.accession_number,
            "filingType": filing.filing_type,
            "filedAt": filing.filed_at.replace(tzinfo=timezone.utc).isoformat(),
            "title": filing.title,
            "url": filing.url,
            "riskLevel": filing.risk_level,
            "digest": filing.digest,
            "facts": filing.facts_json,
        }
        for filing in list_filings(session, symbol, limit=limit)
    ]


def filing_event_flags(filings: list[dict]) -> list[dict]:
    flags = []
    for filing in filings[:3]:
        if filing["riskLevel"] in {"medium", "high"}:
            flags.append(
                {
                    "code": f"FILING_{filing['filingType']}",
                    "severity": filing["riskLevel"],
                    "message": f"{filing['filingType']} filing context: {filing['digest']}",
                }
            )
    return flags


def filing_digest(filings: list[dict]) -> dict:
    if not filings:
        return {
            "headline": "No recent filing events in the local cache.",
            "riskLevel": "low",
            "items": [],
        }
    high_or_medium = [item for item in filings if item["riskLevel"] in {"medium", "high"}]
    return {
        "headline": f"{len(filings)} recent filing/event records, {len(high_or_medium)} carrying caution markers.",
        "riskLevel": "high" if any(item["riskLevel"] == "high" for item in filings) else ("medium" if high_or_medium else "low"),
        "items": filings[:5],
    }
