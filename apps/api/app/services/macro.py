from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.repository import latest_macro_snapshot, save_macro_snapshot


DEFAULT_FRED_SERIES = {
    "DGS10": "10-Year Treasury Constant Maturity Rate",
    "T10YIE": "10-Year Breakeven Inflation Rate",
    "BAMLH0A0HYM2": "ICE BofA US High Yield Option-Adjusted Spread",
    "INDPRO": "Industrial Production Index",
    "UNRATE": "Unemployment Rate",
}


def macro_snapshot(session: Session, mode: str = "demo", persist: bool = True) -> dict:
    existing = latest_macro_snapshot(session, mode)
    if existing:
        return _serialize(existing)

    payload = deterministic_macro_snapshot(mode)
    if persist:
        saved = save_macro_snapshot(session, payload)
        return _serialize(saved)
    return payload


def deterministic_macro_snapshot(mode: str = "demo") -> dict:
    # Demo values are intentionally fixed so signal/backtest explanations are reproducible.
    components = {
        "series": {
            "DGS10": {"label": DEFAULT_FRED_SERIES["DGS10"], "latest": 4.18, "change90d": -0.24, "interpretation": "rates easing"},
            "T10YIE": {"label": DEFAULT_FRED_SERIES["T10YIE"], "latest": 2.28, "change90d": 0.05, "interpretation": "inflation expectations steady"},
            "BAMLH0A0HYM2": {"label": DEFAULT_FRED_SERIES["BAMLH0A0HYM2"], "latest": 3.72, "change90d": -0.18, "interpretation": "credit stress contained"},
            "INDPRO": {"label": DEFAULT_FRED_SERIES["INDPRO"], "latest": 103.4, "change90d": 0.31, "interpretation": "growth stable"},
            "UNRATE": {"label": DEFAULT_FRED_SERIES["UNRATE"], "latest": 4.0, "change90d": 0.0, "interpretation": "labour market balanced"},
        },
        "contribution": {"rates": 0.18, "inflation": -0.04, "credit": 0.16, "growth": 0.12, "labour": 0.02},
        "fredSeries": DEFAULT_FRED_SERIES,
    }
    risk_score = round(0.5 + sum(components["contribution"].values()), 2)
    if risk_score >= 0.65:
        regime = "risk_on"
    elif risk_score <= 0.4:
        regime = "risk_off"
    else:
        regime = "neutral"
    return {
        "mode": mode,
        "asOf": datetime.now(timezone.utc).isoformat(),
        "regime": regime,
        "riskScore": risk_score,
        "ratesTrend": "falling",
        "inflationPressure": "moderate",
        "creditStress": "contained",
        "growthMomentum": "stable",
        "summary": "Macro regime is neutral-to-risk-on: rates are easing, credit stress is contained, and growth momentum remains stable.",
        "components": components,
        "caveat": "Macro regime is a deterministic research overlay, not a timing model or return forecast.",
    }


def macro_signal_contribution(snapshot: dict) -> dict:
    if snapshot["regime"] == "risk_on":
        weight = 0.08
        label = "Macro risk-on support"
    elif snapshot["regime"] == "risk_off":
        weight = -0.12
        label = "Macro risk-off drag"
    else:
        weight = 0.0
        label = "Macro neutral"
    return {
        "code": "MACRO_REGIME",
        "label": label,
        "weight": weight,
        "detail": snapshot["summary"],
    }


def _serialize(snapshot) -> dict:
    return {
        "id": snapshot.id,
        "mode": snapshot.mode,
        "asOf": snapshot.created_at.replace(tzinfo=timezone.utc).isoformat(),
        "regime": snapshot.regime,
        "riskScore": snapshot.risk_score,
        "ratesTrend": snapshot.rates_trend,
        "inflationPressure": snapshot.inflation_pressure,
        "creditStress": snapshot.credit_stress,
        "growthMomentum": snapshot.growth_momentum,
        "summary": snapshot.summary,
        "components": snapshot.components_json,
        "caveat": "FRED data can be revised and released with delays; this overlay is contextual only.",
    }
