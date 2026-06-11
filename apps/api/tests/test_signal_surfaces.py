from __future__ import annotations


ALLOWED_ACTIONS = {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL", "NO_SIGNAL"}


def test_dashboard_and_asset_surfaces_show_valid_decision_signal(client) -> None:
    for mode in ("demo", "live"):
        dashboard = client.get(f"/api/v1/dashboard?mode={mode}&symbol=SPY")
        assert dashboard.status_code == 200
        dashboard_payload = dashboard.json()
        assert dashboard_payload["signal"]["action"] in ALLOWED_ACTIONS
        assert dashboard_payload["watchlist"]
        assert all(row["signal"] in ALLOWED_ACTIONS for row in dashboard_payload["watchlist"])

        asset = client.get(f"/api/v1/assets/SPY?mode={mode}")
        assert asset.status_code == 200
        asset_payload = asset.json()
        assert asset_payload["signal"]["action"] in ALLOWED_ACTIONS


def test_scanner_and_quality_surfaces_show_valid_decision_signal(client) -> None:
    scanner = client.get("/api/v1/scanner?mode=demo&min_confidence=0")
    assert scanner.status_code == 200
    scanner_payload = scanner.json()
    assert scanner_payload["results"]
    assert all(row["action"] in ALLOWED_ACTIONS for row in scanner_payload["results"])

    quality = client.get("/api/v1/signals/quality?mode=demo")
    assert quality.status_code == 200
    quality_payload = quality.json()
    assert all(row["action"] in ALLOWED_ACTIONS for row in quality_payload["rows"])
    assert all(item["action"] in ALLOWED_ACTIONS for item in quality_payload["actionDistribution"])
