"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { IconShield, IconSignal } from "@/components/icons";
import { AppFrame } from "@/components/app-frame";
import { LiveFallbackNotice } from "@/components/live-fallback-notice";
import { MarketChart } from "@/components/market-chart";
import { SignalCard } from "@/components/signal-card";
import { SignalDiffPanel } from "@/components/signal-diff-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { fetchAssetDetail, fetchReplay } from "@/lib/api";
import { DEMO_SYMBOLS } from "@/lib/constants";
import { formatDate, formatDateTime } from "@/lib/format";
import { liveFallbackReasonFromError, liveFallbackReasonFromHealth, shouldAttemptLiveFallback } from "@/lib/live-fallback";
import { useMarketMode } from "@/lib/use-market-mode";

const LIVE_REFRESH_MS = 60_000;
const LIVE_REPLAY_CURSOR = 9999;

export function AssetDetailClient({ symbol, initialDetail = null }: { symbol: string; initialDetail?: any | null }) {
  const router = useRouter();
  const [mode, setMode] = useMarketMode();
  const [detail, setDetail] = useState<any>(initialDetail);
  const detailRef = useRef<any>(initialDetail);
  const [cursor, setCursor] = useState(120);
  const [replay, setReplay] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);

  function changeSymbol(nextSymbol: string) {
    if (nextSymbol !== symbol.toUpperCase()) {
      router.push(`/asset/${nextSymbol}`);
    }
  }

  useEffect(() => {
    let active = true;
    setError(null);

    function applyPayload(payload: any) {
      const fallbackReason = shouldAttemptLiveFallback(mode) ? liveFallbackReasonFromHealth(payload.health) : null;
      if (fallbackReason) {
        setFallbackNotice(fallbackReason);
      } else {
        setFallbackNotice(null);
      }
      detailRef.current = payload;
      setDetail(payload);
    }

    async function loadDetail() {
      fetchAssetDetail(symbol, mode)
        .then((payload) => {
          if (!active) {
            return;
          }
          applyPayload(payload);
        })
        .catch(async (reason) => {
          if (!active) {
            return;
          }
          if (shouldAttemptLiveFallback(mode)) {
            setFallbackNotice(`${liveFallbackReasonFromError(reason)} Live data is unavailable, so this page is showing deterministic demo fallback while it retries provider data.`);
            try {
              const fallbackPayload = await fetchAssetDetail(symbol, "demo");
              if (active) {
                const labelledFallback = {
                  ...fallbackPayload,
                  mode: "live",
                  connectionSummary: "Live data unavailable; showing deterministic demo fallback until provider refresh succeeds.",
                };
                detailRef.current = labelledFallback;
                setDetail(labelledFallback);
              }
            } catch {
              if (active && !detailRef.current) {
                setError("Asset detail needs seeded demo data. Run the demo seed script and retry.");
              }
            }
            return;
          }
          setError(reason instanceof Error ? reason.message : "Asset detail data is unavailable.");
        });
    }

    void loadDetail();
    const refresh = mode === "live" ? window.setInterval(() => {
      if (document.visibilityState !== "hidden") {
        void loadDetail();
      }
    }, LIVE_REFRESH_MS) : null;
    return () => {
      active = false;
      if (refresh) {
        window.clearInterval(refresh);
      }
    };
  }, [mode, symbol]);

  useEffect(() => {
    let active = true;
    const replayCursor = mode === "live" ? LIVE_REPLAY_CURSOR : cursor;

    async function loadReplay() {
      try {
        const payload = await fetchReplay(symbol, replayCursor, mode);
        if (active) {
          setReplay(payload);
        }
      } catch {
        if (active) {
          setReplay(null);
        }
      }
    }

    void loadReplay();
    const refresh = mode === "live" ? window.setInterval(() => {
      if (document.visibilityState !== "hidden") {
        void loadReplay();
      }
    }, LIVE_REFRESH_MS) : null;
    return () => {
      active = false;
      if (refresh) {
        window.clearInterval(refresh);
      }
    };
  }, [cursor, mode, symbol]);

  return (
    <AppFrame
      eyebrow="Asset Drilldown"
      title={`${symbol} Detail`}
      subtitle="Inspect deeper indicator state, news chronology, audit evidence, and data-source health for a single asset."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <div className="min-w-[160px]">
            <NativeSelect value={symbol.toUpperCase()} onChange={changeSymbol}>
              {DEMO_SYMBOLS.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </NativeSelect>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/4 p-1">
            <Button variant={mode === "demo" ? "default" : "ghost"} size="sm" onClick={() => { setFallbackNotice(null); setMode("demo"); }}>
              Demo
            </Button>
            <Button variant={mode === "live" ? "default" : "ghost"} size="sm" onClick={() => { setFallbackNotice(null); setMode("live"); }}>
              Live
            </Button>
          </div>
        </div>
      }
    >
      {fallbackNotice && <div className="mb-4"><LiveFallbackNotice message={fallbackNotice} /></div>}

      {error ? (
        <Card className="p-8">
          <p className="text-sm uppercase tracking-[0.28em] text-rose-300">Asset detail error</p>
          <h2 className="mt-3 text-2xl font-semibold text-white">{error}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">The app is showing this technical failure instead of hiding stale or unreliable data.</p>
        </Card>
      ) : !detail ? (
        <Card className="p-8 text-sm text-slate-400">Loading asset detail...</Card>
      ) : (
        <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="space-y-4">
            <Card className="p-5">
              <div className="grid gap-4 md:grid-cols-[minmax(0,1.2fr)_repeat(3,minmax(0,0.7fr))]">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Selected market</p>
                  <h2 className="mt-2 text-2xl font-semibold text-white">{detail.symbol}</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-400">{detail.metadata.description}</p>
                </div>
                <MiniFact label="Asset class" value={detail.metadata.assetClass} />
                <MiniFact label="Venue" value={detail.metadata.venue} />
                <MiniFact label="Spread" value={`${detail.metadata.avgSpreadBps} bps`} />
              </div>
            </Card>
            <MarketChart chart={detail.chart} />
            <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
              <SignalDiffPanel diff={detail.signalDiff} />
              <Card className="p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Market replay</p>
                <h2 className="mt-2 text-lg font-semibold text-white">{replay?.cursorTime ? formatDateTime(replay.cursorTime) : "Loading replay"}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">{replay?.lookaheadGuard ?? "Replay uses cached bars and hides future data beyond the cursor."}</p>
                {mode === "live" ? (
                  <div className="mt-4 rounded-2xl border border-cyan-300/14 bg-cyan-300/8 p-4 text-sm leading-6 text-cyan-50">
                    Live replay follows the latest available bar and refreshes every minute with the chart, news, signal, and audit context.
                  </div>
                ) : (
                  <>
                    <div className="mt-4 grid gap-2">
                      {(detail.replayScenarios ?? []).map((scenario: any) => (
                        <button
                          key={scenario.id}
                          type="button"
                          aria-label={`Replay scenario: ${scenario.label}`}
                          onClick={() => setCursor(Number(scenario.cursor))}
                          className="relative z-10 min-h-16 rounded-2xl border border-white/8 bg-white/4 px-3 py-2 text-left text-sm transition-colors hover:border-cyan-300/25 hover:bg-cyan-300/10 active:border-cyan-300/35 active:bg-cyan-300/12"
                        >
                          <span className="font-medium text-white">{scenario.label}</span>
                          <span className="mt-1 block text-xs leading-5 text-slate-500">{scenario.detail}</span>
                        </button>
                      ))}
                    </div>
                    <input
                      aria-label="Replay cursor"
                      className="mt-4 w-full accent-cyan-300"
                      type="range"
                      min={40}
                      max={260}
                      value={cursor}
                      onChange={(event) => setCursor(Number(event.target.value))}
                    />
                  </>
                )}
                <div className="mt-4 space-y-2">
                  {(replay?.signalTimeline ?? []).slice(-3).map((item: any) => (
                    <div key={item.time} className="flex items-center justify-between rounded-2xl border border-white/8 bg-white/4 px-3 py-2 text-sm">
                      <span className="text-slate-300">{formatDate(item.time)}</span>
                      <Badge>{item.action}</Badge>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
            <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
              <div className="space-y-4">
                <Card className="p-5">
                  <div className="flex items-center gap-2">
                    <IconSignal className="h-4 w-4 text-cyan-200" />
                    <h2 className="text-lg font-semibold text-white">News timeline</h2>
                  </div>
                  <div className="mt-4 space-y-3">
                    {detail.newsTimeline.map((item: any) => (
                      <div key={item.id} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                        <p className="text-sm font-medium leading-6 text-white">{item.title}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <Badge>{item.source}</Badge>
                          <Badge>Sentiment {item.sentiment.toFixed(2)}</Badge>
                          <Badge>Relevance {item.relevance.toFixed(2)}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card className="p-5">
                  <div className="flex items-center gap-2">
                    <IconShield className="h-4 w-4 text-amber-200" />
                    <h2 className="text-lg font-semibold text-white">SEC filings / event intelligence</h2>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-400">{detail.filingDigest.headline}</p>
                  <div className="mt-4 space-y-3">
                    {detail.filingTimeline.map((item: any) => (
                      <div key={item.id} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
                          <p className="text-sm font-medium text-white">{item.title}</p>
                          <Badge className="self-start sm:self-center">{item.filingType}</Badge>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-slate-400">{item.digest}</p>
                        <p className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-500">
                          {formatDate(item.filedAt)} • risk {item.riskLevel}
                        </p>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>

              <Card className="p-5">
                <div className="flex items-center gap-2">
                  <IconShield className="h-4 w-4 text-emerald-200" />
                  <h2 className="text-lg font-semibold text-white">Audit trail</h2>
                </div>
                <div className="mt-4 max-h-[520px] space-y-3 overflow-y-auto pr-1">
                  {detail.auditTrail.map((item: any) => (
                    <div key={item.createdAt} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                      <p className="text-sm font-medium text-white">
                        {item.action.replaceAll("_", " ")} at {(item.confidence * 100).toFixed(0)}%
                      </p>
                      <p className="mt-2 text-sm text-slate-400">
                        Policy pass: {item.policyPass ? "yes" : "no"} • {formatDateTime(item.createdAt)}
                      </p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>

          <div className="space-y-4 xl:sticky xl:top-4">
            <SignalCard signal={detail.signal} compact />
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Macro contribution</p>
              <h2 className="mt-2 text-lg font-semibold text-white">{detail.macro.regime.replaceAll("_", " ").toUpperCase()}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">{detail.macro.summary}</p>
            </Card>
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Source health</p>
              <div className="mt-4 max-h-[360px] space-y-3 overflow-y-auto pr-1">
                {detail.health.map((item: any) => (
                  <div key={item.name} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-white">{item.name}</p>
                      <Badge>{item.status}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-slate-400">{item.detail}</p>
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

function MiniFact({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/4 p-4">
      <p className="text-[10px] uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-white">{String(value).replaceAll("_", " ")}</p>
    </div>
  );
}
