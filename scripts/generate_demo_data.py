from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

import numpy as np


SEED = 22044744
UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "demo"


@dataclass(slots=True)
class SymbolMeta:
    symbol: str
    name: str
    asset_class: str
    venue: str
    currency: str
    avg_spread_bps: float
    risk_limit: float
    description: str


SYMBOLS = [
    SymbolMeta("SPY", "SPDR S&P 500 ETF Trust", "Equity ETF", "NYSE Arca", "USD", 1.0, 0.35, "US equity beta proxy"),
    SymbolMeta("QQQ", "Invesco QQQ Trust", "Equity ETF", "NASDAQ", "USD", 1.2, 0.32, "US mega-cap growth proxy"),
    SymbolMeta("DIA", "SPDR Dow Jones Industrial Average ETF", "Equity ETF", "NYSE Arca", "USD", 1.4, 0.28, "US blue-chip index proxy"),
    SymbolMeta("IWM", "iShares Russell 2000 ETF", "Equity ETF", "NYSE Arca", "USD", 2.2, 0.24, "US small-cap risk proxy"),
    SymbolMeta("TLT", "iShares 20+ Year Treasury Bond ETF", "Bond ETF", "NASDAQ", "USD", 1.8, 0.22, "Duration and rates proxy"),
    SymbolMeta("USO", "United States Oil Fund", "Commodity ETF", "NYSE Arca", "USD", 4.5, 0.18, "Crude oil proxy"),
    SymbolMeta("GLD", "SPDR Gold Shares", "Commodity ETF", "NYSE Arca", "USD", 2.0, 0.25, "Gold risk-off proxy"),
    SymbolMeta("SLV", "iShares Silver Trust", "Commodity ETF", "NYSE Arca", "USD", 4.0, 0.18, "Silver and industrial metals proxy"),
    SymbolMeta("AAPL", "Apple Inc.", "Equity", "NASDAQ", "USD", 1.1, 0.20, "Mega-cap technology"),
    SymbolMeta("MSFT", "Microsoft Corp.", "Equity", "NASDAQ", "USD", 1.0, 0.22, "Cloud and AI platform leader"),
    SymbolMeta("NVDA", "NVIDIA Corp.", "Equity", "NASDAQ", "USD", 1.8, 0.18, "AI semiconductor momentum"),
    SymbolMeta("TSLA", "Tesla Inc.", "Equity", "NASDAQ", "USD", 3.5, 0.14, "High-beta electric vehicle equity"),
    SymbolMeta("AMZN", "Amazon.com Inc.", "Equity", "NASDAQ", "USD", 1.4, 0.18, "Consumer and cloud platform"),
    SymbolMeta("META", "Meta Platforms Inc.", "Equity", "NASDAQ", "USD", 1.5, 0.18, "Digital advertising and AI platform"),
    SymbolMeta("GOOGL", "Alphabet Inc.", "Equity", "NASDAQ", "USD", 1.3, 0.18, "Search, cloud, and AI platform"),
    SymbolMeta("JPM", "JPMorgan Chase & Co.", "Equity", "NYSE", "USD", 1.6, 0.18, "Large-cap bank and credit proxy"),
    SymbolMeta("XOM", "Exxon Mobil Corp.", "Equity", "NYSE", "USD", 1.8, 0.16, "Integrated energy equity"),
    SymbolMeta("COIN", "Coinbase Global Inc.", "Equity", "NASDAQ", "USD", 5.5, 0.12, "Crypto equity beta proxy"),
    SymbolMeta("EURUSD", "Euro / US Dollar", "FX", "OTC", "USD", 0.8, 0.20, "Major FX pair"),
    SymbolMeta("GBPUSD", "British Pound / US Dollar", "FX", "OTC", "USD", 1.0, 0.18, "Major FX pair"),
    SymbolMeta("USDJPY", "US Dollar / Japanese Yen", "FX", "OTC", "JPY", 1.1, 0.18, "Rates-sensitive FX pair"),
    SymbolMeta("BTCUSD", "Bitcoin / US Dollar", "Crypto", "Polygon Crypto", "USD", 8.0, 0.15, "24/7 digital asset proxy"),
    SymbolMeta("ETHUSD", "Ethereum / US Dollar", "Crypto", "Polygon Crypto", "USD", 10.0, 0.14, "Smart-contract platform proxy"),
    SymbolMeta("SOLUSD", "Solana / US Dollar", "Crypto", "Polygon Crypto", "USD", 16.0, 0.10, "High-beta crypto network proxy"),
]


