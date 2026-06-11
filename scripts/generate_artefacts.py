from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = ROOT / "apps" / "api"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / 'markets_strategy_copilot.db'}")
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db import get_session, init_db  # noqa: E402
from app.demo_store import seed_demo_database  # noqa: E402
from app.main import app  # noqa: E402
from app.repository import bars_dataframe  # noqa: E402
from app.services.backtest import PRESETS  # noqa: E402
from app.services.live_refresh import provider_budget_snapshot  # noqa: E402
from app.services.provider_checks import run_provider_checks  # noqa: E402
from app.services.providers import provider_matrix  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _run_backtest(client: TestClient, preset: str, ablation: str = "technical_news_tca") -> dict:
    response = client.post(
        "/api/v1/backtests/run",
        json={
            "symbol": "SPY",
            "timeframe": "1d",
            "preset": preset,
            "feesBps": 2.0,
            "spreadBps": 2.0,
            "slippageBps": 1.0,
            "longShort": False,
            "ablation": ablation,
        },
    )
    response.raise_for_status()
    return response.json()


def _benchmark_buy_hold() -> dict:
    for session in get_session():
        frame = bars_dataframe(session, "SPY", "1d")
        if frame.empty:
            return {"symbol": "SPY", "totalReturn": 0.0, "notes": "No daily bars available."}
        first = float(frame["close"].iloc[0])
        last = float(frame["close"].iloc[-1])
        total_return = (last / first - 1.0) if first else 0.0
        return {
            "symbol": "SPY",
            "start": str(frame["time"].iloc[0]),
            "end": str(frame["time"].iloc[-1]),
            "totalReturn": round(total_return, 6),
            "notes": "Deterministic buy-and-hold benchmark from seeded daily bars.",
        }
    return {"symbol": "SPY", "totalReturn": 0.0, "notes": "Database session unavailable."}


def _provider_health_demo() -> dict:
    rows = provider_matrix("demo")
    checks = [
        {
            "name": row["name"],
            "label": row["label"],
            "configured": row["configuredKeys"] == row["requiredKeys"],
            "status": row["status"],
            "lastChecked": _now_iso(),
            "latencyMs": 0,
            "note": row["detail"],
        }
        for row in rows
    ]
    return {
        "mode": "demo",
        "generatedAt": _now_iso(),
        "checks": checks,
        "summary": _count_statuses(checks),
        "notes": ["Demo provider health is deterministic and does not make live network calls."],
    }


async def _provider_health_live() -> dict:
    try:
        payload = await run_provider_checks(timeout_seconds=4.0)
    except Exception as exc:  # noqa: BLE001 - artefact generation must record degradation honestly.
        rows = provider_matrix("live")
        checks = [
            {
                "name": row["name"],
                "label": row["label"],
                "configured": row["configuredKeys"] == row["requiredKeys"],
                "status": "manual-check-needed" if row["configuredKeys"] else "missing",
                "lastChecked": _now_iso(),
                "latencyMs": None,
                "note": f"Provider check runner failed safely: {type(exc).__name__}",
            }
            for row in rows
        ]
        return {
            "mode": "live",
            "generatedAt": _now_iso(),
            "checks": checks,
            "summary": _count_statuses(checks),
            "notes": ["Live checks could not complete automatically; no secrets were exposed."],
        }
    payload["mode"] = "live"
    payload["generatedAt"] = payload.get("generatedAt") or _now_iso()
    return payload


