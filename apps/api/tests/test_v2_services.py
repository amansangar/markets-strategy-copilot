from __future__ import annotations

from app.config import get_settings
from app.db import get_session
from app.services.macro import macro_snapshot
from app.services.observability import observability_status
from app.services.portfolio import portfolio_snapshot
from app.services.providers import adapter_registry, provider_matrix
from app.services.sec import filing_digest, filings_for_symbol


def test_openai_latest_alias_resolves_to_supported_model(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "latest")
    get_settings.cache_clear()
    assert get_settings().resolved_openai_model == "gpt-5.5"
    get_settings.cache_clear()


def test_provider_registry_degrades_without_optional_keys(monkeypatch) -> None:
    for key in [
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "FRED_API_KEY",
        "SEC_USER_AGENT",
        "FINNHUB_API_KEY",
        "ALPHAVANTAGE_API_KEY",
        "FMP_API_KEY",
        "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
        "CLERK_SECRET_KEY",
        "RESEND_API_KEY",
        "RESEND_FROM_EMAIL",
    ]:
        monkeypatch.setenv(key, "")
    get_settings.cache_clear()
    matrix = provider_matrix("live")
    assert any(item["name"] == "alpaca" and item["status"] == "disabled" for item in matrix)
    assert all(item["name"] != "posthog" for item in matrix)
    assert all(item["name"] != "sentry" for item in matrix)
    assert "polygon" in adapter_registry()
    get_settings.cache_clear()


def test_macro_regime_snapshot_is_deterministic(client) -> None:
    for session in get_session():
        first = macro_snapshot(session, "demo")
        second = macro_snapshot(session, "demo")
    assert first["regime"] == second["regime"]
    assert first["riskScore"] == second["riskScore"]
    assert "FRED" not in first["summary"]


def test_sec_filing_normalization(client) -> None:
    for session in get_session():
        filings = filings_for_symbol(session, "SPY")
        digest = filing_digest(filings)
    assert filings
    assert digest["headline"]
    assert {"low", "medium", "high"} >= {digest["riskLevel"]}


def test_portfolio_guest_mode_available(client) -> None:
    for session in get_session():
        payload = portfolio_snapshot(session, "demo")
    assert payload["source"] == "local_simulated"
    assert payload["summary"]["openPositions"] >= 1


def test_observability_uses_local_diagnostics() -> None:
    status = observability_status()
    assert status["localLogs"]["enabled"] is True
    assert "posthog" not in status