def business_days(start: datetime, end: datetime) -> list[datetime]:
    current = start
    days: list[datetime] = []
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def generate_daily_bars(meta: SymbolMeta, rng: np.random.Generator, days: list[datetime]) -> list[dict[str, float | str]]:
    drift_map = {
        "SPY": 0.00035,
        "QQQ": 0.00045,
        "NVDA": 0.00085,
        "MSFT": 0.00042,
        "AAPL": 0.00028,
        "TSLA": -0.00005,
        "COIN": 0.00075,
        "TLT": -0.00008,
        "GLD": 0.00018,
        "SLV": 0.00022,
        "USO": 0.0001,
        "EURUSD": 0.00005,
        "GBPUSD": 0.00003,
        "USDJPY": -0.00003,
        "BTCUSD": 0.00085,
        "ETHUSD": 0.00075,
        "SOLUSD": 0.0011,
    }
    vol_map = {
        "SPY": 0.010,
        "QQQ": 0.013,
        "DIA": 0.009,
        "IWM": 0.015,
        "TLT": 0.011,
        "USO": 0.020,
        "GLD": 0.008,
        "SLV": 0.015,
        "AAPL": 0.014,
        "MSFT": 0.012,
        "NVDA": 0.026,
        "TSLA": 0.030,
        "AMZN": 0.017,
        "META": 0.020,
        "GOOGL": 0.015,
        "JPM": 0.013,
        "XOM": 0.014,
        "COIN": 0.038,
        "EURUSD": 0.004,
        "GBPUSD": 0.005,
        "USDJPY": 0.006,
        "BTCUSD": 0.028,
        "ETHUSD": 0.032,
        "SOLUSD": 0.045,
    }
    volume_map = {
        "SPY": 72_000_000,
        "QQQ": 48_000_000,
        "DIA": 5_200_000,
        "IWM": 26_000_000,
        "TLT": 31_000_000,
        "USO": 18_000_000,
        "GLD": 13_000_000,
        "SLV": 24_000_000,
        "AAPL": 56_000_000,
        "MSFT": 28_000_000,
        "NVDA": 44_000_000,
        "TSLA": 92_000_000,
        "AMZN": 39_000_000,
        "META": 21_000_000,
        "GOOGL": 25_000_000,
        "JPM": 11_000_000,
        "XOM": 15_000_000,
        "COIN": 12_000_000,
        "EURUSD": 4_500_000,
        "GBPUSD": 3_900_000,
        "USDJPY": 4_200_000,
        "BTCUSD": 950_000,
        "ETHUSD": 780_000,
        "SOLUSD": 520_000,
    }
    start_price_map = {
        "SPY": 485.0,
        "QQQ": 420.0,
        "DIA": 380.0,
        "IWM": 210.0,
        "TLT": 92.0,
        "USO": 74.0,
        "GLD": 188.0,
        "SLV": 24.0,
        "AAPL": 176.0,
        "MSFT": 410.0,
        "NVDA": 780.0,
        "TSLA": 230.0,
        "AMZN": 165.0,
        "META": 490.0,
        "GOOGL": 150.0,
        "JPM": 178.0,
        "XOM": 112.0,
        "COIN": 210.0,
        "EURUSD": 1.08,
        "GBPUSD": 1.26,
        "USDJPY": 149.0,
        "BTCUSD": 42_000.0,
        "ETHUSD": 2_650.0,
        "SOLUSD": 105.0,
    }

    drift = drift_map.get(meta.symbol, 0.00022)
    vol = vol_map.get(meta.symbol, 0.014)
    base_volume = volume_map.get(meta.symbol, 10_000_000)
    price = start_price_map.get(meta.symbol, 100.0)
    bars: list[dict[str, float | str]] = []
    regime_cycle = np.sin(np.linspace(0, np.pi * 4.5, len(days)))

    for idx, session in enumerate(days):
        regime_boost = 0.5 * regime_cycle[idx]
        overnight = rng.normal(0, vol * 0.22)
        intraday = drift + regime_boost * 0.0006 + rng.normal(0, vol * 0.65)
        open_price = max(0.0001, price * (1 + overnight))
        close_price = max(0.0001, open_price * (1 + intraday))
        wick = abs(rng.normal(vol * 0.6, vol * 0.2))
        high_price = max(open_price, close_price) * (1 + wick)
        low_price = min(open_price, close_price) * (1 - wick * 0.85)
        volume = base_volume * (1 + abs(intraday) * 22 + rng.normal(0, 0.08))
        volume = max(base_volume * 0.35, volume)

        bars.append(
            {
                "symbol": meta.symbol,
                "time": session.replace(hour=21, minute=0, tzinfo=UTC).isoformat(),
                "open": round(open_price, 6),
                "high": round(high_price, 6),
                "low": round(low_price, 6),
                "close": round(close_price, 6),
                "volume": round(volume, 2),
                "timeframe": "1d",
            }
        )
        price = close_price
    return bars


