from __future__ import annotations


def test_strategy_builder_and_rule_evaluation(client) -> None:
    response = client.get("/api/v1/strategy-builder/SPY?mode=demo")
    assert response.status_code == 200
    payload = response.json()
    assert payload["language"].startswith("Pine-lite")
    assert "RSI" in payload["supportedFields"]
    assert payload["templates"]

    evaluation = client.post(
        "/api/v1/strategy-builder/evaluate",
        json={"symbol": "SPY", "mode": "demo", "rule": "CLOSE > EMA50 AND RSI > 40"},
    )
    assert evaluation.status_code == 200
    result = evaluation.json()["evaluation"]
    assert result["totalClauses"] == 2
    assert "conditions" in result


def test_terminal_research_payloads(client) -> None:
    routes = [
        "/api/v1/terminal/multi-chart?symbols=SPY,AAPL,BTCUSD&timeframe=1d",
        "/api/v1/chart-workspace/SPY",
        "/api/v1/alerts/builder",
        "/api/v1/replay-lab/SPY?cursor=120",
        "/api/v1/scanner/columns",
        "/api/v1/compare?symbols=SPY,QQQ,AAPL",
        "/api/v1/events/calendar?mode=demo",
        "/api/v1/tear-sheet/AAPL?mode=demo",
        "/api/v1/patterns/SPY",
        "/api/v1/opportunities/ranked",
    ]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200, route
        assert response.json()


def test_terminal_payloads_do_not_expose_secret_shapes(client) -> None:
    response = client.get("/api/v1/events/calendar?mode=live")
    assert response.status_code == 200
    serialised = response.text.lower()
    assert "api_key" not in serialised
    assert "secret" not in serialised
    assert "bearer " not in serialised


def test_pro_terminal_covers_all_final_feature_additions(client) -> None:
    response = client.get("/api/v1/pro-terminal?mode=demo")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["featureCoverage"]) == 75
    assert payload["apiKeyGuidance"]["needMoreKeys"] is False
    assert payload["portfolioPies"]
    assert payload["marketHeatmap"]
    assert payload["riskNavigator"]["stressTests"]
    assert payload["dataLineage"]["signalInputs"]
