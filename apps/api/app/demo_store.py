from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Alert, AlertDeliveryLog, JournalEntry, MacroSnapshot, PortfolioOrder, PortfolioPosition, SecFiling, WorkspacePreference, Bar, NewsArticle, Symbol


def _read_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def demo_paths() -> dict[str, Path]:
    root = get_settings().resolved_data_dir / "demo"
    return {
        "symbols": root / "symbols.json",
        "bars_1d": root / "bars_1d.json",
        "bars_5m": root / "bars_5m.json",
        "news": root / "news.json",
        "policy": root / "policy.yml",
    }


def seed_demo_database(session: Session) -> None:
    paths = demo_paths()
    now = datetime.now(timezone.utc)

    existing_symbols = set(session.scalars(select(Symbol.symbol)).all())
    symbol_rows = _read_json(paths["symbols"])
    missing_symbols = {row["symbol"] for row in symbol_rows if row["symbol"] not in existing_symbols}

    if missing_symbols:
        for row in symbol_rows:
            if row["symbol"] not in missing_symbols:
                continue
            session.add(Symbol(**row))

        for path_key in ("bars_1d", "bars_5m"):
            for row in _read_json(paths[path_key]):
                if row["symbol"] not in missing_symbols:
                    continue
                session.add(
                    Bar(
                        symbol=row["symbol"],
                        timeframe=row["timeframe"],
                        time=datetime.fromisoformat(row["time"]),
                        open=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=row["volume"],
                    )
                )

    existing_news_ids = set(session.scalars(select(NewsArticle.id)).all())
    for row in _read_json(paths["news"]):
        if row["id"] not in existing_news_ids:
            session.add(
                NewsArticle(
                    id=row["id"],
                    source=row["source"],
                    title=row["title"],
                    description=row["description"],
                    url=row["url"],
                    published_at=datetime.fromisoformat(row["published_at"]),
                    symbols_csv=",".join(row["symbols"]),
                    raw_sentiment=row["raw_sentiment"],
                    relevance=row["relevance"],
                    enrichment_json=None,
                )
            )

    if not session.scalar(select(Alert).limit(1)):
        alerts = [
            Alert(
                symbol="SPY",
                kind="price",
                name="SPY breakout above 20d high",
                enabled=True,
                rule_json={"type": "price_breakout", "level": "rolling_20_high"},
                history_json=[],
            ),
            Alert(
                symbol="BTCUSD",
                kind="signal",
                name="BTC momentum confluence",
                enabled=True,
                rule_json={"type": "signal", "preset": "Momentum Confirmation", "minConfidence": 0.72},
                history_json=[],
            ),
        ]
        session.add_all(alerts)

    if not session.scalar(select(MacroSnapshot).limit(1)):
        session.add(
            MacroSnapshot(
                mode="demo",
                regime="neutral",
                risk_score=0.54,
                rates_trend="falling",
                inflation_pressure="moderate",
                credit_stress="contained",
                growth_momentum="stable",
                summary="Demo macro tape is neutral-to-risk-on: rates are easing, credit stress is contained, and growth momentum is stable.",
                components_json={
                    "series": {
                        "DGS10": {"label": "10Y Treasury yield", "latest": 4.18, "change90d": -0.24},
                        "T10YIE": {"label": "10Y breakeven inflation", "latest": 2.28, "change90d": 0.05},
                        "BAMLH0A0HYM2": {"label": "High-yield OAS", "latest": 3.72, "change90d": -0.18},
                        "INDPRO": {"label": "Industrial production", "latest": 103.4, "change90d": 0.31},
                    },
                    "contribution": {"rates": 0.18, "inflation": -0.04, "credit": 0.16, "growth": 0.12},
                },
            )
        )

    if not session.scalar(select(SecFiling).limit(1)):
        filings = [
            ("SPY", "N-CSR", "Annual shareholder report filed; review holdings concentration and expense disclosures.", "medium"),
            ("AAPL", "10-Q", "Quarterly filing: monitor revenue mix, buyback cadence, and regulatory risk language.", "medium"),
            ("MSFT", "10-K", "Annual filing: cloud concentration, AI capex, and cybersecurity risk factors remain relevant.", "medium"),
            ("BTCUSD", "8-K", "Crypto proxy event marker: exchange/liquidity risk flagged for demo context.", "high"),
            ("GLD", "10-Q", "Commodity trust filing: custody, expense, and liquidity disclosures updated.", "low"),
        ]
        for index, (symbol, filing_type, digest, risk) in enumerate(filings):
            filed_at = now - timedelta(days=7 + index * 13)
            session.add(
                SecFiling(
                    id=f"demo-{symbol}-{filing_type}-{index}",
                    symbol=symbol,
                    accession_number=f"0000000000-26-{index:06d}",
                    filing_type=filing_type,
                    filed_at=filed_at,
                    title=f"{symbol} {filing_type} event intelligence",
                    url=f"https://www.sec.gov/edgar/search/#/{symbol}",
                    risk_level=risk,
                    digest=digest,
                    facts_json={"demo": True, "source": "seeded SEC-style event marker"},
                )
            )

    if not session.scalar(select(PortfolioPosition).limit(1)):
        session.add_all(
            [
                PortfolioPosition(workspace_id="local", symbol="SPY", quantity=8, avg_price=512.25, last_price=520.7, source="local_simulated"),
                PortfolioPosition(workspace_id="local", symbol="GLD", quantity=12, avg_price=191.1, last_price=194.4, source="local_simulated"),
                PortfolioPosition(workspace_id="local", symbol="BTCUSD", quantity=0.04, avg_price=64750.0, last_price=67120.0, source="local_simulated"),
            ]
        )
        session.add_all(
            [
                PortfolioOrder(workspace_id="local", symbol="SPY", side="BUY", quantity=8, price=512.25, status="filled", source="local_simulated", reason_codes_json=[{"code": "TREND"}], note="Demo paper entry linked to trend confluence."),
                PortfolioOrder(workspace_id="local", symbol="GLD", side="BUY", quantity=12, price=191.1, status="filled", source="local_simulated", reason_codes_json=[{"code": "RISK_HEDGE"}], note="Portfolio hedge sleeve."),
            ]
        )
        session.add(
            JournalEntry(
                workspace_id="local",
                symbol="SPY",
                entry_type="trade_note",
                title="Initial demo portfolio thesis",
                body="Local simulated portfolio only. Position sizing follows risk caps and does not represent a broker order.",
            )
        )

    if not session.scalar(select(WorkspacePreference).limit(1)):
        session.add_all(
            [
                WorkspacePreference(workspace_id="local", kind="watchlist", name="Core cross-asset board", payload_json={"symbols": ["SPY", "AAPL", "MSFT", "BTCUSD", "GLD"]}),
                WorkspacePreference(workspace_id="local", kind="scanner", name="High-confidence confluence", payload_json={"action": "BUY", "minConfidence": 0.68, "regime": "not-risk-off"}),
                WorkspacePreference(workspace_id="local", kind="chart_layout", name="Trend + momentum research", payload_json={"overlays": ["EMA21", "EMA50", "VWAP"], "panes": ["RSI", "MACD"]}),
                WorkspacePreference(workspace_id="local", kind="symbol_note", name="SPY macro sensitivity", payload_json={"symbol": "SPY", "note": "Watch rates trend and credit stress before upgrading size."}),
            ]
        )

    if not session.scalar(select(AlertDeliveryLog).limit(1)):
        session.add(
            AlertDeliveryLog(
                alert_id="demo-bootstrap",
                channel="browser",
                status="delivered",
                dedupe_key="demo-bootstrap",
                detail="Seeded browser alert delivery log. Email delivery remains disabled unless Resend is configured.",
            )
        )
    session.commit()