def generate_intraday_bars(meta: SymbolMeta, rng: np.random.Generator, last_daily_close: float) -> list[dict[str, float | str]]:
    bars: list[dict[str, float | str]] = []
    base_day = datetime(2026, 4, 20, tzinfo=UTC)
    current = datetime.combine((base_day - timedelta(days=3)).date(), time(8, 0), tzinfo=UTC)
    close = last_daily_close

    for idx in range(288):
        drift = 0.00006 if meta.symbol in {"SPY", "QQQ", "NVDA", "BTCUSD", "ETHUSD", "SOLUSD"} else 0.00002
        vol = 0.0014 if meta.asset_class != "Crypto" else 0.0035
        open_price = close
        close = max(0.0001, close * (1 + drift + rng.normal(0, vol)))
        wick = abs(rng.normal(vol * 0.9, vol * 0.3))
        high = max(open_price, close) * (1 + wick)
        low = min(open_price, close) * (1 - wick * 0.9)
        volume_base = 2_000_000 if meta.asset_class in {"Equity ETF", "Equity"} else 300_000 if meta.asset_class == "Crypto" else 180_000
        volume = volume_base * (1 + abs(close - open_price) * 20)
        bars.append(
            {
                "symbol": meta.symbol,
                "time": current.isoformat(),
                "open": round(open_price, 6),
                "high": round(high, 6),
                "low": round(low, 6),
                "close": round(close, 6),
                "volume": round(volume, 2),
                "timeframe": "5m",
            }
        )
        current += timedelta(minutes=5)
    return bars


