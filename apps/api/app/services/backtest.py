from __future__ import annotations

from datetime import timezone
from uuid import uuid4

import numpy as np
import pandas as pd

from app.services.indicators import compute_indicators


PRESETS = {
    "Trend Following": "trend",
    "Momentum Confirmation": "momentum",
    "Mean Reversion": "mean_reversion",
    "Breakout": "breakout",
    "News + Trend Confluence": "news_trend",
}


def _daily_news_score(articles: list) -> dict[str, float]:
    scores: dict[str, float] = {}
    for article in articles:
        key = article.published_at.date().isoformat()
        scores.setdefault(key, 0.0)
        scores[key] += article.raw_sentiment * article.relevance
    return scores


def _target_position(row: pd.Series, preset_key: str, news_score: float, allow_short: bool, ablation: str) -> tuple[int, float]:
    signal_strength = 0.0
    target = 0

    if preset_key == "trend":
        signal_strength = (1.2 if row["close"] > row["ema_50"] else -1.2) + (0.8 if row["macd"] > row["macd_signal"] else -0.8)
    elif preset_key == "momentum":
        signal_strength = (1.4 if row["close"] > row["ema_21"] > row["ema_50"] else -1.0) + (0.5 if row["rsi"] > 55 else -0.3) + (0.4 if row["adx"] > 20 else 0.0)
    elif preset_key == "mean_reversion":
        signal_strength = (1.6 if row["close"] < row["bb_lower"] and row["rsi"] < 35 else -1.4 if row["close"] > row["bb_upper"] and row["rsi"] > 65 else 0.0)
    elif preset_key == "breakout":
        signal_strength = (1.7 if row["close"] >= row["resistance_20"] * 0.999 and row["adx"] > 20 else -1.5 if row["close"] <= row["support_20"] * 1.001 and row["adx"] > 20 else 0.0)
    else:
        signal_strength = (1.1 if row["close"] > row["ema_50"] else -1.1) + (0.6 if row["macd"] > row["macd_signal"] else -0.6)
        if ablation != "technical_only":
            signal_strength += news_score * 1.3

    threshold = 0.8
    if signal_strength > threshold:
        target = 1
    elif allow_short and signal_strength < -threshold:
        target = -1
    return target, signal_strength


def _compute_metrics(net_returns: pd.Series, gross_returns: pd.Series, positions: pd.Series, trades: list[dict]) -> dict:
    equity = (1 + net_returns.fillna(0)).cumprod()
    gross_equity = (1 + gross_returns.fillna(0)).cumprod()
    total_return = equity.iloc[-1] - 1
    periods_per_year = 252
    years = max(len(net_returns) / periods_per_year, 1 / periods_per_year)
    cagr = equity.iloc[-1] ** (1 / years) - 1
    vol = net_returns.std(ddof=0) * np.sqrt(periods_per_year)
    downside = net_returns.where(net_returns < 0, 0).std(ddof=0) * np.sqrt(periods_per_year)
    sharpe = (net_returns.mean() * periods_per_year) / vol if vol else 0.0
    sortino = (net_returns.mean() * periods_per_year) / downside if downside else 0.0
    drawdown = equity / equity.cummax() - 1
    max_drawdown = drawdown.min()
    calmar = cagr / abs(max_drawdown) if max_drawdown else 0.0
    winners = [trade for trade in trades if trade["pnlPct"] > 0]
    losers = [trade for trade in trades if trade["pnlPct"] <= 0]
    gross_profit = sum(trade["pnlPct"] for trade in winners)
    gross_loss = abs(sum(trade["pnlPct"] for trade in losers))
    hit_rate = len(winners) / len(trades) if trades else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else float("inf")
    turnover = positions.diff().abs().fillna(0).sum()
    avg_hold = np.mean([trade["holdBars"] for trade in trades]) if trades else 0.0
    exposure = positions.abs().mean()

    return {
        "totalReturn": round(float(total_return), 6),
        "grossReturn": round(float(gross_equity.iloc[-1] - 1), 6),
        "cagr": round(float(cagr), 6),
        "sharpe": round(float(sharpe), 6),
        "sortino": round(float(sortino), 6),
        "maxDrawdown": round(float(max_drawdown), 6),
        "calmar": round(float(calmar), 6),
        "hitRate": round(float(hit_rate), 6),
        "profitFactor": None if profit_factor == float("inf") else round(float(profit_factor), 6),
        "turnover": round(float(turnover), 6),
        "averageHoldDurationBars": round(float(avg_hold), 2),
        "exposure": round(float(exposure), 6),
    }


