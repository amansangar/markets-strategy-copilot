"use client";

import { useEffect, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { LiveFallbackNotice } from "@/components/live-fallback-notice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { DEMO_SYMBOLS } from "@/lib/constants";
import { fetchStrategyMatrix } from "@/lib/api";
import { liveFallbackReasonFromError, shouldAttemptLiveFallback } from "@/lib/live-fallback";
import { useMarketMode } from "@/lib/use-market-mode";

export function StrategyMatrixClient() {
  const [mode, setMode] = useMarketMode();
  const [symbol, setSymbol] = useState("SPY");
  const [payload, setPayload] = useState<any>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setPayload(null);
    setError(null);
    fetchStrategyMatrix(symbol, mode)
      .then((data) => { if (active) setPayload(data); })
      .catch((reason) => {
        if (!active) return;
        if (shouldAttemptLiveFallback(mode)) {
          setFallbackNotice(liveFallbackReasonFromError(reason));
          setError("Live strategy comparison is temporarily unavailable. Stay in Live to retry, or switch to Demo for deterministic local backtest evidence.");
          return;
        }
        setError(reason instanceof Error ? reason.message : "Strategy comparison failed");
      });
    return () => { active = false; };
  }, [mode, setMode, symbol]);

  return (
    <AppFrame
      eyebrow="Backtest Lab"
      title="Strategy Matrix"
      subtitle="Rank strategy presets side-by-side with net/gross return, drawdown, Sharpe, turnover, trade count, and robustness evidence."
      actions={
        <div className="flex flex-wrap gap-2">
          <div className="w-32">
            <NativeSelect value={symbol} onChange={setSymbol}>{DEMO_SYMBOLS.map((item) => <option key={item} value={item}>{item}</option>)}</NativeSelect>
          </div>
          <Button variant={mode === "demo" ? "default" : "secondary"} size="sm" onClick={() => { setFallbackNotice(null); setMode("demo"); }}>Demo</Button>
          <Button variant={mode === "live" ? "default" : "secondary"} size="sm" onClick={() => { setFallbackNotice(null); setMode("live"); }}>Live</Button>
        </div>
      }
    >
      <div className="space-y-4">
        {fallbackNotice && <LiveFallbackNotice message={fallbackNotice} />}
        {error && <Card className="p-5 text-sm text-rose-100">{error}</Card>}
        {!payload ? (
          <Card className="p-8 text-sm text-slate-400">Running preset comparison for {symbol}...</Card>
        ) : (
          <>
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Best current preset</p>
              <h2 className="mt-2 text-3xl font-semibold text-white">{payload.bestPreset}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">{payload.caveat}</p>
            </Card>
            <Card className="overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-white/8 bg-white/4 text-slate-400">
                    <tr>
                      {["Preset", "Net Return", "Gross Return", "Sharpe", "Max DD", "Hit Rate", "Turnover", "Trades", "Robustness"].map((column) => <th key={column} className="px-4 py-3 font-medium">{column}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {payload.rows.map((row: any) => (
                      <tr key={row.preset} className="border-b border-white/6 text-slate-200 last:border-b-0">
                        <td className="px-4 py-3 font-medium text-white">{row.preset}</td>
                        <td className="px-4 py-3">{(row.totalReturn * 100).toFixed(2)}%</td>
                        <td className="px-4 py-3">{(row.grossReturn * 100).toFixed(2)}%</td>
                        <td className="px-4 py-3">{Number(row.sharpe).toFixed(2)}</td>
                        <td className="px-4 py-3">{(row.maxDrawdown * 100).toFixed(2)}%</td>
                        <td className="px-4 py-3">{(row.hitRate * 100).toFixed(0)}%</td>
                        <td className="px-4 py-3">{Number(row.turnover).toFixed(2)}</td>
                        <td className="px-4 py-3">{row.tradeCount}</td>
                        <td className="px-4 py-3"><Badge>{row.robustnessScore}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        )}
      </div>
    </AppFrame>
  );
}
