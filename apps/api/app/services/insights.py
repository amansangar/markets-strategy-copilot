from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean

from sqlalchemy.orm import Session

from app.repository import list_alerts, list_reports, list_symbols
from app.services.providers import provider_matrix


def data_quality_score(signal: dict, health: list[dict], mode: str) -> dict:
    score = 100
    factors: list[dict] = []

    freshness = float(signal.get("dataFreshnessSeconds") or 0)
    if freshness <= 600:
        factors.append({"label": "Market-data freshness", "status": "pass", "impact": 0, "detail": "Latest bars are inside the freshness guardrail."})
    elif freshness <= 1800:
        score -= 18
        factors.append({"label": "Market-data freshness", "status": "watch", "impact": -18, "detail": "Bars are aging; confidence is penalised."})
    else:
        score -= 42
        factors.append({"label": "Market-data freshness", "status": "blocker", "impact": -42, "detail": "Bars are stale enough to suppress directional certainty."})

    provider_penalty = 0
    for item in health:
        status = item.get("status")
        if status in {"offline", "missing"}:
            provider_penalty += 10
        elif status == "degraded":
            provider_penalty += 5
    if provider_penalty:
        score -= provider_penalty
        factors.append({"label": "Provider health", "status": "watch", "impact": -provider_penalty, "detail": "One or more providers are degraded, missing, or offline."})
    else:
        factors.append({"label": "Provider health", "status": "pass", "impact": 0, "detail": "Required demo/live sources are reporting usable status."})

    news = signal.get("newsSnapshot", {})
    article_count = int(news.get("articleCount") or 0)
    relevance = float(news.get("relevance") or 0)
    if article_count == 0:
        score -= 8
        factors.append({"label": "News coverage", "status": "watch", "impact": -8, "detail": "No relevant articles were attached to this signal."})
    elif relevance < 0.15:
        score -= 4
        factors.append({"label": "News coverage", "status": "watch", "impact": -4, "detail": "News exists but relevance is weak."})
    else:
        factors.append({"label": "News coverage", "status": "pass", "impact": 0, "detail": f"{article_count} relevant article(s) are mapped to the symbol."})

    risk_penalty = 0
    for flag in signal.get("riskFlags", []):
        risk_penalty += {"high": 10, "medium": 5, "low": 2}.get(flag.get("severity"), 3)
    if signal.get("policyBlockers"):
        risk_penalty += 15
    if risk_penalty:
        score -= risk_penalty
        factors.append({"label": "Risk and policy gates", "status": "watch", "impact": -risk_penalty, "detail": "Risk flags or policy blockers reduce usable confidence."})
    else:
        factors.append({"label": "Risk and policy gates", "status": "pass", "impact": 0, "detail": "No active risk blockers are attached to the recommendation."})

    if mode == "demo":
        factors.append({"label": "Reproducibility", "status": "pass", "impact": 0, "detail": "Demo data is deterministic, so repeated local runs stay consistent."})

    bounded = max(0, min(100, score))
    label = "excellent" if bounded >= 88 else "good" if bounded >= 74 else "watch" if bounded >= 55 else "degraded"
    return {
        "score": bounded,
        "label": label,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "factors": factors,
    }


def signal_waterfall(signal: dict) -> dict:
    baseline = 45.0
    items = [{"label": "Base prior", "value": baseline, "kind": "base", "detail": "Neutral deterministic prior before evidence is applied."}]
    running = baseline

    for reason in signal.get("reasonCodes", [])[:8]:
        value = round(float(reason.get("weight") or 0) * 8, 2)
        running += value
        items.append({"label": reason.get("label", reason.get("code", "Reason")), "value": value, "kind": "positive" if value >= 0 else "negative", "detail": reason.get("detail", "")})

    for flag in signal.get("riskFlags", []):
        value = -{"high": 10, "medium": 5, "low": 2}.get(flag.get("severity"), 3)
        running += value
        items.append({"label": _human_code_label(flag.get("code", "Risk flag")), "value": value, "kind": "risk", "detail": flag.get("message", "")})

    if signal.get("policyBlockers"):
        value = -15
        running += value
        items.append({"label": "Policy blockers", "value": value, "kind": "risk", "detail": ", ".join(signal["policyBlockers"])})

    final_confidence = round(float(signal.get("confidence") or 0) * 100, 2)
    items.append({"label": "Model calibration", "value": round(final_confidence - running, 2), "kind": "calibration", "detail": "Maps raw evidence score into bounded confidence."})
    return {"baseline": baseline, "finalConfidence": final_confidence, "items": items}


def _human_code_label(code: str) -> str:
    labels = {
        "STALE_DATA": "Stale price data",
        "FILING_N-CSR": "Filing caution",
        "HIGH_VOLATILITY": "High volatility",
        "LOW_LIQUIDITY": "Liquidity watch",
    }
    if code in labels:
        return labels[code]
    return code.replace("_", " ").replace("-", " ").title()


