"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { LiveFallbackNotice } from "@/components/live-fallback-notice";
import { fetchScanner } from "@/lib/api";
import { liveFallbackReasonFromError } from "@/lib/live-fallback";
import { useMarketMode } from "@/lib/use-market-mode";
import { cn } from "@/lib/utils";

const LIVE_REFRESH_MS = 60_000;

export function ScannerClient() {
  const [mode, setMode] = useMarketMode();
  const [action, setAction] = useState("ALL");
  const [minConfidence, setMinConfidence] = useState(0.1);
  const [payload, setPayload] = useState<any>(null);
  const payloadRef = useRef<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);

  const params = useMemo(() => {
    const search = new URLSearchParams();
    search.set("mode", mode);
    if (action !== "ALL") {
      search.set("action", action);
    }
    search.set("min_confidence", String(minConfidence));
    return search;
  }, [action, minConfidence, mode]);

  useEffect(() => {
    let cancelled = false;

    async function loadScanner(background = false) {
      if (!background) {
        setIsLoading(true);
      }
      setError(null);
      try {
        const data = await fetchScanner(params);
        if (!cancelled) {
          setFallbackNotice(null);
          payloadRef.current = data;
          setPayload(data);
        }
      } catch (reason) {
        if (cancelled) {
          return;
        }

        if (mode === "live") {
          const fallbackParams = new URLSearchParams(params);
          fallbackParams.set("mode", "demo");
          try {
            const fallbackData = await fetchScanner(fallbackParams);
            if (!cancelled) {
              setFallbackNotice(
                `${liveFallbackReasonFromError(reason)} Showing clearly labelled cached demo scanner rows until live data refreshes.`,
              );
              const labelledFallback = { ...fallbackData, mode: "live", source: "local_fallback" };
              payloadRef.current = labelledFallback;
              setPayload(labelledFallback);
            }
            return;
          } catch {
            if (!cancelled) {
              setFallbackNotice(liveFallbackReasonFromError(reason));
              setError("Scanner data is unavailable. Run the demo seed script and retry.");
            }
          }
        } else {
          setError(reason instanceof Error ? reason.message : "Scanner data is unavailable.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadScanner();
    const refresh = mode === "live" ? window.setInterval(() => {
      if (document.visibilityState !== "hidden") {
        void loadScanner(true);
      }
    }, LIVE_REFRESH_MS) : null;
    return () => {
      cancelled = true;
      if (refresh) {
        window.clearInterval(refresh);
      }
    };
  }, [mode, params]);

  return (
    <AppFrame
      eyebrow="Signal Discovery"
      title="Find Opportunities"
      subtitle="Filter markets by signal, confidence, trend, volume, and news mood to find what deserves your attention first."
      actions={
        <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/4 p-1">
          <Button variant={mode === "demo" ? "default" : "ghost"} size="sm" onClick={() => { setFallbackNotice(null); setMode("demo"); }}>
            Demo data
          </Button>
          <Button variant={mode === "live" ? "default" : "ghost"} size="sm" onClick={() => { setFallbackNotice(null); setMode("live"); }}>
            Live data
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {fallbackNotice && <LiveFallbackNotice message={fallbackNotice} />}

        <Card className="grid gap-4 p-5 md:grid-cols-3">
          <div>
            <p className="mb-2 text-xs uppercase tracking-[0.24em] text-slate-500">Signal</p>
            <NativeSelect value={action} onChange={setAction}>
                  {["ALL", "STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL", "NO_SIGNAL"].map((item) => (
                <option key={item} value={item}>
                  {item.replaceAll("_", " ")}
                </option>
              ))}
            </NativeSelect>
          </div>
          <label className="block">
            <p className="mb-2 text-xs uppercase tracking-[0.24em] text-slate-500">Minimum confidence</p>
            <input
              type="range"
              min={0.1}
              max={0.95}
              step={0.05}
              value={minConfidence}
              onChange={(event) => setMinConfidence(Number(event.target.value))}
              className="w-full accent-cyan-300"
            />
            <p className="mt-2 text-sm text-slate-400">{Math.round(minConfidence * 100)}%</p>
          </label>
          <div className="rounded-[22px] border border-white/8 bg-white/4 p-4 text-sm text-slate-300">
            Each result explains why it matched, using trend, momentum, volume, price position, and news mood.
          </div>
        </Card>

        <div className="space-y-3 md:hidden">
          {isLoading ? (
            <Card className="p-5 text-sm text-slate-400">Finding opportunities and checking the latest signals...</Card>
          ) : error ? (
            <Card className="p-5 text-sm text-amber-200">{error}</Card>
          ) : payload?.results?.length ? (
            payload.results.map((row: any) => (
              <Link key={row.symbol} href={`/asset/${row.symbol}`} className="block">
                <Card className="p-4 transition hover:border-cyan-300/30 hover:bg-cyan-300/5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-lg font-semibold text-white">{row.symbol}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">{row.regime.replaceAll("_", " ")}</p>
                    </div>
                    <div className="text-right">
                      <ActionBadge action={row.action} />
                      <p className="text-sm text-slate-400">{Math.round(row.confidence * 100)}% confidence</p>
                    </div>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-slate-300">
                    <span>RSI {row.rsi}</span>
                    <span>MACD {row.macdState}</span>
                    <span>VWAP {row.priceVsVwap}</span>
                    <span>Volume {row.volumeSpike ? "spike" : "normal"}</span>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-slate-400">{row.whyThisAppeared}</p>
                </Card>
              </Link>
            ))
          ) : (
            <Card className="p-5 text-sm text-slate-400">No markets match these filters. Lower confidence or switch the signal filter back to All.</Card>
          )}
        </div>

        <Card className="hidden overflow-hidden md:block">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-white/8 bg-white/4 text-slate-400">
                <tr>
                  {["Symbol", "Action", "Confidence", "Regime", "RSI", "MACD", "VWAP", "ADX", "Volume", "Sentiment", "Why"].map((column) => (
                    <th key={column} className="px-4 py-3 font-medium">{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={11} className="px-4 py-8 text-center text-slate-400">
                      Finding opportunities and checking the latest signals...
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={11} className="px-4 py-8 text-center text-amber-200">
                      {error}
                    </td>
                  </tr>
                ) : payload?.results?.length ? (
                  payload.results.map((row: any) => (
                  <tr key={row.symbol} className="border-b border-white/6 text-slate-200">
                    <td className="px-4 py-3">
                      <Link href={`/asset/${row.symbol}`} className="text-cyan-200 hover:text-cyan-100">{row.symbol}</Link>
                    </td>
                    <td className="px-4 py-3"><ActionBadge action={row.action} /></td>
                    <td className="px-4 py-3">{Math.round(row.confidence * 100)}%</td>
                    <td className="px-4 py-3">{row.regime.replaceAll("_", " ")}</td>
                    <td className="px-4 py-3">{row.rsi}</td>
                    <td className="px-4 py-3">{row.macdState}</td>
                    <td className="px-4 py-3">{row.priceVsVwap}</td>
                    <td className="px-4 py-3">{row.adx}</td>
                    <td className="px-4 py-3">{row.volumeSpike ? "Spike" : "Normal"}</td>
                    <td className="px-4 py-3">{row.sentiment.toFixed(2)}</td>
                    <td className="px-4 py-3 text-slate-400">{row.whyThisAppeared}</td>
                  </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={11} className="px-4 py-8 text-center text-slate-400">
                      No markets match these filters. Lower confidence or switch the signal filter back to All.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppFrame>
  );
}

function ActionBadge({ action }: { action: string }) {
  return (
    <span className={cn("inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em]", actionClasses(action))}>
      {action.replaceAll("_", " ")}
    </span>
  );
}

function actionClasses(action: string) {
  if (action === "STRONG_BUY") return "border-emerald-200/35 bg-emerald-300/18 text-emerald-50";
  if (action === "BUY") return "border-emerald-300/25 bg-emerald-300/10 text-emerald-100";
  if (action === "STRONG_SELL") return "border-rose-200/35 bg-rose-300/18 text-rose-50";
  if (action === "SELL") return "border-rose-300/25 bg-rose-300/10 text-rose-100";
  if (action === "HOLD") return "border-amber-300/25 bg-amber-300/10 text-amber-100";
  return "border-slate-300/15 bg-slate-300/10 text-slate-200";
}
