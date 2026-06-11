from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    if database_url.startswith("postgres"):
        # Keep local startup responsive when a configured Postgres service is down.
        return {"connect_timeout": 3}
    return {}


def _engine_kwargs(database_url: str) -> dict:
    kwargs: dict = {"future": True}
    if database_url.startswith("postgres"):
        kwargs["pool_pre_ping"] = True
        kwargs["pool_timeout"] = 3
    return kwargs


def _make_engine(database_url: str):
    return create_engine(database_url, connect_args=_connect_args(database_url), **_engine_kwargs(database_url))


def _fallback_sqlite_url() -> str:
    path = Path(get_settings().repo_root / "markets_strategy_copilot_local.db")
    return "sqlite:///" + path.as_posix()


def _rebind_engine(database_url: str) -> None:
    global engine

    try:
        engine.dispose()
    except Exception:
        pass
    engine = _make_engine(database_url)
    SessionLocal.configure(bind=engine)


settings = get_settings()
engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)



def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    from app import models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError:
        settings = get_settings()
        if settings.database_url.startswith("sqlite") or settings.app_env.lower() in {"production", "prod"}:
            raise
        _rebind_engine(_fallback_sqlite_url())
        Base.metadata.create_all(bind=engine)
    _ensure_runtime_indexes()


def _ensure_runtime_indexes() -> None:
    """Add read-path indexes that keep local demo/live research screens responsive."""

    index_statements = [
        "CREATE INDEX IF NOT EXISTS ix_bars_symbol_timeframe_time ON bars (symbol, timeframe, time)",
        "CREATE INDEX IF NOT EXISTS ix_signals_symbol_created_at ON signals (symbol, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_audit_events_symbol_created_at ON audit_events (symbol, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_exported_reports_created_at ON exported_reports (created_at)",
    ]
    with engine.begin() as connection:
        for statement in index_statements:
            connection.execute(text(statement))
