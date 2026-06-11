"use client";

import { useDeferredValue, useEffect, useMemo, useRef, useState, useTransition } from "react";

import { IconBell, IconChart, IconGauge, IconSignal, IconTrendDown, IconTrendUp } from "@/components/icons";
import { AnalyticsTabs } from "@/components/analytics-tabs";
import { AppFrame } from "@/components/app-frame";
import { LiveFallbackNotice } from "@/components/live-fallback-notice";
import { MarketChart } from "@/components/market-chart";
import { MacroStrip } from "@/components/macro-strip";
import { SignalCard } from "@/components/signal-card";
import { SummaryTile } from "@/components/summary-tile";
import { TopOpportunities } from "@/components/top-opportunities";
import { WatchlistPanel } from "@/components/watchlist-panel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchDashboard, websocketUrl } from "@/lib/api";
import { liveFallbackReasonFromError, liveFallbackReasonFromHealth, shouldAttemptLiveFallback } from "@/lib/live-fallback";
import type { DashboardResponse } from "@/lib/types";
import { useMarketMode } from "@/lib/use-market-mode";

const DASHBOARD_BROWSER_CACHE_KEY = "markets-strategy-copilot:last-dashboard";
const DASHBOARD_BROWSER_CACHE_TTL_MS = 10 * 60 * 1000;
const LIVE_REFRESH_MS = 60_000;

function dashboardCacheKey(symbol: string, mode: "demo" | "live") {
  return `${DASHBOARD_BROWSER_CACHE_KEY}:${mode}:${symbol.toUpperCase()}`;
}

function readCachedDashboard(symbol: string, mode: "demo" | "live"): DashboardResponse | null {
  try {
    const raw = window.localStorage.getItem(dashboardCacheKey(symbol, mode));
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as { savedAt: number; payload: DashboardResponse };
    if (Date.now() - parsed.savedAt > DASHBOARD_BROWSER_CACHE_TTL_MS) {
      return null;
    }
    return parsed.payload;
  } catch {
    return null;
  }
}

function writeCachedDashboard(symbol: string, mode: "demo" | "live", payload: DashboardResponse) {
  try {
    window.localStorage.setItem(dashboardCacheKey(symbol, mode), JSON.stringify({ savedAt: Date.now(), payload }));
  } catch {
    // Browser storage is an enhancement only; the API remains the source of truth.
  }
}

