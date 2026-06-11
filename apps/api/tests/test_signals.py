from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from app.services.signals import generate_signal, _sanitized_trade_levels


def _bars() -> tuple[pd.DataFrame, pd.DataFrame]:
    intraday = pd.DataFrame(
        {
            "time": pd.date_range("2026-04-20 08:00", periods=120, freq="5min", tz="UTC"),
            "open": [100 + index * 0.1 for index in range(120)],
            "high": [100.3 + index * 0.1 for index in range(120)],
            "low": [99.8 + index * 0.1 for index in range(120)],
            "close": [100.1 + index * 0.1 for index in range(120)],
            "volume": [100_000 + (index % 12) * 1_000 for index in range(120)],
        }
    )
    daily = pd.DataFrame(
        {
            "time": pd.date_range("2025-09-01", periods=220, freq="B", tz="UTC"),
            "open": [90 + index * 0.2 for index in range(220)],
            "high": [90.3 + index * 0.2 for index in range(220)],
            "low": [89.6 + index * 0.2 for index in range(220)],
            "close": [90.1 + index * 0.21 for index in range(220)],
            "volume": [1_200_000 + (index % 20) * 1_000 for index in range(220)],
        }
    )
    return intraday, daily


def test_very_stale_signal_becomes_no_signal() -> None:
    intraday, daily = _bars()
    symbol = SimpleNamespace(symbol="TEST", asset_class="Equity ETF", avg_spread_bps=1.0, risk_limit=0.2)
    signal = generate_signal(symbol_meta=symbol, intraday_bars=intraday, daily_bars=daily, articles=[], mode="demo", stale_override_seconds=5_000)
    assert signal["action"] == "NO_SIGNAL"
    assert signal["confidence"] <= 0.24
    assert signal["positionSizePct"] == 0
    assert any(flag["code"] == "STALE_DATA" for flag in signal["riskFlags"])


def test_directional_trade_levels_are_price_sane() -> None:
    buy_levels = _sanitized_trade_levels("BUY", 100.0, 2.0)
    assert buy_levels is not None
    assert buy_levels["stop"] < 100.0 < buy_levels["takeLow"] <= buy_levels["takeHigh"]

    sell_levels = _sanitized_trade_levels("SELL", 100.0, 2.0)
    assert sell_levels is not None
    assert sell_levels["takeLow"] <= sell_levels["takeHigh"] < 100.0 < sell_levels["stop"]

    assert _sanitized_trade_levels("HOLD", 100.0, 2.0) is None
    assert _sanitized_trade_levels("NO_SIGNAL", 100.0, 2.0) is None
    assert _sanitized_trade_levels("BUY", 100.0, 0.0) is None


def test_hold_and_no_signal_do_not_publish_trade_size_or_levels() -> None:
    intraday, daily = _bars()
    symbol = SimpleNamespace(symbol="TEST", asset_class="Equity ETF", avg_spread_bps=1.0, risk_limit=0.2)
    signal = generate_signal(symbol_meta=symbol, intraday_bars=intraday, daily_bars=daily, articles=[], mode="demo", stale_override_seconds=2_000)
    assert signal["action"] == "NO_SIGNAL"
    assert signal["positionSizePct"] == 0
    assert signal["stopLoss"] is None
    assert signal["takeProfitLow"] is None
    assert signal["takeProfitHigh"] is None
