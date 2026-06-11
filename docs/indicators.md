# Indicator Catalogue

This project uses canonical, deterministic implementations for both UI display and backtesting. Exact parity with TradingView cannot be guaranteed because data source rounding, session definitions, and warm-up handling may differ. Any differences are documented here rather than hidden.

## Defaults

- `SMA`: length 20
- `EMA`: lengths 9, 21, 50, 200
- `VWAP`: session cumulative typical price × volume / cumulative volume
- `RSI`: length 14 using Wilder smoothing
- `MACD`: fast 12, slow 26, signal 9
- `Bollinger Bands`: length 20, standard deviation 2
- `ATR`: length 14 using Wilder smoothing
- `Stochastic`: %K 14, %D 3, smooth 3
- `ADX / DMI`: length 14
- `Supertrend`: ATR length 10, multiplier 3
- `Ichimoku`: 9 / 26 / 52 with displacement 26
- `OBV`: cumulative signed volume
- `Volume MA`: length 20
- `Support / Resistance`: rolling swing highs and lows using a 5-bar pivot window

## Formula Notes

### SMA

Arithmetic rolling mean of close over `n` periods.

### EMA

Exponential moving average with smoothing factor `2 / (n + 1)`.

### VWAP

Computed from cumulative `(high + low + close) / 3 * volume` divided by cumulative volume within the active session window in the demo dataset.

### RSI

Uses Wilder's average gain / average loss method:

- `RS = avg_gain / avg_loss`
- `RSI = 100 - 100 / (1 + RS)`

### MACD

- `MACD line = EMA(12) - EMA(26)`
- `Signal line = EMA(MACD, 9)`
- `Histogram = MACD - Signal`

### Bollinger Bands

- `Middle = SMA(close, 20)`
- `Upper = Middle + 2 * std(close, 20)`
- `Lower = Middle - 2 * std(close, 20)`

### ATR

True range is `max(high-low, |high-prev_close|, |low-prev_close|)`. ATR is the Wilder-smoothed mean of true range.

### Stochastic

- `%K = 100 * (close - lowest_low) / (highest_high - lowest_low)`
- `%D = SMA(%K, 3)` after optional smoothing

### ADX / DMI

Directional movement uses standard positive / negative DM and ATR-normalised DI values, with ADX as Wilder-smoothed DX.

### Supertrend

Uses ATR bands around the median price, then flips regime only when close breaches the active band.

### Ichimoku

- Conversion line: `(9-period high + 9-period low) / 2`
- Base line: `(26-period high + 26-period low) / 2`
- Span A: `(conversion + base) / 2`, shifted forward 26
- Span B: `(52-period high + 52-period low) / 2`, shifted forward 26
- Lagging span: close shifted backward 26

## Consistency Rule

The same indicator engine is used by:

- chart overlays
- scanner filters
- live signal engine
- backtesting pipeline

This avoids the common failure mode where a chart suggests one state but the backtest used a slightly different formula.
