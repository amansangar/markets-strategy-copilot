"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { BacktestRobustnessCard } from "@/components/backtest-robustness-card";
import { MarketChart } from "@/components/market-chart";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { DEMO_SYMBOLS, PRESETS } from "@/lib/constants";
import { fetchAssetDetail, fetchStrategyMatrix, runBacktest } from "@/lib/api";

export function StrategyTesterClient() {
  const [symbol, setSymbol] = useState<(typeof DEMO_SYMBOLS)[number]>("SPY");
  const [preset, setPreset] = useState<(typeof PRESETS)[number]>("Mean Reversion");
  const [longShort, setLongShort] = useState(false);
  const [ablation, setAblation] = useState("technical_news_tca");
  const [result, setResult] = useState<any>(null);
  const [detail, setDetail] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);
  const [mounted, setMounted] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRunDone, setAutoRunDone] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    let active = true;
    setDetail(null);
    setError(null);
    setComparison(null);
    fetchAssetDetail(symbol, "demo")
      .then((payload) => active && setDetail(payload))
      .catch(() => active && setDetail(null));
    fetchStrategyMatrix(symbol, "demo")
      .then((payload) => active && setComparison(payload))
      .catch(() => active && setComparison(null));
    return () => {
      active = false;
    };
  }, [symbol]);

  useEffect(() => {
    setResult(null);
    setAutoRunDone(false);
  }, [symbol, preset, longShort, ablation]);

  const chart = useMemo(() => {
    if (!detail) {
      return null;
    }
    return result ? { ...detail.chart, markers: result.chartMarkers } : detail.chart;
  }, [detail, result]);

  const runSelectedBacktest = useCallback(async () => {
    setIsRunning(true);
    setError(null);
    try {
      const payload = await runBacktest({
        symbol,
        timeframe: "1d",
        preset,
        feesBps: 2.0,
        spreadBps: 2.0,
        slippageBps: 1.0,
        longShort,
        ablation,
      });
      setResult(payload);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Backtest failed to run");
    } finally {
      setIsRunning(false);
    }
  }, [ablation, longShort, preset, symbol]);

  useEffect(() => {
    if (!mounted || result || isRunning || autoRunDone) {
      return;
    }
    setAutoRunDone(true);
    void runSelectedBacktest();
  }, [autoRunDone, isRunning, mounted, result, runSelectedBacktest]);

  function handleRun() {
    setAutoRunDone(true);
    void runSelectedBacktest();
  }

  return (
    <AppFrame
      eyebrow="Evaluation"
      title="Strategy Tester"
      subtitle="Run deterministic backtests with realistic frictions, next-bar execution, and walk-forward reporting rather than idealised chart-only impressions."
      actions={<Button onClick={handleRun} disabled={!mounted || isRunning}>{isRunning ? "Running..." : "Run backtest"}</Button>}
    >
      <div className="space-y-4">
        <Card className="grid gap-4 p-5 md:grid-cols-4">
          <Control label="Symbol">
            <NativeSelect value={symbol} onChange={(value) => setSymbol(value as (typeof DEMO_SYMBOLS)[number])}>
              {DEMO_SYMBOLS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </NativeSelect>
          </Control>
          <Control label="Preset">
            <NativeSelect value={preset} onChange={(value) => setPreset(value as (typeof PRESETS)[number])}>
              {PRESETS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </NativeSelect>
          </Control>
          <Control label="Exposure mode">
            <NativeSelect value={longShort ? "long_short" : "long_only"} onChange={(value) => setLongShort(value === "long_short")}>
              <option value="long_only">Long only</option>
              <option value="long_short">Long / short</option>
            </NativeSelect>
          </Control>
          <Control label="Ablation">
            <NativeSelect value={ablation} onChange={setAblation}>
              <option value="technical_only">Technical only</option>
              <option value="technical_news">Technical + news</option>
              <option value="technical_news_tca">Technical + news + TCA</option>
            </NativeSelect>
          </Control>
        </Card>

        {error && <Card className="border-rose-300/20 bg-rose-500/8 p-4 text-sm text-rose-100">{error}</Card>}
        {!detail && !error && (
          <Card className="p-5 text-sm text-slate-400">
            Chart context is refreshing from seeded bars. Backtest results can be reviewed below.
          </Card>
        )}

        {comparison?.rows?.length ? (
          <Card className="p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-cyan-200/70">Preset comparison</p>
                <h2 className="mt-2 text-xl font-semibold text-white">Best deterministic evidence: {comparison.bestPreset}</h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                  Metrics are computed from seeded data with fees, spread, slippage, and walk-forward checks. They are not edited or faked, and one sample is not optimisation advice.
                </p>
              </div>
              <span className="rounded-full border border-emerald-300/20 bg-emerald-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100">
                Demo evidence
              </span>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              {comparison.rows.slice(0, 5).map((row: any) => (
                <button
                  key={row.preset}
                  type="button"
                  onClick={() => setPreset(row.preset as (typeof PRESETS)[number])}
                  className={`rounded-[22px] border p-4 text-left transition hover:-translate-y-0.5 hover:border-cyan-300/35 ${
                    row.preset === preset ? "border-cyan-300/35 bg-cyan-400/10" : "border-white/8 bg-white/4"
                  }`}
                >
                  <p className="text-sm font-semibold text-white">{row.preset}</p>
                  <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">Sharpe</p>
                  <p className="text-lg font-semibold text-white">{formatNumber(row.sharpe)}</p>
                  <p className="mt-2 text-xs text-slate-400">Return {formatPercent(row.totalReturn)} • Drawdown {formatPercent(row.maxDrawdown)}</p>
                  <p className="mt-1 text-xs text-slate-500">Robustness {formatNumber(row.robustnessScore)}</p>
                </button>
              ))}
            </div>
          </Card>
        ) : null}

        {chart && <MarketChart chart={chart} />}

        {result && (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {Object.entries(result.metrics).map(([key, value]) => (
                <Card key={key} className="p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{formatMetricLabel(key)}</p>
                  <p className="mt-3 text-2xl font-semibold text-white">{formatMetricValue(key, value)}</p>
                  {key.toLowerCase().includes("sortino") && Number(value) > 20 ? (
                    <p className="mt-2 text-xs leading-5 text-slate-400">
                      High Sortino reflects very low downside volatility in this seeded demo window.
                    </p>
                  ) : null}
                </Card>
              ))}
            </div>
            <BacktestRobustnessCard robustness={result.robustness} />
            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="p-5">
                <h2 className="text-lg font-semibold text-white">Walk-forward windows</h2>
                <div className="mt-4 space-y-3">
                  {result.walkForward.map((window: any) => (
                    <div key={`${window.start}-${window.end}`} className="rounded-[22px] border border-white/8 bg-white/4 p-4 text-sm text-slate-300">
                      <p className="font-medium text-white">
                        {window.start.slice(0, 10)} {"->"} {window.end.slice(0, 10)}
                      </p>
                      <p className="mt-2">Return {formatPercent(window.return)} • Max drawdown {formatPercent(window.maxDrawdown)} • Sharpe {formatNumber(window.sharpe)}</p>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5">
                <h2 className="text-lg font-semibold text-white">Trades</h2>
                <div className="mt-4 space-y-3">
                  {result.tradeList.slice(0, 8).map((trade: any, index: number) => (
                    <div key={`${trade.entryTime}-${index}`} className="rounded-[22px] border border-white/8 bg-white/4 p-4 text-sm text-slate-300">
                      <p className="font-medium text-white">{trade.side}</p>
                      <p className="mt-2">Entry {trade.entryTime.slice(0, 10)} at {formatCurrency(trade.entryPrice)}</p>
                      <p>Exit {trade.exitTime.slice(0, 10)} at {formatCurrency(trade.exitPrice)}</p>
                      <p>PnL {formatPercent(trade.pnlPct)} • Hold {trade.holdBars} bars • Cost {formatNumber(trade.totalCostBps)} bps</p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </>
        )}
      </div>
    </AppFrame>
  );
}

function Control({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
      {children}
    </div>
  );
}

function formatNumber(value: unknown) {
  const number = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(number)) {
    return "n/a";
  }
  return number.toFixed(2);
}

function formatPercent(value: unknown) {
  const number = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(number)) {
    return "n/a";
  }
  const percentage = Math.abs(number) > 1 ? number : number * 100;
  return `${percentage.toFixed(1)}%`;
}

function formatCurrency(value: unknown) {
  const number = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(number)) {
    return "n/a";
  }
  return number.toLocaleString("en-GB", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}

function formatMetricLabel(key: string) {
  const labels: Record<string, string> = {
    totalReturn: "Total return",
    total_return: "Total return",
    grossReturn: "Gross return",
    gross_return: "Gross return",
    cagr: "CAGR",
    sharpe: "Sharpe",
    sortino: "Sortino",
    maxDrawdown: "Max drawdown",
    max_drawdown: "Max drawdown",
    calmar: "Calmar",
    hitRate: "Hit rate",
    hit_rate: "Hit rate",
    profitFactor: "Profit factor",
    profit_factor: "Profit factor",
    turnover: "Turnover",
    averageHoldDuration: "Average hold",
    averageHoldDurationBars: "Average hold",
    average_hold_duration: "Average hold",
    average_hold_duration_bars: "Average hold",
    exposure: "Exposure",
    grossVsNet: "Gross vs net",
    gross_vs_net: "Gross vs net",
  };
  return labels[key] ?? key.replace(/_/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2");
}

function formatMetricValue(key: string, value: unknown) {
  const lower = key.toLowerCase();
  if (
    lower.includes("return") ||
    lower.includes("drawdown") ||
    lower.includes("hitrate") ||
    lower.includes("hit_rate") ||
    lower.includes("turnover") ||
    lower.includes("exposure")
  ) {
    return formatPercent(value);
  }
  if (lower.includes("duration")) {
    return `${formatNumber(value)} bars`;
  }
  return formatNumber(value);
}
