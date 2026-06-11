from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from app.services.backtest import run_backtest


def test_backtest_is_deterministic() -> None:
    bars = pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=320, freq="B", tz="UTC"),
            "open": [100 + index * 0.05 for index in range(320)],
            "high": [100.5 + index * 0.05 for index in range(320)],
            "low": [99.7 + index * 0.05 for index in range(320)],
            "close": [100.1 + index * 0.055 for index in range(320)],
            "volume": [800_000 + (index % 20) * 500 for index in range(320)],
        }
    )
    news = [
        SimpleNamespace(published_at=bars.iloc[-30]["time"].to_pydatetime(), raw_sentiment=0.4, relevance=0.8),
        SimpleNamespace(published_at=bars.iloc[-10]["time"].to_pydatetime(), raw_sentiment=0.2, relevance=0.7),
    ]
    result_a = run_backtest(
        symbol="TEST",
        bars=bars,
        articles=news,
        preset="Trend Following",
        fees_bps=2.0,
        spread_bps=2.0,
        slippage_bps=1.0,
        allow_short=False,
        ablation="technical_news_tca",
    )
    result_b = run_backtest(
        symbol="TEST",
        bars=bars,
        articles=news,
        preset="Trend Following",
        fees_bps=2.0,
        spread_bps=2.0,
        slippage_bps=1.0,
        allow_short=False,
        ablation="technical_news_tca",
    )
    assert result_a["metrics"]["totalReturn"] == result_b["metrics"]["totalReturn"]
    assert len(result_a["equityCurve"]) == len(result_b["equityCurve"])