export function DashboardClient({ initialDashboard = null }: { initialDashboard?: DashboardResponse | null }) {
  const [mode, setMode] = useMarketMode();
  const [selectedSymbol, setSelectedSymbol] = useState(initialDashboard?.chart.symbol ?? initialDashboard?.signal.symbol ?? "SPY");
  const deferredSymbol = useDeferredValue(selectedSymbol);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(initialDashboard);
  const dashboardRef = useRef<DashboardResponse | null>(initialDashboard);
  const hasDashboardRef = useRef(Boolean(initialDashboard));
  const [error, setError] = useState<string | null>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);
  const [fallbackTitle, setFallbackTitle] = useState("Live fallback active");
  const [loading, setLoading] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    dashboardRef.current = dashboard;
    hasDashboardRef.current = Boolean(dashboard);
  }, [dashboard]);

  useEffect(() => {
    let active = true;

    async function loadDashboard(background = false) {
      try {
        setError(null);
        if (!background) {
          setLoading(true);
        }
        if (!hasDashboardRef.current) {
          const cachedPayload = readCachedDashboard(deferredSymbol, mode);
          if (cachedPayload) {
            setDashboard(cachedPayload);
          }
        }
        const payload = await fetchDashboard(mode, deferredSymbol);
        if (!active) {
          return;
        }

        const fallbackReason = shouldAttemptLiveFallback(mode) ? liveFallbackReasonFromHealth(payload.health) : null;
        if (fallbackReason) {
          setFallbackTitle("Live data degraded");
          setFallbackNotice(fallbackReason);
        } else {
          setFallbackNotice(null);
        }

        setDashboard(payload);
        writeCachedDashboard(deferredSymbol, mode, payload);
      } catch (reason) {
        if (!active) {
          return;
        }
        if (shouldAttemptLiveFallback(mode)) {
          const currentFallback = dashboardRef.current ?? readCachedDashboard(deferredSymbol, mode);
          if (currentFallback) {
            setFallbackTitle("Live data unavailable");
            setFallbackNotice(`${liveFallbackReasonFromError(reason)} The app is keeping the last usable local view on screen and will retry live data every minute.`);
            setDashboard({
              ...currentFallback,
              mode: "live",
              connectionSummary: "Live request failed; displaying the last usable local view until the next refresh succeeds.",
            } as DashboardResponse);
          }
          try {
            const demoPayload = await fetchDashboard("demo", deferredSymbol);
            if (!active) {
              return;
            }
            setFallbackTitle("Live data unavailable");
            setFallbackNotice(`${liveFallbackReasonFromError(reason)} The app is temporarily showing a labelled local fallback and will retry live data every minute.`);
            const labelledFallback = {
              ...demoPayload,
              mode: "live",
              connectionSummary: "Live request failed; displaying local fallback data until the next refresh succeeds.",
            } as DashboardResponse;
            setDashboard(labelledFallback);
            writeCachedDashboard(deferredSymbol, mode, labelledFallback);
            return;
          } catch (fallbackReason) {
            if (!active) {
              return;
            }
            if (currentFallback) {
              return;
            }
            setError(fallbackReason instanceof Error ? fallbackReason.message : "Dashboard request failed");
            return;
          }
        }
        setError(reason instanceof Error ? reason.message : "Dashboard request failed");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadDashboard();
    const refresh = mode === "live" ? window.setInterval(() => {
      if (document.visibilityState !== "hidden") {
        void loadDashboard(true);
      }
    }, LIVE_REFRESH_MS) : null;
    return () => {
      active = false;
      if (refresh) {
        window.clearInterval(refresh);
      }
    };
  }, [deferredSymbol, mode]);

  useEffect(() => {
    if (mode !== "demo") {
      return;
    }
    const socket = new WebSocket(websocketUrl());
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data) as { rows: Array<{ symbol: string; lastPrice: number; signal: string; confidence: number }> };
      setDashboard((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          watchlist: current.watchlist.map((row) => {
            const update = payload.rows.find((candidate) => candidate.symbol === row.symbol);
            return update
              ? { ...row, lastPrice: update.lastPrice, signal: update.signal as DashboardResponse["watchlist"][number]["signal"], confidence: update.confidence }
              : row;
          }),
        };
      });
    };
    return () => socket.close();
  }, [mode]);

  const summaryTiles = useMemo(() => {
    if (!dashboard) {
      return null;
    }
    return [
      {
        label: "Markets",
        value: String(dashboard.trackedAssets),
        hint: "Tracked in this workspace",
        accent: "linear-gradient(135deg,#1ec8ff,#52b0ff)",
        icon: <IconChart className="h-5 w-5" />,
      },
      {
        label: "Connection",
        value: mode === "live" ? "Live data" : "Demo data",
        hint: dashboard.health.every((item) => item.status === "healthy") ? "Verified and fresh" : dashboard.health.some((item) => item.status === "configured") ? "Configured, checking live health" : "Safe fallback ready",
        accent: "linear-gradient(135deg,#47f6a1,#0dbf73)",
        icon: <IconSignal className="h-5 w-5" />,
      },
      {
        label: "Best Buy Setup",
        value: dashboard.strongestBuy,
        hint: "Highest positive signal",
        accent: "linear-gradient(135deg,#4af59d,#1eb980)",
        icon: <IconTrendUp className="h-5 w-5" />,
      },
      {
        label: "Most Cautious",
        value: dashboard.strongestSell,
        hint: "Highest defensive signal",
        accent: "linear-gradient(135deg,#ff8d96,#ff5b71)",
        icon: <IconTrendDown className="h-5 w-5" />,
      },
      {
        label: "Market Mood",
        value: dashboard.marketRegimeSummary,
        hint: "Overall backdrop",
        accent: "linear-gradient(135deg,#f3ca6f,#ff9f62)",
        icon: <IconGauge className="h-5 w-5" />,
      },
      {
        label: "Alerts",
        value: String(dashboard.alertCount),
        hint: "Rules watching markets",
        accent: "linear-gradient(135deg,#88a1ff,#5e74ff)",
        icon: <IconBell className="h-5 w-5" />,
      },
    ];
  }, [dashboard, mode]);

  function chooseMode(nextMode: "demo" | "live") {
    setFallbackNotice(null);
    setMode(nextMode);
  }

  function chooseSymbol(symbol: string) {
    startTransition(() => {
      setSelectedSymbol(symbol);
      const cachedPayload = readCachedDashboard(symbol, mode);
      if (cachedPayload) {
        setDashboard(cachedPayload);
      }
    });
  }

  const chartMatchesSelection = dashboard?.chart.symbol === selectedSymbol;

  return (
    <AppFrame
      eyebrow="Live Research Workspace"
      title="Market Overview"
      subtitle="Watch prices, review clear buy/sell signals, and open deeper research when something catches your eye."
      actions={
        <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/4 p-1">
          <Button variant={mode === "demo" ? "default" : "ghost"} size="sm" onClick={() => chooseMode("demo")}>
            Demo data
          </Button>
          <Button variant={mode === "live" ? "default" : "ghost"} size="sm" onClick={() => chooseMode("live")}>
            Live data
          </Button>
        </div>
      }
    >
      {!dashboard && !error ? (
        <DashboardLoading mode={mode} />
      ) : error ? (
        <Card className="p-8">
          <p className="text-sm uppercase tracking-[0.28em] text-rose-300">Could not load markets</p>
          <h2 className="mt-3 text-2xl font-semibold text-white">The dashboard needs a refresh</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
            {error}. Try the Live/Demo switch above. If live data is slow, the app will keep demo data available instead of pretending stale data is fresh.
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {fallbackNotice && <LiveFallbackNotice title={fallbackTitle} message={fallbackNotice} />}

          {dashboard && <TopOpportunities rows={dashboard.watchlist} signal={dashboard.signal} />}

          <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
            <div className="order-2 min-w-0 xl:order-1">
              <WatchlistPanel
                rows={dashboard?.watchlist ?? []}
                selectedSymbol={selectedSymbol}
                onSelect={chooseSymbol}
              />
            </div>
            <div className="order-1 min-w-0 space-y-4 xl:order-2">
              {dashboard && (
                <div className="grid items-start gap-4 2xl:grid-cols-[minmax(0,1fr)_330px]">
                  {chartMatchesSelection ? (
                    <MarketChart chart={dashboard.chart} signal={dashboard.signal} hero />
                  ) : (
                    <SelectedMarketLoading symbol={selectedSymbol} mode={mode} />
                  )}
                  {chartMatchesSelection ? (
                    <SignalCard signal={dashboard.signal} compact />
                  ) : (
                    <Card className="p-5">
                      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Current view</p>
                      <h2 className="mt-2 text-2xl font-semibold text-white">Loading {selectedSymbol}</h2>
                      <p className="mt-2 text-sm leading-6 text-slate-400">
                        The app is fetching the selected market so the signal panel does not show the wrong asset.
                      </p>
                    </Card>
                  )}
                </div>
              )}
              <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
                {summaryTiles?.map((tile) => <SummaryTile key={tile.label} {...tile} compact />)}
              </div>
              {dashboard && (
                <MacroStrip macro={dashboard.macro} providerBadges={dashboard.providerBadges} portfolioSummary={dashboard.portfolioSummary} />
              )}
              {dashboard && <AnalyticsTabs dashboard={dashboard} />}
            </div>
          </div>

          {(isPending || loading) && (
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/14 bg-cyan-300/8 px-4 py-2 text-xs uppercase tracking-[0.24em] text-cyan-100">
              <IconSignal className="h-4 w-4" />
              {mode === "live" ? "Updating live context" : `Refreshing ${deferredSymbol}`}
            </div>
          )}
        </div>
      )}
    </AppFrame>
  );
}

