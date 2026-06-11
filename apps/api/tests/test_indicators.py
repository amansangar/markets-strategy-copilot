from __future__ import annotations

import pandas as pd

from app.services.indicators import compute_indicators


def test_indicator_ranges_are_sane() -> None:
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=80, freq="D", tz="UTC"),
            "open": [100 + index * 0.5 for index in range(80)],
            "high": [101 + index * 0.5 for index in range(80)],
            "low": [99 + index * 0.5 for index in range(80)],
            "close": [100 + index * 0.55 for index in range(80)],
            "volume": [1_000_000 + index * 500 for index in range(80)],
        }
    )
    enriched = compute_indicators(frame)
    latest = enriched.iloc[-1]
    assert 0 <= latest["rsi"] <= 100
    assert latest["ema_21"] > 0
    assert latest["atr"] > 0
    assert latest["adx"] >= 0
