from __future__ import annotations

from datetime import datetime
import re

import pandas as pd
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AlertDeliveryLog,
    AuditEvent,
    BacktestRun,
    BacktestTrade,
    Bar,
    ExportedReport,
    JournalEntry,
    MacroSnapshot,
    NewsArticle,
    PortfolioOrder,
    PortfolioPosition,
    ProviderSnapshot,
    SecFiling,
    SignalRecord,
    Symbol,
    WorkspacePreference,
)


def list_symbols(session: Session) -> list[Symbol]:
    return list(session.scalars(select(Symbol).order_by(Symbol.symbol)))


def get_symbol(session: Session, symbol: str) -> Symbol:
    result = session.get(Symbol, symbol)
    if not result:
        raise KeyError(f"Unknown symbol: {symbol}")
    return result


def bars_dataframe(session: Session, symbol: str, timeframe: str, limit: int | None = None) -> pd.DataFrame:
    query = select(Bar).where(Bar.symbol == symbol, Bar.timeframe == timeframe)
    if limit:
        rows = list(session.scalars(query.order_by(desc(Bar.time)).limit(limit)))
        rows.reverse()
    else:
        rows = list(session.scalars(query.order_by(Bar.time.asc())))
    frame = pd.DataFrame(
        [
            {
                "time": row.time,
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
            }
            for row in rows
        ]
    )
    return frame


def news_for_symbol(session: Session, symbol: str, limit: int = 8) -> list[NewsArticle]:
    rows = list(
        session.scalars(
            select(NewsArticle)
            .where(NewsArticle.symbols_csv.like(f"%{symbol}%"))
            .order_by(NewsArticle.published_at.desc())
            .limit(limit * 4)
        )
    )
    relevant = [row for row in rows if _article_matches_symbol(symbol, row)]
    return (relevant or rows)[:limit]


def _article_matches_symbol(symbol: str, article: NewsArticle) -> bool:
    text = f"{article.title} {article.description}".lower()
    symbol_upper = symbol.upper()
    market_terms = {
        "market",
        "markets",
        "stock",
        "stocks",
        "shares",
        "equity",
        "etf",
        "earnings",
        "wall street",
        "index",
        "inflation",
        "rates",
        "fed",
    }
    broad_symbol_terms = {
        "SPY": {"s&p", "spdr", "s&p 500", "index", "etf", *market_terms},
        "QQQ": {"nasdaq", "qqq", "invesco", "index", "etf", *market_terms},
        "DIA": {"dow", "industrial", "index", "etf", *market_terms},
        "GLD": {"gold", "bullion", "commod", "etf", "rates", "inflation"},
        "BTCUSD": {"bitcoin", "btc", "crypto", "cryptocurrency"},
        "ETHUSD": {"ethereum", "ether", "crypto", "cryptocurrency"},
        "EURUSD": {"eur/usd", "euro", "dollar", "forex", "currency", "ecb", "fed"},
    }
    expected_terms = broad_symbol_terms.get(symbol_upper)
    if expected_terms:
        return any(_contains_market_term(text, term) for term in expected_terms)
    return any(_contains_market_term(text, term) for term in market_terms) or _contains_market_term(text, symbol.lower())


def _contains_market_term(text: str, term: str) -> bool:
    term = term.lower()
    if any(character in term for character in {" ", "&", "/"}):
        return term in text
    return re.search(rf"\b{re.escape(term)}s?\b", text) is not None


