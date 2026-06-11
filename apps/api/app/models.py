from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid4())


class Symbol(Base):
    __tablename__ = "symbols"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    asset_class: Mapped[str] = mapped_column(String(64))
    venue: Mapped[str] = mapped_column(String(128))
    currency: Mapped[str] = mapped_column(String(16))
    avg_spread_bps: Mapped[float] = mapped_column(Float)
    risk_limit: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(Text)


class Bar(Base):
    __tablename__ = "bars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(500))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbols_csv: Mapped[str] = mapped_column(String(255), index=True)
    raw_sentiment: Mapped[float] = mapped_column(Float)
    relevance: Mapped[float] = mapped_column(Float)
    enrichment_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SignalRecord(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    mode: Mapped[str] = mapped_column(String(16))
    timeframe: Mapped[str] = mapped_column(String(8))
    action: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    regime: Mapped[str] = mapped_column(String(32))
    horizon: Mapped[str] = mapped_column(String(32))
    price: Mapped[float] = mapped_column(Float)
    payload_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(8))
    preset: Mapped[str] = mapped_column(String(64))
    mode: Mapped[str] = mapped_column(String(16))
    parameters_json: Mapped[dict] = mapped_column(JSON)
    metrics_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exit_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    pnl_pct: Mapped[float] = mapped_column(Float)
    hold_bars: Mapped[int] = mapped_column(Integer)
    total_cost_bps: Mapped[float] = mapped_column(Float)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    rule_json: Mapped[dict] = mapped_column(JSON)
    history_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    reason_codes_json: Mapped[list] = mapped_column(JSON)
    indicator_values_json: Mapped[dict] = mapped_column(JSON)
    headlines_json: Mapped[list] = mapped_column(JSON)
    policy_pass: Mapped[bool] = mapped_column(Boolean)
    risk_flags_json: Mapped[list] = mapped_column(JSON)
    freshness_seconds: Mapped[float] = mapped_column(Float)
    provenance_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ExportedReport(Base):
    __tablename__ = "exported_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    mode: Mapped[str] = mapped_column(String(16))
    path: Mapped[str] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ProviderSnapshot(Base):
    __tablename__ = "provider_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    mode: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(32))
    freshness_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class MacroSnapshot(Base):
    __tablename__ = "macro_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mode: Mapped[str] = mapped_column(String(16), index=True)
    regime: Mapped[str] = mapped_column(String(32), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    rates_trend: Mapped[str] = mapped_column(String(32))
    inflation_pressure: Mapped[str] = mapped_column(String(32))
    credit_stress: Mapped[str] = mapped_column(String(32))
    growth_momentum: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    components_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SecFiling(Base):
    __tablename__ = "sec_filings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    accession_number: Mapped[str] = mapped_column(String(64), index=True)
    filing_type: Mapped[str] = mapped_column(String(32), index=True)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(600))
    risk_level: Mapped[str] = mapped_column(String(32))
    digest: Mapped[str] = mapped_column(Text)
    facts_json: Mapped[dict] = mapped_column(JSON, default=dict)


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="local")
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    avg_price: Mapped[float] = mapped_column(Float)
    last_price: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), default="local_simulated")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PortfolioOrder(Base):
    __tablename__ = "portfolio_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="local")
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32), default="local_simulated")
    signal_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="local")
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    entry_type: Mapped[str] = mapped_column(String(32), default="note")
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    linked_signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linked_report_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class WorkspacePreference(Base):
    __tablename__ = "workspace_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="local")
    kind: Mapped[str] = mapped_column(String(48), index=True)
    name: Mapped[str] = mapped_column(String(255))
    payload_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AlertDeliveryLog(Base):
    __tablename__ = "alert_delivery_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    alert_id: Mapped[str] = mapped_column(String(36), index=True)
    channel: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    dedupe_key: Mapped[str] = mapped_column(String(128), index=True)
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
