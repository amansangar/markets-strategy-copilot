"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { LiveFallbackNotice } from "@/components/live-fallback-notice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchSignalQuality } from "@/lib/api";
import { liveFallbackReasonFromError, shouldAttemptLiveFallback } from "@/lib/live-fallback";
import { useMarketMode } from "@/lib/use-market-mode";

export function SignalQualityClient() {
  const [mode, setMode] = useMarketMode();
  const [payload, setPayload] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    fetchSignalQuality(mode)
      .then((data) => {
        if (active) {
          setPayload(data);
        }
      })
      .catch((reason) => {
        if (!active) {
          return;
        }
        if (shouldAttemptLiveFallback(mode)) {
          setFallbackNotice(liveFallbackReasonFromError(reason));
          setError("Live signal quality is temporarily unavailable. Stay in Live to retry, or switch to Demo for the deterministic local view.");
          return;
        }
        setError(reason instanceof Error ? reason.message : "Signal quality request failed");
      });
    return () => {
      active = false;
    };
  }, [mode, setMode]);

  const summary = payload?.summary ?? {};
  const holdPct = Number(summary.holdPct ?? summary.noSignalPct ?? 0);
  const holdBackReasons = payload?.holdBackReasons ?? payload?.noSignalReasons ?? [];
  const actionMax = useMemo(() => {
    return Math.max(1, ...(payload?.actionDistribution ?? []).map((item: any) => Number(item.count) || 0));
  }, [payload]);

  function chooseMode(nextMode: "demo" | "live") {
    setFallbackNotice(null);
    setMode(nextMode);
  }

  return (
    <AppFrame
      eyebrow="Governance"
      title="Signal Quality"
      subtitle="Evidence that BUY / SELL outputs are explainable, confidence-scored, audited, and honest when risk controls lower conviction."
      actions={
        <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/4 p-1">
          <Button variant={mode === "demo" ? "default" : "ghost"} size="sm" onClick={() => chooseMode("demo")}>Demo</Button>
          <Button variant={mode === "live" ? "default" : "ghost"} size="sm" onClick={() => chooseMode("live")}>Live</Button>
        </div>
      }
    >
      <div className="space-y-4">
        {fallbackNotice && <LiveFallbackNotice message={fallbackNotice} />}
        {error && <Card className="p-5 text-sm text-rose-100">{error}</Card>}
        {!payload && !error ? (
          <Card className="p-8 text-sm text-slate-400">Calculating signal-quality evidence across the tracked universe...</Card>
        ) : payload ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <Metric label="Signals Reviewed" value={String(summary.totalSignals ?? 0)} />
              <Metric label="Avg Confidence" value={`${Math.round(Number(summary.averageConfidence ?? 0) * 100)}%`} />
              <Metric label="Avg Data Quality" value={`${Math.round(Number(summary.averageDataQuality ?? 0))}/100`} />
              <Metric label="Audit Coverage" value={`${Number(summary.auditCoveragePct ?? 0).toFixed(0)}%`} />
              <Metric label="Non-directional Signals" value={`${holdPct.toFixed(0)}%`} />
            </div>

            <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
              <Card className="p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Action distribution</p>
                <div className="mt-5 space-y-3">
                  {payload.actionDistribution.map((item: any) => (
                    <div key={item.action}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-300">{item.action.replaceAll("_", " ")}</span>
                        <span className="font-medium text-white">{item.count}</span>
                      </div>
                      <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/8">
                        <div className="h-full rounded-full bg-cyan-300" style={{ width: `${Math.max(4, (item.count / actionMax) * 100)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Why confidence is reduced</p>
                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  {holdBackReasons.map((item: any) => (
                    <div key={item.label} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                      <p className="text-sm font-medium text-white">{item.label}</p>
                      <p className="mt-2 text-2xl font-semibold text-amber-100">{item.count}</p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <Card className="overflow-hidden">
              <div className="border-b border-white/8 p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Per-symbol evidence</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{payload.caveat}</p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b border-white/8 bg-white/4 text-slate-400">
                    <tr>
                      {["Symbol", "Action", "Confidence", "Data Quality", "Regime", "Audit", "Top Reasons"].map((column) => (
                        <th key={column} className="px-4 py-3 font-medium">{column}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {payload.rows.map((row: any) => (
                      <tr key={row.symbol} className="border-b border-white/6 text-slate-200 last:border-b-0">
                        <td className="px-4 py-3">
                          <Link href={`/asset/${row.symbol}`} className="font-medium text-cyan-200 hover:text-cyan-100">{row.symbol}</Link>
                        </td>
                        <td className="px-4 py-3">{row.action.replaceAll("_", " ")}</td>
                        <td className="px-4 py-3">{Math.round(row.confidence * 100)}%</td>
                        <td className="px-4 py-3">{Math.round(row.dataQuality)}/100</td>
                        <td className="px-4 py-3">{row.regime.replaceAll("_", " ")}</td>
                        <td className="px-4 py-3">
                          <Badge className={row.auditCovered ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : "border-amber-300/20 bg-amber-300/10 text-amber-100"}>
                            {row.auditCovered ? "covered" : "pending"}
                          </Badge>
                        </td>
                        <td className="max-w-[420px] px-4 py-3 text-slate-400">
                          {(row.topReasons ?? []).map((reason: any) => reason.label).join(", ") || "No reason codes available"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        ) : null}
      </div>
    </AppFrame>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-white">{value}</p>
    </Card>
  );
}