function SelectedMarketLoading({ symbol, mode }: { symbol: string; mode: "demo" | "live" }) {
  return (
    <Card className="space-y-4 p-5">
      <div>
        <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">Switching market</p>
        <h2 className="mt-2 text-xl font-semibold text-white">{symbol} chart is loading</h2>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          {mode === "live"
            ? "Live data can take a moment; cached or demo fallback will be labelled if providers slow down."
            : "Demo data is loading from the local deterministic dataset."}
        </p>
      </div>
      <Skeleton className="h-[480px] w-full" />
      <div className="grid gap-3 md:grid-cols-2">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
    </Card>
  );
}

function DashboardLoading({ mode }: { mode: "demo" | "live" }) {
  return (
    <div className="space-y-4">
      <Card className="overflow-hidden p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-cyan-200">{mode === "live" ? "Connecting to live data" : "Preparing demo data"}</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">Loading your market workspace</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              Prices, signals, watchlist, and chart tools are loading. On localhost, live providers can take a few seconds on first open.
            </p>
          </div>
          <div className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-4 py-2 text-sm font-semibold text-cyan-100">
            {mode === "live" ? "Live data mode" : "Demo mode"}
          </div>
        </div>
      </Card>
      <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
        <Card className="space-y-3 p-4">
          <Skeleton className="h-8 w-36" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </Card>
        <Card className="space-y-4 p-4">
          <Skeleton className="h-8 w-44" />
          <Skeleton className="h-[420px] w-full" />
          <div className="grid gap-3 md:grid-cols-3">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        </Card>
      </div>
    </div>
  );
}
