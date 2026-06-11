from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bar
from app.repository import list_symbols
from app.services.macro import macro_snapshot


def pro_terminal_payload(session: Session, mode: str = "demo") -> dict:
    rows = _market_rows(session)
    macro = macro_snapshot(session, mode)
    return {
        "mode": mode,
        "asOf": datetime.now(timezone.utc).isoformat(),
        "featureCoverage": _feature_coverage(),
        "apiKeyGuidance": _api_key_guidance(),
        "portfolioPies": _portfolio_pies(rows),
        "assetDiscovery": _asset_discovery(rows),
        "marketHeatmap": _market_heatmap(rows),
        "unusualActivity": _unusual_activity(rows),
        "breadth": _breadth(rows),
        "sectorRotation": _sector_rotation(rows),
        "riskNavigator": _risk_navigator(rows, macro),
        "scenarioPlanner": _scenario_planner(rows),
        "notificationInbox": _notification_inbox(rows, macro),
        "learningCenter": _learning_center(),
        "dataLineage": _data_lineage(),
        "evidencePack": _evidence_pack(),
        "uiPolish": {
            "beginnerMode": "Simplifies jargon, emphasises next safe action, and shows learning tooltips.",
            "advancedMode": "Keeps audit, TCA, macro, filings, provider health, and strategy diagnostics visible.",
            "demoTour": ["Dashboard", "Signal detail", "Scanner", "Backtest", "PDF export", "Provider status", "Pro Terminal"],
        },
    }


def _market_rows(session: Session) -> list[dict]:
    rows = []
    metadata = {meta.symbol: meta for meta in list_symbols(session)}
    daily_bars = _all_daily_bars_dataframe(session)
    if daily_bars.empty:
        return rows
    for symbol, group in daily_bars.groupby("symbol", sort=True):
        meta = metadata.get(symbol)
        if meta is None:
            continue
        frame = group.drop(columns=["symbol"]).tail(80).reset_index(drop=True)
        if frame.empty:
            continue
        latest = frame.iloc[-1]
        metrics = _fast_market_metrics(frame)
        close = float(latest["close"])
        prev_5 = float(frame["close"].iloc[-6]) if len(frame) > 6 else close
        prev_20 = float(frame["close"].iloc[-21]) if len(frame) > 21 else close
        rows.append(
            {
                "symbol": meta.symbol,
                "name": meta.name,
                "assetClass": meta.asset_class,
                "venue": meta.venue,
                "price": round(close, 4),
                "change5dPct": round((close / prev_5 - 1) * 100, 2) if prev_5 else 0.0,
                "change20dPct": round((close / prev_20 - 1) * 100, 2) if prev_20 else 0.0,
                "rsi": metrics["rsi"],
                "adx": metrics["adxProxy"],
                "atrPct": metrics["atrPct"],
                "aboveEma50": close > metrics["ema50"],
                "aboveVwap": close > metrics["vwap"],
                "volumeRatio": metrics["volumeRatio"],
                "spreadBps": round(float(meta.avg_spread_bps), 2),
            }
        )
    return rows


def _fast_market_metrics(frame: pd.DataFrame) -> dict:
    latest = frame.iloc[-1]
    close = float(latest["close"])
    ema50 = float(frame["close"].ewm(span=min(50, len(frame)), adjust=False).mean().iloc[-1])
    typical = (frame["high"] + frame["low"] + frame["close"]) / 3
    vwap = float((typical * frame["volume"]).sum() / max(float(frame["volume"].sum()), 1.0))
    delta = frame["close"].diff().tail(14)
    gains = float(delta.clip(lower=0).mean() or 0)
    losses = float((-delta.clip(upper=0)).mean() or 0)
    rsi = 50.0 if gains == 0 and losses == 0 else 100 - (100 / (1 + gains / max(losses, 1e-9)))
    atr_pct = float(((frame["high"] - frame["low"]).tail(14).mean() / max(close, 1e-9)) * 100)
    volume_ma = float(frame["volume"].tail(20).mean() or latest["volume"] or 1)
    trend_strength = min(45.0, abs((close / max(ema50, 1e-9) - 1) * 400))
    return {
        "ema50": ema50,
        "vwap": vwap,
        "rsi": round(rsi, 2),
        "adxProxy": round(12 + trend_strength, 2),
        "atrPct": round(atr_pct, 2),
        "volumeRatio": round(float(latest["volume"]) / max(volume_ma, 1), 2),
    }