def _walk_forward(net_returns: pd.Series, window: int = 126) -> list[dict]:
    points: list[dict] = []
    if len(net_returns) <= window:
        return points
    for start in range(0, len(net_returns) - window + 1, window):
        slice_returns = net_returns.iloc[start : start + window]
        equity = (1 + slice_returns.fillna(0)).cumprod()
        drawdown = equity / equity.cummax() - 1
        points.append(
            {
                "start": slice_returns.index[0].isoformat(),
                "end": slice_returns.index[-1].isoformat(),
                "return": round(float(equity.iloc[-1] - 1), 6),
                "maxDrawdown": round(float(drawdown.min()), 6),
                "sharpe": round(float((slice_returns.mean() * 252) / (slice_returns.std(ddof=0) * np.sqrt(252) or np.nan)), 6),
            }
        )
    return points


def run_backtest(
    *,
    symbol: str,
    bars: pd.DataFrame,
    articles: list,
    preset: str,
    fees_bps: float,
    spread_bps: float,
    slippage_bps: float,
    allow_short: bool,
    ablation: str,
) -> dict:
    frame = compute_indicators(bars).dropna().reset_index(drop=True)
    preset_key = PRESETS.get(preset, "trend")
    news_by_day = _daily_news_score(articles)

    targets = []
    strengths = []
    for _, row in frame.iterrows():
        news_score = news_by_day.get(row["time"].date().isoformat(), 0.0)
        target, strength = _target_position(row, preset_key, news_score, allow_short, ablation)
        if ablation == "technical_news_tca" and abs(strength) < (fees_bps + spread_bps + slippage_bps) / 5:
            target = 0
        targets.append(target)
        strengths.append(strength)

    frame["target"] = targets
    frame["strength"] = strengths
    frame["position"] = frame["target"].shift(1).fillna(0)
    frame["gross_return"] = frame["position"] * frame["close"].pct_change().fillna(0)
    frame["turnover"] = frame["position"].diff().abs().fillna(frame["position"].abs())
    total_cost_rate = (fees_bps + spread_bps + slippage_bps) / 10_000
    frame["cost"] = frame["turnover"] * total_cost_rate
    frame["net_return"] = frame["gross_return"] - frame["cost"]

    run_id = str(uuid4())
    open_trade: dict | None = None
    trades: list[dict] = []
    markers: list[dict] = []

    for idx in range(1, len(frame)):
        current = frame.iloc[idx]
        previous = frame.iloc[idx - 1]
        if current["position"] != previous["position"]:
            if open_trade is not None:
                open_trade["exitTime"] = current["time"].to_pydatetime().replace(tzinfo=timezone.utc).isoformat()
                open_trade["exitPrice"] = round(float(current["open"]), 4)
                open_trade["pnlPct"] = round(float((current["open"] / open_trade["entryPrice"] - 1) * (1 if open_trade["side"] == "LONG" else -1)), 6)
                open_trade["holdBars"] = idx - open_trade["entryIndex"]
                open_trade["totalCostBps"] = round(float(total_cost_rate * 10_000), 3)
                trades.append({k: v for k, v in open_trade.items() if k != "entryIndex"})
                open_trade = None
            if current["position"] != 0:
                side = "LONG" if current["position"] > 0 else "SHORT"
                open_trade = {
                    "side": side,
                    "entryTime": current["time"].to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
                    "entryPrice": round(float(current["open"]), 4),
                    "entryIndex": idx,
                }
                markers.append(
                    {
                        "time": current["time"].to_pydatetime().replace(tzinfo=timezone.utc).isoformat(),
                        "position": "belowBar" if side == "LONG" else "aboveBar",
                        "color": "#12d18e" if side == "LONG" else "#ff6f91",
                        "shape": "arrowUp" if side == "LONG" else "arrowDown",
                        "text": side,
                    }
                )

    net_returns = frame.set_index("time")["net_return"]
    gross_returns = frame.set_index("time")["gross_return"]
    positions = frame.set_index("time")["position"]
    metrics = _compute_metrics(net_returns, gross_returns, positions, trades)

    equity_curve = [
        {"time": idx.isoformat(), "gross": round(float(gross), 6), "net": round(float(net), 6)}
        for idx, gross, net in zip(
            net_returns.index,
            (1 + gross_returns.fillna(0)).cumprod(),
            (1 + net_returns.fillna(0)).cumprod(),
        )
    ]
    drawdown_curve = [
        {"time": idx.isoformat(), "value": round(float(val), 6)}
        for idx, val in ((1 + net_returns.fillna(0)).cumprod() / (1 + net_returns.fillna(0)).cumprod().cummax() - 1).items()
    ]

    return {
        "runId": run_id,
        "symbol": symbol,
        "preset": preset,
        "metrics": metrics,
        "equityCurve": equity_curve,
        "drawdownCurve": drawdown_curve,
        "tradeList": trades,
        "walkForward": _walk_forward(net_returns),
        "chartMarkers": markers,
    }
