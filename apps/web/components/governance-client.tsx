"use client";

import { useEffect, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { LiveFallbackNotice } from "@/components/live-fallback-notice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { DEMO_SYMBOLS } from "@/lib/constants";
import { fetchSignalGovernance } from "@/lib/api";
import { liveFallbackReasonFromError, shouldAttemptLiveFallback } from "@/lib/live-fallback";
import { useMarketMode } from "@/lib/use-market-mode";

export function GovernanceClient() {
  const [mode, setMode] = useMarketMode();
  const [symbol, setSymbol] = useState("SPY");
  const [payload, setPayload] = useState<any>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    fetchSignalGovernance(symbol, mode)
      .then((data) => {
        if (active) setPayload(data);
      })
      .catch((reason) => {
        if (!active) return;
        if (shouldAttemptLiveFallback(mode)) {
          setFallbackNotice(liveFallbackReasonFromError(reason));
          setError("Live governance comparison is temporarily unavailable. Stay in Live to retry, or switch to Demo for deterministic local evidence.");
          return;
        }
        setError(reason instanceof Error ? reason.message : "Governance comparison failed");
      });
    return () => {
      active = false;
    };
  }, [mode, setMode, symbol]);

  return (
    <AppFrame
      eyebrow="Model Governance"
      title="Signal Comparison"
      subtitle="Compare technical-only, news-aware, and fully governed signal variants so users can see exactly what changed and why."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <div className="w-32">
            <NativeSelect value={symbol} onChange={setSymbol}>
              {DEMO_SYMBOLS.map((item) => <option key={item} value={item}>{item}</option>)}
            </NativeSelect>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/4 p-1">
            <Button variant={mode === "demo" ? "default" : "ghost"} size="sm" onClick={() => { setFallbackNotice(null); setMode("demo"); }}>Demo</Button>
            <Button variant={mode === "live" ? "default" : "ghost"} size="sm" onClick={() => { setFallbackNotice(null); setMode("live"); }}>Live</Button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        {fallbackNotice && <LiveFallbackNotice message={fallbackNotice} />}
        {error && <Card className="p-5 text-sm text-rose-100">{error}</Card>}
        {!payload ? (
          <Card className="p-8 text-sm text-slate-400">Building governance comparison...</Card>
        ) : (
          <>
            <div className="grid gap-4 xl:grid-cols-3">
              {payload.variants.map((variant: any) => (
                <Card key={variant.key} className="p-5">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{variant.label}</p>
                  <div className="mt-4 flex items-center justify-between gap-3">
                    <h2 className="text-2xl font-semibold text-white">{variant.action.replaceAll("_", " ")}</h2>
                    <Badge>{Math.round(variant.confidence * 100)}%</Badge>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-400">{variant.description}</p>
                  <div className="mt-4 space-y-2">
                    {variant.reasonCodes.slice(0, 4).map((reason: any) => (
                      <div key={reason.code} className="rounded-2xl border border-white/8 bg-white/4 p-3">
                        <p className="text-sm font-medium text-white">{reason.label}</p>
                        <p className="mt-1 text-xs leading-5 text-slate-500">{reason.detail}</p>
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>

            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">What changed</p>
              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                {payload.comparisons.map((item: any) => (
                  <div key={item.to} className="rounded-[24px] border border-white/8 bg-white/4 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium text-white">{item.headline}</p>
                      <Badge className={item.actionChanged ? "border-amber-300/20 bg-amber-300/10 text-amber-100" : "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"}>
                        {item.actionChanged ? "action changed" : "action stable"}
                      </Badge>
                    </div>
                    <p className="mt-2 text-sm text-slate-400">Confidence delta: {(item.confidenceDelta * 100).toFixed(1)} pts</p>
                    <p className="mt-2 text-sm text-slate-500">Added reasons: {item.addedReasons.join(", ") || "none"}</p>
                    <p className="mt-1 text-sm text-slate-500">New risks: {item.newRiskFlags.join(", ") || "none"}</p>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-xs text-slate-500">{payload.caveat}</p>
            </Card>
          </>
        )}
      </div>
    </AppFrame>
  );
}