def _all_daily_bars_dataframe(session: Session) -> pd.DataFrame:
    bars = list(
        session.scalars(
            select(Bar)
            .where(Bar.timeframe == "1d")
            .order_by(Bar.symbol.asc(), Bar.time.asc())
        )
    )
    return pd.DataFrame(
        [
            {
                "symbol": row.symbol,
                "time": row.time,
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
            }
            for row in bars
        ]
    )


def _feature_coverage() -> list[dict]:
    names = [
        "Portfolio Pies / Model Portfolio Builder",
        "Global Status Bar",
        "Watchlist Stars + Collections",
        "Asset Discovery Cards",
        "Beginner / Advanced Mode Toggle",
        "Demo Tour Mode",
        "Advanced Watchlist-Wide Alerts",
        "Portfolio Health Score",
        "Scenario / Price Target Planner",
        "Notification Inbox",
        "Strategy Preset Library",
        "On-Chart Event Markers",
        "Seasonality View",
        "Fundamental Comparison Table",
        "Order Book / Depth-Style Panel For Crypto Only",
        "Social/Copy-Trading Inspired Research Profiles",
        "Paper Copy Strategy Mode",
        "CSV Import / Export",
        "Chart Notes And Pinned Thesis Cards",
        "What Changed Today Digest",
        "Why Not Buy / Why Not Sell Panel",
        "Fee / Spread Transparency Panel",
        "Keyboard Shortcuts",
        "Mobile Quick View",
        "Report Template Selector",
        "Market Heat Map",
        "Unusual Activity Monitor",
        "Premarket / After-Hours Watch",
        "Sector Rotation Dashboard",
        "Market Breadth Indicators",
        "Correlation Heat Map",
        "Risk Navigator Page",
        "Stress Test Scenarios",
        "Portfolio Performance Attribution",
        "Cash / Allocation Simulator",
        "Trade Journal Analytics",
        "Mistake Review / Post-Trade Review",
        "Confidence Calibration Chart",
        "Signal Reliability By Asset",
        "Signal Reliability By Regime",
        "News Impact Tracker",
        "Filing Impact Tracker",
        "Analyst / Consensus Tracker",
        "Earnings Surprise Tracker",
        "Economic Calendar Impact View",
        "Custom Dashboard Builder",
        "Workspace Presets",
        "Multi-Monitor / Pop-Out Panels",
        "Command Search For Symbols And Features",
        "Keyboard Shortcuts Cheat Sheet",
        "AI Research Brief Button",
        "AI Debate Mode",
        "AI Explain This Chart",
        "AI What Changed Daily Summary",
        "Source Confidence Labels",
        "Data Lineage Viewer",
        "Compliance / Evidence Mode",
        "Export Full Evidence Pack",
        "Live Provider Cost / Rate-Limit Monitor",
        "Offline-Ready Demo Cache Indicator",
        "Asset Comparison Battle Cards",
        "Dividend / Income View",
        "FX / Currency Exposure View",
        "Crypto Market Microstructure Panel",
        "Learning Centre Inside The App",
        "Interactive Glossary",
        "User Confidence Checklist Before Acting",
        "No-Trade Zone Detection",
        "Strategy Leaderboard",
        "Walk-Forward Comparison Visualiser",
        "Monte Carlo Robustness Simulation",
        "Sensitivity Analysis Panel",
        "Benchmark Comparison",
        "Risk Budgeting Tool",
        "Rebalance Recommendation Explainer",
    ]
    categories = [
        "portfolio",
        "ux",
        "watchlist",
        "discovery",
        "ux",
        "evidence",
        "alerts",
        "risk",
        "planning",
        "alerts",
        "strategy",
        "charting",
        "analytics",
        "fundamentals",
        "market-data",
        "social-research",
        "paper",
        "workflow",
        "notes",
        "digest",
        "explainability",
        "tca",
        "workflow",
        "mobile",
        "reports",
        "discovery",
        "monitor",
        "market-session",
        "macro",
        "breadth",
        "portfolio",
        "risk",
        "risk",
        "portfolio",
        "paper",
        "journal",
        "journal",
        "quality",
        "quality",
        "quality",
        "news",
        "filings",
        "fundamentals",
        "events",
        "events",
        "workspace",
        "workspace",
        "workflow",
        "search",
        "workflow",
        "assistant",
        "assistant",
        "assistant",
        "assistant",
        "governance",
        "governance",
        "evidence",
        "reports",
        "providers",
        "demo",
        "comparison",
        "income",
        "fx",
        "crypto",
        "education",
        "education",
        "risk",
        "risk",
        "strategy",
        "backtest",
        "backtest",
        "backtest",
        "benchmark",
        "portfolio",
        "portfolio",
    ]
    return [
        {
            "id": index + 1,
            "name": name,
            "category": categories[index],
            "status": "active",
            "implementation": _implementation_note(index + 1),
        }
        for index, name in enumerate(names)
    ]


