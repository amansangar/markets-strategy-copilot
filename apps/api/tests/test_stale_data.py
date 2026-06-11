from __future__ import annotations

from app.db import get_session
from app.repository import bars_dataframe, get_symbol, news_for_symbol
from app.services.signals import generate_signal


def test_stale_data_suppresses_direction(client) -> None:
    for session in get_session():
        meta = get_symbol(session, "SPY")
        intraday = bars_dataframe(session, "SPY", "5m")
        daily = bars_dataframe(session, "SPY", "1d")
        news = news_for_symbol(session, "SPY")
        payload = generate_signal(
            symbol_meta=meta,
            intraday_bars=intraday,
            daily_bars=daily,
            articles=news,
            mode="demo",
            stale_override_seconds=3600,
        )
    assert payload["action"] == "NO_SIGNAL"
    assert payload["confidence"] <= 0.24
    assert payload["positionSizePct"] == 0
    assert any(flag["code"] == "STALE_DATA" for flag in payload["riskFlags"])