def save_signal(session: Session, payload: dict) -> SignalRecord:
    record = SignalRecord(
        symbol=payload["symbol"],
        mode=payload["mode"],
        timeframe=payload["timeframe"],
        action=payload["action"],
        confidence=payload["confidence"],
        regime=payload["regime"],
        horizon=payload["horizon"],
        price=payload["currentPrice"],
        payload_json=payload,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def record_audit_event(
    session: Session,
    *,
    symbol: str,
    event_type: str,
    mode: str,
    action: str,
    confidence: float,
    reason_codes: list[dict],
    indicator_values: dict,
    headlines: list[dict],
    policy_pass: bool,
    risk_flags: list[dict],
    freshness_seconds: float,
    provenance: dict,
) -> AuditEvent:
    event = AuditEvent(
        symbol=symbol,
        event_type=event_type,
        mode=mode,
        action=action,
        confidence=confidence,
        reason_codes_json=reason_codes,
        indicator_values_json=indicator_values,
        headlines_json=headlines,
        policy_pass=policy_pass,
        risk_flags_json=risk_flags,
        freshness_seconds=freshness_seconds,
        provenance_json=provenance,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def recent_audit(session: Session, symbol: str, limit: int = 12) -> list[AuditEvent]:
    return list(
        session.scalars(
            select(AuditEvent)
            .where(AuditEvent.symbol == symbol)
            .order_by(desc(AuditEvent.created_at))
            .limit(limit)
        )
    )


def save_backtest(session: Session, result: dict, request: dict) -> BacktestRun:
    run = BacktestRun(
        id=result["runId"],
        symbol=result["symbol"],
        timeframe=request["timeframe"],
        preset=request["preset"],
        mode="demo",
        parameters_json=request,
        metrics_json=result["metrics"],
    )
    session.add(run)
    for trade in result["tradeList"]:
        session.add(
            BacktestTrade(
                run_id=result["runId"],
                symbol=result["symbol"],
                side=trade["side"],
                entry_time=datetime.fromisoformat(trade["entryTime"]),
                exit_time=datetime.fromisoformat(trade["exitTime"]),
                entry_price=trade["entryPrice"],
                exit_price=trade["exitPrice"],
                pnl_pct=trade["pnlPct"],
                hold_bars=trade["holdBars"],
                total_cost_bps=trade["totalCostBps"],
            )
        )
    session.commit()
    session.refresh(run)
    return run


def get_backtest_run(session: Session, run_id: str) -> BacktestRun | None:
    return session.get(BacktestRun, run_id)


def list_alerts(session: Session) -> list[Alert]:
    return list(session.scalars(select(Alert).order_by(Alert.symbol, Alert.name)))


def toggle_alert(session: Session, alert_id: str) -> Alert:
    alert = session.get(Alert, alert_id)
    if not alert:
        raise KeyError(f"Unknown alert: {alert_id}")
    alert.enabled = not alert.enabled
    session.commit()
    session.refresh(alert)
    return alert


def save_report(session: Session, symbol: str, mode: str, path: str, metadata: dict) -> ExportedReport:
    report = ExportedReport(symbol=symbol, mode=mode, path=path, metadata_json=metadata)
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def list_reports(session: Session) -> list[ExportedReport]:
    return list(session.scalars(select(ExportedReport).order_by(desc(ExportedReport.created_at))))


def latest_signal_record(session: Session, symbol: str, offset: int = 0) -> SignalRecord | None:
    rows = list(
        session.scalars(
            select(SignalRecord)
            .where(SignalRecord.symbol == symbol)
            .order_by(desc(SignalRecord.created_at))
            .limit(offset + 1)
        )
    )
    return rows[offset] if len(rows) > offset else None


def save_provider_snapshot(session: Session, payload: dict) -> ProviderSnapshot:
    snapshot = ProviderSnapshot(
        provider=payload["name"],
        mode=payload["mode"],
        status=payload["status"],
        freshness_seconds=payload.get("freshnessSeconds"),
        payload_json=payload,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def save_macro_snapshot(session: Session, payload: dict) -> MacroSnapshot:
    snapshot = MacroSnapshot(
        mode=payload["mode"],
        regime=payload["regime"],
        risk_score=payload["riskScore"],
        rates_trend=payload["ratesTrend"],
        inflation_pressure=payload["inflationPressure"],
        credit_stress=payload["creditStress"],
        growth_momentum=payload["growthMomentum"],
        summary=payload["summary"],
        components_json=payload["components"],
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def latest_macro_snapshot(session: Session, mode: str) -> MacroSnapshot | None:
    return session.scalar(
        select(MacroSnapshot)
        .where(MacroSnapshot.mode == mode)
        .order_by(desc(MacroSnapshot.created_at))
        .limit(1)
    )


def list_filings(session: Session, symbol: str, limit: int = 12) -> list[SecFiling]:
    return list(
        session.scalars(
            select(SecFiling)
            .where(SecFiling.symbol == symbol)
            .order_by(desc(SecFiling.filed_at))
            .limit(limit)
        )
    )


def list_positions(session: Session, workspace_id: str = "local") -> list[PortfolioPosition]:
    return list(session.scalars(select(PortfolioPosition).where(PortfolioPosition.workspace_id == workspace_id).order_by(PortfolioPosition.symbol)))


def list_orders(session: Session, workspace_id: str = "local", limit: int = 20) -> list[PortfolioOrder]:
    return list(
        session.scalars(
            select(PortfolioOrder)
            .where(PortfolioOrder.workspace_id == workspace_id)
            .order_by(desc(PortfolioOrder.created_at))
            .limit(limit)
        )
    )


def list_journal_entries(session: Session, workspace_id: str = "local", limit: int = 20) -> list[JournalEntry]:
    return list(
        session.scalars(
            select(JournalEntry)
            .where(JournalEntry.workspace_id == workspace_id)
            .order_by(desc(JournalEntry.created_at))
            .limit(limit)
        )
    )


def list_workspace_preferences(session: Session, workspace_id: str = "local") -> list[WorkspacePreference]:
    return list(
        session.scalars(
            select(WorkspacePreference)
            .where(WorkspacePreference.workspace_id == workspace_id)
            .order_by(WorkspacePreference.kind, WorkspacePreference.name)
        )
    )


def list_alert_delivery_logs(session: Session, limit: int = 25) -> list[AlertDeliveryLog]:
    return list(session.scalars(select(AlertDeliveryLog).order_by(desc(AlertDeliveryLog.created_at)).limit(limit)))
