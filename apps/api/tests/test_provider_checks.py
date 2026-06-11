from __future__ import annotations

import pytest

from app.config import get_settings
from app.db import get_session
from app.services.provider_checks import run_provider_checks
from app.services import live_refresh


@pytest.mark.asyncio
async def test_provider_checks_report_missing_without_network(monkeypatch) -> None:
    for key in [
        "OPENAI_API_KEY",
        "POLYGON_API_KEY",
        "NEWSAPI_API_KEY",
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "FRED_API_KEY",
        "SEC_USER_AGENT",
        "FINNHUB_API_KEY",
        "ALPHAVANTAGE_API_KEY",
        "FMP_API_KEY",
        "TWELVEDATA_API_KEY",
        "MARKETAUX_API_KEY",
        "EODHD_API_KEY",
        "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
        "CLERK_SECRET_KEY",
        "RESEND_API_KEY",
        "RESEND_FROM_EMAIL",
    ]:
        monkeypatch.setenv(key, "")
    get_settings.cache_clear()
    payload = await run_provider_checks(timeout_seconds=0.1)
    statuses = {item["name"]: item["status"] for item in payload["checks"]}
    assert statuses["openai"] == "missing"
    assert statuses["polygon"] == "missing"
    assert statuses["resend"] == "disabled"
    assert "sentry" not in statuses
    get_settings.cache_clear()


def test_newsapi_budget_blocks_repeat_requests(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, url: str) -> None:
            self.url = url

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "articles": [
                    {
                        "title": f"SPY budget smoke {self.url}",
                        "description": "Budget test article.",
                        "url": f"https://example.test/{abs(hash(self.url))}",
                        "publishedAt": "2026-05-04T12:00:00Z",
                        "source": {"name": "Budget Test"},
                    }
                ]
            }

    class FakeClient:
        calls = 0

        def __init__(self, *args, **kwargs) -> None:
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def get(self, url: str, params: dict):
            FakeClient.calls += 1
            return FakeResponse(f"{url}-{FakeClient.calls}")

    monkeypatch.setenv("NEWSAPI_API_KEY", "configured-for-test")
    get_settings.cache_clear()
    live_refresh._PROVIDER_BUDGETS.clear()
    monkeypatch.setattr(live_refresh.httpx, "Client", FakeClient)

    for session in get_session():
        live_refresh._refresh_news(session, "SPY", "SPDR S&P 500 ETF Trust")
        first_call_count = FakeClient.calls
        assert first_call_count == 2
        live_refresh._refresh_news(session, "SPY", "SPDR S&P 500 ETF Trust")
        assert FakeClient.calls == first_call_count
        snapshot = live_refresh.provider_budget_snapshot()
        assert any(row["provider"] == "newsapi" and row["scope"] == "symbol:SPY" for row in snapshot)
        break

    get_settings.cache_clear()
    live_refresh._PROVIDER_BUDGETS.clear()
