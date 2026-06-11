"use client";

import { useEffect, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { IconGauge, IconShield, IconSignal } from "@/components/icons";
import { LiveFallbackNotice } from "@/components/live-fallback-notice";
import { PortfolioRiskHeatmap } from "@/components/portfolio-risk-heatmap";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchPortfolio } from "@/lib/api";
import { liveFallbackReasonFromError, shouldAttemptLiveFallback } from "@/lib/live-fallback";
import type { PortfolioResponse } from "@/lib/types";
import { useMarketMode } from "@/lib/use-market-mode";

const LIVE_REFRESH_MS = 60_000;

function sourceLabel(source: string | undefined) {
  switch (source) {
    case "alpaca_paper_synced":
      return "Alpaca paper synced";
    case "local_fallback":
      return "Local fallback";
    case "local_simulated":
    default:
      return "Local simulated";
  }
}

export function PortfolioClient() {
  const [mode, setMode] = useMarketMode();
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadPortfolio() {
      setError(null);
      fetchPortfolio(mode)
      .then((payload) => {
        if (active) {
          setFallbackNotice(null);
          setPortfolio(payload);
        }
      })
      .catch(async (reason) => {
        if (!active) {
          return;
        }
        if (shouldAttemptLiveFallback(mode)) {
          setFallbackNotice(`${liveFallbackReasonFromError(reason)} Showing clearly labelled local paper state until the next live refresh succeeds.`);
          try {
            const fallbackPortfolio = await fetchPortfolio("demo");
            if (active) {
              setPortfolio({ ...fallbackPortfolio, mode: "live", source: "local_fallback" } as PortfolioResponse);
            }
          } catch {
            if (active) {
              setError("Portfolio request failed");
            }
          }
          return;
        }
        setError(reason instanceof Error ? reason.message : "Portfolio request failed");
      });
    }

    void loadPortfolio();
    const refresh = mode === "live" ? window.setInterval(() => {
      if (document.visibilityState !== "hidden") {
        void loadPortfolio();
      }
    }, LIVE_REFRESH_MS) : null;
    return () => {
      active = false;
      if (refresh) {
        window.clearInterval(refresh);
      }
    };
  }, [mode]);

  return (
    <AppFrame
      eyebrow="Paper Portfolio"
      title="Portfolio"
      subtitle="Track local simulated paper positions, journal entries, and Alpaca paper-account readiness. No real-money execution is implemented."
      actions={
        <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/4 p-1">
          <Button variant={mode === "demo" ? "default" : "ghost"} size="sm" onClick={() => { setFallbackNotice(null); setMode("demo"); }}>Demo</Button>
          <Button variant={mode === "live" ? "default" : "ghost"} size="sm" onClick={() => { setFallbackNotice(null); setMode("live"); }}>Live</Button>
        </div>
      }
    >
      {fallbackNotice && <div className="mb-4"><LiveFallbackNotice message={fallbackNotice} /></div>}

      {error ? (
        <Card className="p-8">
          <p className="text-sm uppercase tracking-[0.28em] text-rose-300">Portfolio error</p>
          <h2 className="mt-3 text-2xl font-semibold text-white">{error}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Portfolio data is unavailable, so the app is not pretending the paper state is current.</p>
        </Card>
      ) : !portfolio ? (
        <Card className="p-8 text-sm text-slate-400">Loading portfolio...</Card>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Metric label="Open Positions" value={String(portfolio.summary.openPositions ?? 0)} />
            <Metric label="Gross Exposure" value={`$${Number(portfolio.summary.grossExposure ?? 0).toLocaleString("en-GB")}`} />
            <Metric label="Unrealized P&L" value={`$${Number(portfolio.summary.unrealizedPnl ?? 0).toLocaleString("en-GB")}`} />
            <Metric label="Win Rate" value={`${(Number(portfolio.summary.winRate ?? 0) * 100).toFixed(1)}%`} />
          </div>

          <Card className="p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <IconShield className="h-4 w-4 text-cyan-200" />
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Portfolio Source</p>
              </div>
              <Badge>{sourceLabel(portfolio.source)}</Badge>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-300">{portfolio.alpacaSync.detail}</p>
          </Card>

          <PortfolioRiskHeatmap heatmap={portfolio.riskHeatmap} />

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <Card className="p-5">
              <div className="flex items-center gap-2">
                <IconGauge className="h-4 w-4 text-emerald-200" />
                <h2 className="text-lg font-semibold text-white">Open positions</h2>
              </div>
              <div className="mt-4 overflow-hidden rounded-[24px] border border-white/8">
                {portfolio.positions.map((position) => (
                  <div key={String(position.id)} className="grid grid-cols-5 gap-3 border-b border-white/8 bg-white/3 p-4 text-sm last:border-b-0">
                    <span className="font-medium text-white">{String(position.symbol)}</span>
                    <span className="text-slate-300">{Number(position.quantity).toFixed(4)}</span>
                    <span className="text-slate-300">${Number(position.lastPrice).toFixed(2)}</span>
                    <span className={Number(position.unrealizedPnl) >= 0 ? "text-emerald-200" : "text-rose-200"}>${Number(position.unrealizedPnl).toFixed(2)}</span>
                    <span className="text-slate-500">{sourceLabel(String(position.source))}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-5">
              <div className="flex items-center gap-2">
                <IconSignal className="h-4 w-4 text-cyan-200" />
                <h2 className="text-lg font-semibold text-white">Journal</h2>
              </div>
              <div className="mt-4 space-y-3">
                {portfolio.journal.map((entry) => (
                  <div key={String(entry.id)} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                    <p className="text-sm font-medium text-white">{String(entry.title)}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{String(entry.body)}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}
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
