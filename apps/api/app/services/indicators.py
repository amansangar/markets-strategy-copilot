from __future__ import annotations

import numpy as np
import pandas as pd


def _wilder(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def compute_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy().sort_values("time").reset_index(drop=True)
    if df.empty:
        return df

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    df["sma_20"] = df["close"].rolling(20).mean()
    df["ema_9"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["vwap"] = (typical_price * df["volume"]).cumsum() / df["volume"].replace(0, np.nan).cumsum()

    delta = df["close"].diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = _wilder(gains, 14)
    avg_loss = _wilder(losses, 14)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df.loc[(avg_loss == 0) & (avg_gain > 0), "rsi"] = 100
    df.loc[(avg_gain == 0) & (avg_loss > 0), "rsi"] = 0
    df.loc[(avg_gain == 0) & (avg_loss == 0), "rsi"] = 50

    ema_fast = df["close"].ewm(span=12, adjust=False).mean()
    ema_slow = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    rolling_std = df["close"].rolling(20).std()
    df["bb_mid"] = df["sma_20"]
    df["bb_upper"] = df["bb_mid"] + 2 * rolling_std
    df["bb_lower"] = df["bb_mid"] - 2 * rolling_std

    prev_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr"] = _wilder(true_range, 14)
    df["atr_pct"] = df["atr"] / df["close"].replace(0, np.nan)

    lowest_low = df["low"].rolling(14).min()
    highest_high = df["high"].rolling(14).max()
    raw_k = 100 * (df["close"] - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    df["stoch_k"] = raw_k.rolling(3).mean()
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr14 = _wilder(true_range, 14)
    plus_di = 100 * _wilder(pd.Series(plus_dm), 14) / tr14.replace(0, np.nan)
    minus_di = 100 * _wilder(pd.Series(minus_dm), 14) / tr14.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di
    df["adx"] = _wilder(dx, 14)

    hl2 = (df["high"] + df["low"]) / 2
    multiplier = 3.0
    atr10 = _wilder(true_range, 10)
    upperband = hl2 + multiplier * atr10
    lowerband = hl2 - multiplier * atr10
    close_values = df["close"].to_numpy(dtype=float)
    upper_values = upperband.to_numpy(dtype=float)
    lower_values = lowerband.to_numpy(dtype=float)
    supertrend_values = np.empty(len(df), dtype=float)
    direction_values = np.ones(len(df), dtype=int)
    for index in range(len(df)):
        if index == 0:
            supertrend_values[index] = lower_values[index]
            direction_values[index] = 1
            continue
        prev_super = supertrend_values[index - 1]
        prev_dir = direction_values[index - 1]
        if close_values[index] > upper_values[index - 1]:
            direction_values[index] = 1
        elif close_values[index] < lower_values[index - 1]:
            direction_values[index] = -1
        else:
            direction_values[index] = prev_dir
        band = lower_values[index] if direction_values[index] == 1 else upper_values[index]
        supertrend_values[index] = band if prev_dir != direction_values[index] or np.isnan(prev_super) else (
            max(band, prev_super) if direction_values[index] == 1 else min(band, prev_super)
        )
    df["supertrend"] = supertrend_values
    df["supertrend_direction"] = direction_values

    df["ichimoku_conversion"] = (df["high"].rolling(9).max() + df["low"].rolling(9).min()) / 2
    df["ichimoku_base"] = (df["high"].rolling(26).max() + df["low"].rolling(26).min()) / 2
    df["ichimoku_span_a"] = ((df["ichimoku_conversion"] + df["ichimoku_base"]) / 2).shift(26)
    df["ichimoku_span_b"] = ((df["high"].rolling(52).max() + df["low"].rolling(52).min()) / 2).shift(26)
    df["ichimoku_lagging"] = df["close"].shift(-26)

    direction_volume = np.sign(df["close"].diff().fillna(0))
    df["obv"] = (direction_volume * df["volume"]).fillna(0).cumsum()
    df["volume_ma_20"] = df["volume"].rolling(20).mean()
    df["support_20"] = df["low"].rolling(20).min()
    df["resistance_20"] = df["high"].rolling(20).max()
    df["return_20d"] = df["close"].pct_change(20)
    df["return_5d"] = df["close"].pct_change(5)
    return df