def provider_fallback_plan(mode: str) -> list[dict]:
    rows = {row["name"]: row for row in provider_matrix(mode)}

    def item(name: str, role: str) -> dict:
        row = rows.get(name, {})
        return {
            "name": name,
            "label": row.get("label", name),
            "role": role,
            "status": row.get("status", "disabled"),
            "configured": bool(row.get("keyPresent")),
            "detail": row.get("detail", "Provider not registered."),
        }

    return [
        {
            "category": "Market data",
            "policy": "Use Polygon first for live bars; fall back to free-tier quote/EOD providers only when needed.",
            "providers": [item("polygon", "primary"), item("twelvedata", "fallback"), item("alphavantage", "fallback"), item("eodhd", "last-resort")],
        },
        {
            "category": "News and events",
            "policy": "Use NewsAPI for headline tape; Marketaux provides finance-news fallback/entity metadata.",
            "providers": [item("newsapi", "primary"), item("marketaux", "fallback"), item("sec", "filing-context")],
        },
        {
            "category": "Macro and research data",
            "policy": "Use FRED for macro regime; fall back to cached demo macro data when live macro data is unavailable.",
            "providers": [item("fred", "primary")],
        },
        {
            "category": "Crypto",
            "policy": "Use Polygon or deterministic demo crypto bars; show stale-data warnings instead of hiding uncertainty when crypto data is unavailable.",
            "providers": [item("polygon", "primary")],
        },
    ]


def system_readiness(session: Session, mode: str = "demo") -> dict:
    providers = provider_matrix(mode)
    required_names = {"polygon", "newsapi", "openai"}
    provider_blockers = [row for row in providers if row["name"] in required_names and row["status"] in {"offline", "missing"}]
    symbols = list_symbols(session)
    reports = list_reports(session)
    alerts = list_alerts(session)

    checks = [
        {"label": "Demo data seeded", "status": "ready" if len(symbols) >= 4 else "blocker", "detail": f"{len(symbols)} instruments available across asset classes."},
        {"label": "Decision-support guardrail", "status": "ready", "detail": "No real-money execution is implemented; portfolio actions are paper/local only."},
        {"label": "Provider transparency", "status": "ready", "detail": "Settings reports configured, degraded, missing, disabled, and manual-check-needed states without showing secrets."},
        {"label": "Investment note export", "status": "ready" if reports else "attention", "detail": "At least one PDF investment note has been created." if reports else "Create a sample PDF from Reports to confirm exports are ready for users."},
        {"label": "Alerts and audit", "status": "ready" if alerts else "attention", "detail": f"{len(alerts)} alert rule(s) are configured and audit logging covers recommendations."},
    ]
    blockers = sum(1 for item in checks if item["status"] == "blocker")
    attention = sum(1 for item in checks if item["status"] == "attention")
    score = max(0, 100 - blockers * 35 - attention * 10 - len(provider_blockers) * 8)
    return {
        "score": score,
        "status": "ready" if score >= 85 else "attention" if score >= 65 else "blocker",
        "checks": checks,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def portfolio_risk_heatmap(portfolio: dict) -> dict:
    gross = float(portfolio.get("summary", {}).get("grossExposure") or 0)
    cells = []
    for position in portfolio.get("positions", []):
        market_value = float(position.get("marketValue") or 0)
        weight = abs(market_value) / gross if gross else 0
        pnl_pct = float(position.get("unrealizedPnlPct") or 0)
        if weight > 0.45:
            level = "high"
        elif weight > 0.25 or pnl_pct < -0.04:
            level = "medium"
        else:
            level = "low"
        cells.append(
            {
                "symbol": position.get("symbol"),
                "weight": round(weight, 4),
                "marketValue": round(market_value, 2),
                "pnlPct": round(pnl_pct, 4),
                "riskLevel": level,
                "source": position.get("source"),
                "note": "Concentration watch" if weight > 0.25 else "Within demo exposure guardrails",
            }
        )
    return {"grossExposure": gross, "cells": cells}


def backtest_robustness(backtest: dict) -> dict:
    metrics = backtest.get("metrics", {})
    folds = backtest.get("walkForward", [])
    returns = [float(fold.get("return") or 0) for fold in folds]
    positive_folds = sum(1 for value in returns if value > 0)
    consistency = positive_folds / len(returns) if returns else 0.0
    max_drawdown = abs(float(metrics.get("maxDrawdown") or 0))
    turnover = float(metrics.get("turnover") or 0)
    total_return = float(metrics.get("totalReturn") or 0)
    estimated_extra_cost = turnover * 0.0005
    stress_return = total_return - estimated_extra_cost
    warnings = []
    if len(folds) < 2:
        warnings.append("Limited walk-forward folds; avoid over-interpreting the result.")
    if max_drawdown > 0.15:
        warnings.append("Drawdown exceeds the preferred 15% risk guardrail.")
    if turnover > 12:
        warnings.append("High turnover makes the strategy sensitive to costs and slippage.")
    if not warnings:
        warnings.append("No major robustness warning in this deterministic demo run.")
    score = max(0, min(100, 80 + consistency * 15 - max_drawdown * 100 - max(0, turnover - 8) * 2))
    return {
        "score": round(score, 1),
        "positiveFoldRatio": round(consistency, 4),
        "foldCount": len(folds),
        "costSensitivity": {
            "baseNetReturn": round(total_return, 6),
            "estimatedReturnWithPlus5BpsCost": round(stress_return, 6),
            "estimatedCostDrag": round(estimated_extra_cost, 6),
        },
        "warnings": warnings,
    }


def replay_scenarios(symbol: str) -> list[dict]:
    return [
        {"id": "breakout", "label": "Breakout watch", "cursor": 190, "detail": f"Replay {symbol} around a momentum/volume expansion window."},
        {"id": "risk_off", "label": "Risk-off check", "cursor": 90, "detail": "Inspect whether risk flags and confidence react before future bars are visible."},
        {"id": "mean_reversion", "label": "Mean reversion", "cursor": 135, "detail": "Show oscillator and Bollinger context without lookahead leakage."},
        {"id": "news_shock", "label": "News/event shock", "cursor": 220, "detail": "Review stored news/filing markers alongside the signal timeline."},
    ]