def _count_statuses(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def main() -> None:
    init_db()
    for session in get_session():
        seed_demo_database(session)

    artefacts = ROOT / "artefacts"
    exports = artefacts / "exports"
    artefacts.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)

    with TestClient(app) as client:
        dashboard = client.get("/api/v1/dashboard?mode=demo&symbol=SPY").json()
        audit = client.get("/api/v1/audit/SPY").json()
        providers = client.get("/api/v1/providers/status?mode=live").json()
        portfolio = client.get("/api/v1/portfolio?mode=demo").json()

        preset_runs = []
        for preset in PRESETS:
            run = _run_backtest(client, preset)
            preset_runs.append(
                {
                    "preset": preset,
                    "metrics": run["metrics"],
                    "tradeCount": len(run.get("trades") or []),
                    "walkForwardWindows": len(run.get("walkForward") or []),
                }
            )

        best_run = max(
            preset_runs,
            key=lambda item: (
                float(item["metrics"].get("totalReturn") or 0),
                float(item["metrics"].get("sharpe") or 0),
            ),
        )
        worst_run = min(
            preset_runs,
            key=lambda item: (
                float(item["metrics"].get("totalReturn") or 0),
                float(item["metrics"].get("sharpe") or 0),
            ),
        )
        ablation_runs = []
        for ablation in ["technical_only", "technical_news", "technical_news_tca"]:
            run = _run_backtest(client, str(best_run["preset"]), ablation)
            ablation_runs.append(
                {
                    "preset": best_run["preset"],
                    "ablation": ablation,
                    "metrics": run["metrics"],
                    "tradeCount": len(run.get("trades") or []),
                }
            )
        report = client.post(
            "/api/v1/reports/export",
            json={"symbol": "SPY", "mode": "demo", "preset": best_run["preset"]},
        ).json()

    benchmark = _benchmark_buy_hold()
    report_path = str(report["path"]).replace("\\", "/")
    report_file = ROOT / report_path
    if not report_file.exists():
        raise SystemExit(f"Report export did not create the referenced PDF: {report_path}")

    provider_demo = _provider_health_demo()
    provider_live = asyncio.run(_provider_health_live())
    provider_live["requestBudgets"] = provider_budget_snapshot()

    strategy_comparison = {
        "generatedAt": _now_iso(),
        "symbol": "SPY",
        "bestPreset": best_run,
        "worstPreset": worst_run,
        "benchmark": benchmark,
        "allPresets": preset_runs,
        "honestyNote": "Metrics are computed from deterministic seeded data; no performance result is fabricated.",
    }
    ablation_results = {
        "generatedAt": _now_iso(),
        "symbol": "SPY",
        "selectedPreset": best_run["preset"],
        "runs": ablation_runs,
        "honestyNote": "Ablations compare technical-only, technical plus news, and TCA-aware variants using the same deterministic engine.",
    }

    seeded_metrics = {
        "generatedAt": _now_iso(),
        "dashboardBacktestSummary": dashboard["backtestSummary"],
        "strategyTesterMetrics": best_run["metrics"],
        "bestPreset": best_run["preset"],
        "worstPreset": worst_run["preset"],
        "benchmark": benchmark,
        "macro": dashboard.get("macro"),
        "portfolioSummary": portfolio.get("summary"),
        "providerStatusCounts": {
            item["status"]: sum(1 for row in providers["providers"] if row["status"] == item["status"])
            for item in providers["providers"]
        },
        "reportPath": report_path,
    }

    _write_json(artefacts / "seeded_metrics.json", seeded_metrics)
    _write_json(artefacts / "audit-log-extract.json", audit[:12])
    _write_json(artefacts / "provider-health-demo.json", provider_demo)
    _write_json(artefacts / "provider-health-live.json", provider_live)
    _write_json(artefacts / "strategy-benchmark-comparison.json", strategy_comparison)
    _write_json(artefacts / "ablation-results.json", ablation_results)

    print("Generated final artefacts:")
    for path in [
        artefacts / "seeded_metrics.json",
        artefacts / "audit-log-extract.json",
        artefacts / "provider-health-demo.json",
        artefacts / "provider-health-live.json",
        artefacts / "strategy-benchmark-comparison.json",
        artefacts / "ablation-results.json",
        report_file,
    ]:
        print(path)


if __name__ == "__main__":
    main()