def generate_news() -> list[dict[str, str | float | list[str]]]:
    published = [
        ("SPY", "Mega-cap earnings keep broad US index bid as volatility cools", 0.71, 0.82, "https://example.com/demo/spy-earnings"),
        ("QQQ", "AI software and chip leadership keeps Nasdaq momentum screen active", 0.64, 0.81, "https://example.com/demo/qqq-ai"),
        ("NVDA", "Semiconductor breadth improves as data-centre demand remains resilient", 0.69, 0.86, "https://example.com/demo/nvda-demand"),
        ("MSFT", "Cloud growth stabilises while AI infrastructure spend remains elevated", 0.48, 0.78, "https://example.com/demo/msft-cloud"),
        ("AAPL", "Apple services margins offset cautious hardware replacement cycle", 0.18, 0.72, "https://example.com/demo/aapl-services"),
        ("TSLA", "Tesla volatility rises as delivery expectations reset lower", -0.42, 0.80, "https://example.com/demo/tsla-deliveries"),
        ("AMZN", "Retail margins and cloud backlog support constructive Amazon tape", 0.44, 0.73, "https://example.com/demo/amzn-backlog"),
        ("META", "Ad checks and AI engagement keep Meta relative strength intact", 0.51, 0.74, "https://example.com/demo/meta-ads"),
        ("JPM", "Bank credit commentary remains stable as deposit beta normalises", 0.24, 0.69, "https://example.com/demo/jpm-credit"),
        ("GLD", "Gold steadies as real yields soften and macro hedging demand returns", 0.22, 0.63, "https://example.com/demo/gld-yields"),
        ("TLT", "Long-duration bonds catch a bid as rate volatility cools", 0.34, 0.71, "https://example.com/demo/tlt-rates"),
        ("USO", "Oil range tightens as inventory data offsets geopolitical premium", -0.05, 0.62, "https://example.com/demo/uso-inventory"),
        ("EURUSD", "Euro firms after inflation print nudges rate expectations higher", 0.41, 0.76, "https://example.com/demo/eurusd-cpi"),
        ("GBPUSD", "Sterling holds support as UK wage data keeps policy path uncertain", 0.16, 0.64, "https://example.com/demo/gbpusd-wages"),
        ("USDJPY", "Yen sensitivity rises as rate-differential trades get crowded", -0.28, 0.70, "https://example.com/demo/usdjpy-rates"),
        ("BTCUSD", "Bitcoin liquidity improves as ETF flows recover from prior week drawdown", 0.58, 0.88, "https://example.com/demo/btc-etf"),
        ("ETHUSD", "Ethereum staking flows improve while volatility remains elevated", 0.39, 0.76, "https://example.com/demo/eth-staking"),
        ("SOLUSD", "Solana network activity rebounds but funding risk remains high", 0.27, 0.77, "https://example.com/demo/sol-activity"),
        ("SPY", "Index breadth narrows even as headline benchmark makes fresh highs", -0.18, 0.66, "https://example.com/demo/spy-breadth"),
        ("BTCUSD", "Crypto derivatives funding spikes, raising risk of short-term shakeout", -0.36, 0.74, "https://example.com/demo/btc-funding"),
        ("GLD", "Commodity inflows pick up as portfolio hedgers add defensive exposure", 0.31, 0.61, "https://example.com/demo/gld-inflows"),
        ("EURUSD", "Dollar demand fades into month-end rebalance window", 0.17, 0.57, "https://example.com/demo/fx-rebalance"),
    ]
    rows: list[dict[str, str | float | list[str]]] = []
    for idx, (symbol, title, sentiment, relevance, url) in enumerate(published):
        rows.append(
            {
                "id": f"demo-news-{idx + 1}",
                "source": "Seeded Market Wire",
                "title": title,
                "description": f"Deterministic demo headline for {symbol} used to exercise relevance, decay, and explainability paths.",
                "published_at": (datetime(2026, 4, 20, 14, 30, tzinfo=UTC) - timedelta(hours=idx * 4)).isoformat(),
                "url": url,
                "symbols": [symbol],
                "raw_sentiment": sentiment,
                "relevance": relevance,
            }
        )
    return rows


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    rng = np.random.default_rng(SEED)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    start = datetime(2024, 1, 2, tzinfo=UTC)
    end = datetime(2026, 4, 22, tzinfo=UTC)
    days = business_days(start, end)

    daily_bars: list[dict[str, float | str]] = []
    intraday_bars: list[dict[str, float | str]] = []

    for meta in SYMBOLS:
        bars = generate_daily_bars(meta, rng, days)
        daily_bars.extend(bars)
        intraday_bars.extend(generate_intraday_bars(meta, rng, float(bars[-1]["close"])))

    write_json(OUT_DIR / "symbols.json", [asdict(symbol) for symbol in SYMBOLS])
    write_json(OUT_DIR / "bars_1d.json", daily_bars)
    write_json(OUT_DIR / "bars_5m.json", intraday_bars)
    write_json(OUT_DIR / "news.json", generate_news())

    print(f"Wrote demo dataset to {OUT_DIR}")


if __name__ == "__main__":
    main()