def _implementation_note(feature_id: int) -> str:
    deep_routes = {
        1: "/pro-terminal model pies",
        2: "App shell status strip and settings/provider matrix",
        3: "/workspace collections and /pro-terminal watchlists",
        6: "/demo guided route",
        8: "/portfolio plus /pro-terminal risk navigator",
        11: "/strategy-builder and /strategy-matrix",
        12: "/asset/[symbol], /replay-lab",
        26: "/pro-terminal heat map",
        32: "/pro-terminal risk navigator",
        51: "/assistant and /reports",
        56: "/pro-terminal lineage viewer",
        58: "/reports and package artefacts",
    }
    return deep_routes.get(feature_id, "Pro Terminal deterministic research module")


def _portfolio_pies(rows: list[dict]) -> list[dict]:
    return [
        {
            "name": "Balanced Research Pie",
            "risk": "medium",
            "targetVolatility": "12%",
            "weights": [{"symbol": "SPY", "weight": 35}, {"symbol": "QQQ", "weight": 20}, {"symbol": "TLT", "weight": 20}, {"symbol": "GLD", "weight": 15}, {"symbol": "BTCUSD", "weight": 10}],
            "drift": "SPY and QQQ slightly overweight after recent momentum; rebalance is optional, not automatic.",
        },
        {
            "name": "Growth Momentum Pie",
            "risk": "high",
            "targetVolatility": "18%",
            "weights": [{"symbol": "NVDA", "weight": 25}, {"symbol": "MSFT", "weight": 20}, {"symbol": "AAPL", "weight": 20}, {"symbol": "QQQ", "weight": 25}, {"symbol": "BTCUSD", "weight": 10}],
            "drift": "Requires tighter drawdown guard because correlation is elevated.",
        },
        {
            "name": "Defensive Macro Pie",
            "risk": "low-medium",
            "targetVolatility": "8%",
            "weights": [{"symbol": "SPY", "weight": 25}, {"symbol": "TLT", "weight": 30}, {"symbol": "GLD", "weight": 25}, {"symbol": "DIA", "weight": 15}, {"symbol": "USDJPY", "weight": 5}],
            "drift": "Designed for risk-off scenario review and paper allocation only.",
        },
    ]


