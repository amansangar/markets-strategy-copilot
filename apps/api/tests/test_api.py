from __future__ import annotations

from app.config import get_settings


def test_system_status_endpoint(client) -> None:
    response = client.get("/api/v1/system/status?mode=live")
    assert response.status_code == 200
    payload = response.json()
    assert "health" in payload
    assert isinstance(payload["technicalOnlyMode"], bool)
    assert "providers" in payload


def test_dashboard_endpoint(client) -> None:
    response = client.get("/api/v1/dashboard?mode=demo&symbol=SPY")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "demo"
    assert payload["watchlist"]
    assert payload["signal"]["symbol"] == "SPY"
    assert payload["signal"]["dataQuality"]["score"] >= 0
    assert payload["signal"]["waterfall"]["items"]
    assert payload["readiness"]["score"] >= 0
    assert payload["fallbackPlan"]


def test_live_dashboard_uses_fast_status_shell(client) -> None:
    response = client.get("/api/v1/dashboard?mode=live&symbol=SPY")
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "live"
    assert "provider" in payload["connectionSummary"].lower() or "live" in payload["connectionSummary"].lower()
    assert payload["health"]


def test_demo_briefing_endpoint(client) -> None:
    response = client.get("/api/v1/demo/briefing")
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Guided Research Walkthrough"
    assert payload["routeSequence"]
    assert payload["readinessScore"]["score"] >= 0
    assert payload["checklist"]
    assert payload["metrics"]["trackedAssets"] >= 4
    assert all("route" in item and "goal" in item for item in payload["routeSequence"])


def test_demo_warmup_endpoint_primes_safe_demo_paths(client) -> None:
    response = client.post("/api/v1/demo/warmup")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ready", "partial"}
    assert "dashboard SPY" in payload["warmed"]
    assert "default strategy tester" in payload["warmed"]
    assert payload["mode"] == "demo"


def test_system_readiness_endpoint(client) -> None:
    response = client.get("/api/v1/system/readiness?mode=demo")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ready", "review", "blocked"}
    assert payload["checks"]


def test_provider_status_and_checks_serialize(client, monkeypatch) -> None:
    status = client.get("/api/v1/providers/status?mode=demo")
    assert status.status_code == 200
    assert status.json()["providers"]
    assert status.json()["fallbackPlan"]
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
    ]:
        monkeypatch.setenv(key, "")
    get_settings.cache_clear()
    checks = client.get("/api/v1/providers/checks")
    assert checks.status_code == 200
    payload = checks.json()
    assert "checks" in payload
    assert all("configured" in item and "status" in item for item in payload["checks"])
    get_settings.cache_clear()