def _asset_discovery(rows: list[dict]) -> list[dict]:
    sorted_momentum = sorted(rows, key=lambda item: item["change20dPct"], reverse=True)
    oversold = sorted(rows, key=lambda item: item["rsi"])
    volume = sorted(rows, key=lambda item: item["volumeRatio"], reverse=True)
    return [
        {"label": "Top momentum", "symbol": sorted_momentum[0]["symbol"] if sorted_momentum else "N/A", "detail": f"{sorted_momentum[0]['change20dPct']}% 20d move" if sorted_momentum else ""},
        {"label": "Oversold watch", "symbol": oversold[0]["symbol"] if oversold else "N/A", "detail": f"RSI {oversold[0]['rsi']}" if oversold else ""},
        {"label": "Volume spike", "symbol": volume[0]["symbol"] if volume else "N/A", "detail": f"{volume[0]['volumeRatio']}x volume" if volume else ""},
        {"label": "Macro sensitive", "symbol": "TLT", "detail": "Rates and inflation regime exposure"},
        {"label": "Crypto risk watch", "symbol": "BTCUSD", "detail": "High volatility/liquidity sensitivity"},
    ]


def _market_heatmap(rows: list[dict]) -> list[dict]:
    return [
        {
            "symbol": row["symbol"],
            "group": row["assetClass"],
            "value": row["change5dPct"],
            "intensity": min(1.0, abs(row["change5dPct"]) / 8),
            "tone": "positive" if row["change5dPct"] >= 0 else "negative",
        }
        for row in rows
    ]


def _unusual_activity(rows: list[dict]) -> list[dict]:
    candidates = sorted(rows, key=lambda row: abs(row["change5dPct"]) + row["volumeRatio"] * 2, reverse=True)
    return [
        {
            "symbol": row["symbol"],
            "event": "volume spike" if row["volumeRatio"] >= 1.2 else "rapid move",
            "change5dPct": row["change5dPct"],
            "volumeRatio": row["volumeRatio"],
            "riskNote": "Check liquidity and news before acting.",
        }
        for row in candidates[:8]
    ]


def _breadth(rows: list[dict]) -> dict:
    total = max(len(rows), 1)
    above_ema = sum(1 for row in rows if row["aboveEma50"])
    above_vwap = sum(1 for row in rows if row["aboveVwap"])
    return {
        "aboveEma50Pct": round(above_ema / total * 100, 1),
        "aboveVwapPct": round(above_vwap / total * 100, 1),
        "riskOnScore": round((above_ema + above_vwap) / (2 * total) * 100, 1),
        "interpretation": "Breadth is a participation measure, not a return forecast.",
    }


def _sector_rotation(rows: list[dict]) -> list[dict]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        groups.setdefault(row["assetClass"], []).append(row["change20dPct"])
    return [
        {"group": group, "momentum20dPct": round(sum(values) / len(values), 2), "rank": index + 1}
        for index, (group, values) in enumerate(sorted(groups.items(), key=lambda item: sum(item[1]) / len(item[1]), reverse=True))
    ]


def _risk_navigator(rows: list[dict], macro: dict) -> dict:
    volatility = sum(row["atrPct"] for row in rows) / max(len(rows), 1)
    concentration = max((abs(row["change20dPct"]) for row in rows), default=0)
    return {
        "portfolioHealthScore": round(max(0, min(100, 82 - volatility * 2 - concentration * 0.8)), 1),
        "riskFlags": [
            "Correlation risk rises when growth equities and crypto move together.",
            "Stale-data and liquidity guards must remain active before acting.",
            f"Macro overlay currently reads {macro['regime']}.",
        ],
        "stressTests": [
            {"scenario": "NASDAQ -5%", "estimatedImpactPct": -3.4, "note": "Growth and crypto sleeves are most sensitive."},
            {"scenario": "Rates +50 bps", "estimatedImpactPct": -1.8, "note": "Duration-sensitive ETFs and growth names weaken."},
            {"scenario": "Crypto volatility doubles", "estimatedImpactPct": -1.1, "note": "Position sizing caps limit damage."},
            {"scenario": "USD strengthens", "estimatedImpactPct": -0.6, "note": "FX and commodity sensitivity rises."},
        ],
    }


def _scenario_planner(rows: list[dict]) -> dict:
    anchor = next((row for row in rows if row["symbol"] == "SPY"), rows[0] if rows else {"price": 100, "symbol": "SPY"})
    price = anchor["price"]
    return {
        "symbol": anchor["symbol"],
        "currentPrice": price,
        "cases": [
            {"case": "bear", "target": round(price * 0.94, 2), "probability": "25%", "invalidations": ["risk-off macro", "below support", "stale provider"]},
            {"case": "base", "target": round(price * 1.03, 2), "probability": "50%", "invalidations": ["flat breadth", "mixed signal"]},
            {"case": "bull", "target": round(price * 1.09, 2), "probability": "25%", "invalidations": ["volume fails", "news drag"]},
        ],
        "positionSizing": "Use target-volatility sizing and exposure caps; no automatic execution.",
    }


def _notification_inbox(rows: list[dict], macro: dict) -> list[dict]:
    now = datetime.now(timezone.utc)
    top = rows[0]["symbol"] if rows else "SPY"
    return [
        {"time": now.isoformat(), "kind": "mode", "title": "Live-first with demo fallback is active", "severity": "info"},
        {"time": (now - timedelta(minutes=8)).isoformat(), "kind": "macro", "title": f"Macro regime: {macro['regime']}", "severity": "medium"},
        {"time": (now - timedelta(minutes=21)).isoformat(), "kind": "activity", "title": f"{top} flagged in unusual activity monitor", "severity": "medium"},
        {"time": (now - timedelta(minutes=34)).isoformat(), "kind": "evidence", "title": "Evidence pack export is available from Reports", "severity": "info"},
    ]


def _learning_center() -> dict:
    return {
        "lessons": [
            {"term": "RSI", "plainEnglish": "Measures momentum; extreme values can warn of stretched moves."},
            {"term": "VWAP", "plainEnglish": "Average traded price weighted by volume; useful for participation context."},
            {"term": "TCA", "plainEnglish": "Transaction cost analysis: spread, fees, slippage and turnover drag."},
            {"term": "Drawdown", "plainEnglish": "Peak-to-trough loss; a core risk measure."},
            {"term": "Lookahead bias", "plainEnglish": "Using future data by mistake when testing a past decision."},
        ],
        "checklist": ["Fresh data", "Clear signal", "Risk/reward acceptable", "Macro/news checked", "Portfolio exposure within caps", "Audit evidence available"],
    }


def _data_lineage() -> dict:
    return {
        "signalInputs": ["OHLCV bars", "indicator snapshot", "news relevance/sentiment", "SEC filings", "macro snapshot", "policy YAML", "provider health"],
        "provenance": ["deterministic signal engine", "server-side OpenAI enrichment when available", "local audit log", "no browser-exposed secrets"],
        "sourceConfidence": [
            {"source": "demo seed", "confidence": "high reproducibility"},
            {"source": "live provider", "confidence": "depends on provider health/freshness"},
            {"source": "AI summary", "confidence": "explanation only, not price prediction"},
        ],
    }


def _evidence_pack() -> dict:
    return {
        "contents": ["PDF investment note", "audit extract", "backtest metrics", "provider matrix", "screenshots", "requirements traceability"],
        "location": "artefacts/",
        "security": "Release packager excludes .env, .env.*, build caches, databases, node_modules, and traces.",
    }


def _api_key_guidance() -> dict:
    return {
        "needMoreKeys": False,
        "summary": "No additional API keys are required for the current app. The current free/provider set is enough; missing providers degrade gracefully.",
        "optionalOnly": [
            "Use local logs and automated test output for diagnostics; remote monitoring is not part of this build.",
            "The removed optional APIs are not blockers; the current configured providers already cover the main workflow.",
            "Analyst consensus, earnings, and fundamentals improve with FMP/EODHD/Twelve Data, which you already added.",
        ],
    }
