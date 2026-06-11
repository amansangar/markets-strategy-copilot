"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import {
  evaluateStrategyRule,
  fetchAlertBuilder,
  fetchChartWorkspace,
  fetchEventsCalendar,
  fetchMultiChart,
  fetchReplayLab,
  fetchScannerColumns,
  fetchStrategyBuilder,
  fetchTearSheet,
} from "@/lib/api";
import { DEMO_SYMBOLS } from "@/lib/constants";
import { useMarketMode } from "@/lib/use-market-mode";

const primarySymbols = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "BTCUSD", "GLD"];
const defaultStrategyRule = "CLOSE > EMA50 AND MACD > MACD_SIGNAL AND RSI > 50";

function terminalFallbackPayload(symbols: string[], timeframe: string) {
  const charts = symbols.map((item, index) => ({
    symbol: item,
    name: `${item} workspace pending`,
    assetClass: "Local fallback",
    lastPrice: "waiting for data",
    changePct: 0,
    series: Array.from({ length: 24 }, (_, pointIndex) => ({
      time: pointIndex,
      normalised: Math.sin((pointIndex + index) / 4) * 0.35,
      close: 0,
    })),
  }));

  return {
    timeframe,
    layoutOptions: ["2x2", "3x2", "focus-plus-mini"],
    activeLayout: charts.length > 4 ? "3x2" : "2x2",
    charts,
    comparison: {
      correlations: symbols.slice(0, 6).map((item, index) => ({
        pair: `${item}/SPY`,
        correlation: index === 0 ? "1.00" : "pending",
      })),
    },
  };
}

function terminalFallbackWorkspace(symbol: string) {
  return {
    symbol,
    savedLayouts: [
      { name: "Core research layout", timeframes: ["1d", "1h"], indicators: ["EMA 21/50", "VWAP", "RSI", "MACD"] },
      { name: "Breakout watch", timeframes: ["15m", "1h"], indicators: ["Volume", "Support/Resistance"] },
    ],
    drawings: [
      { kind: "status", label: "Data refresh pending", confidence: 0.5 },
      { kind: "guardrail", label: "No trade execution", confidence: 1 },
    ],
    patterns: [],
    note: "The terminal shell stays usable while the API refreshes. Values marked pending are not live market metrics.",
  };
}

function strategyBuilderFallbackPayload(symbol: string) {
  const evaluation = {
    passed: false,
    confidenceHint: 0,
    totalClauses: 3,
    decisionUse: "The rule editor is available while market context refreshes. Re-run once the API reconnects before using the result.",
    conditions: [
      { clause: "CLOSE > EMA50", passed: false, left: "pending", right: "pending" },
      { clause: "MACD > MACD_SIGNAL", passed: false, left: "pending", right: "pending" },
      { clause: "RSI > 50", passed: false, left: "pending", right: "pending" },
    ],
  };

  return {
    language: "Pine-lite local shell",
    supportedFields: ["CLOSE", "EMA50", "MACD", "MACD_SIGNAL", "RSI", "VWAP", "ATR"],
    templates: [{ name: "Momentum confirmation", rule: defaultStrategyRule, evaluation }],
    context: {
      symbol,
      snapshot: {
        Status: "Waiting for data refresh",
        Mode: "Local fallback",
        Guardrail: "No order execution",
      },
    },
  };
}

function replayLabFallbackPayload(symbol: string, cursor: number) {
  const start = Date.UTC(2026, 0, 1);
  return {
    symbol,
    cursor,
    cursorTime: new Date(start + cursor * 60 * 60 * 1000).toISOString(),
    controls: { speeds: ["1x", "5x", "15x"], modes: ["bars-only", "bars-news-filings", "signal-debug"] },
    bars: Array.from({ length: 90 }, (_, index) => ({
      time: new Date(start + index * 60 * 60 * 1000).toISOString(),
      close: 100 + Math.sin(index / 7) * 2 + index * 0.02,
    })),
    events: [],
    signals: [
      { index: 1, time: "local-shell-1", action: "BUY" },
      { index: 2, time: "local-shell-2", action: "SELL" },
      { index: 3, time: "local-shell-3", action: "BUY" },
    ],
    guardrail: "Local replay shell only: no lookahead leakage is introduced, and live cached evidence is reloaded when the API responds.",
  };
}

function LoadingCard({ label }: { label: string }) {
  return <Card className="p-5 text-sm text-slate-400">{label}</Card>;
}

function ErrorCard({ error }: { error: string }) {
  return <Card className="border-rose-400/20 bg-rose-500/8 p-5 text-sm text-rose-100">{error}</Card>;
}

function FieldBadge({ label, tone = "neutral" }: { label: string; tone?: "neutral" | "good" | "warn" }) {
  const toneClass = tone === "good" ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : tone === "warn" ? "border-amber-300/20 bg-amber-300/10 text-amber-100" : "";
  return <Badge className={toneClass}>{label}</Badge>;
}

function humaniseKey(value: string) {
  return value
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replaceAll(".", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatFriendlyValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(formatFriendlyValue).join(", ");
  }
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, nestedValue]) => `${humaniseKey(key)}: ${formatFriendlyValue(nestedValue)}`)
      .join(" | ");
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (typeof value === "string") {
    return value
      .replace(/\bprovider\.status\b/gi, "provider status")
      .replace(/\bsignal\.action\b/gi, "signal action")
      .replaceAll("_", " ")
      .replace(/([a-z])([A-Z])/g, "$1 $2")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }
  return String(value ?? "Not set");
}

function FriendlyRuleSummary({ rule }: { rule: Record<string, unknown> }) {
  return (
    <div className="mt-5 grid gap-3 md:grid-cols-2">
      {Object.entries(rule).map(([key, value]) => (
        <div key={key} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{humaniseKey(key)}</p>
          <p className="mt-2 text-sm font-semibold leading-6 text-white">{formatFriendlyValue(value)}</p>
        </div>
      ))}
    </div>
  );
}

function MiniLine({ points, valueKey = "normalised" }: { points: any[]; valueKey?: string }) {
  const path = useMemo(() => {
    if (!points?.length) return "";
    const values = points.map((point) => Number(point[valueKey] ?? point.returnPct ?? point.close ?? 0));
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    return values
      .map((value, index) => {
        const x = (index / Math.max(values.length - 1, 1)) * 100;
        const y = 42 - ((value - min) / span) * 36;
        return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(" ");
  }, [points, valueKey]);
  return (
    <svg viewBox="0 0 100 48" className="h-20 w-full overflow-visible">
      <path d={path} fill="none" stroke="url(#terminalLine)" strokeWidth="2.5" strokeLinecap="round" />
      <defs>
        <linearGradient id="terminalLine" x1="0" x2="1">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="#34d399" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function EmptyNotice({ text }: { text: string }) {
  return <div className="rounded-3xl border border-dashed border-white/10 bg-white/4 p-6 text-sm leading-6 text-slate-400">{text}</div>;
}

export function StrategyBuilderClient() {
  const [mode, setMode] = useMarketMode();
  const [symbol, setSymbol] = useState("SPY");
  const [payload, setPayload] = useState<any>(null);
  const [rule, setRule] = useState(defaultStrategyRule);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    fetchStrategyBuilder(symbol, mode)
      .then((data) => {
        if (!active) return;
        setPayload(data);
        setRule(data.templates?.[0]?.rule ?? defaultStrategyRule);
        setResult(data.templates?.[0]?.evaluation ?? null);
      })
      .catch(() => {
        if (!active) return;
        const fallback = strategyBuilderFallbackPayload(symbol);
        setPayload(fallback);
        setRule(fallback.templates[0].rule);
        setResult(fallback.templates[0].evaluation);
      });
    return () => {
      active = false;
    };
  }, [mode, symbol]);

  async function evaluate() {
    try {
      const data = await evaluateStrategyRule({ symbol, mode, rule });
      setResult(data.evaluation);
    } catch {
      setResult({
        passed: false,
        confidenceHint: 0,
        decisionUse: "Could not evaluate against current market context. The rule text is saved on screen; retry when the API is reachable.",
        conditions: [{ clause: rule, passed: false, left: "pending", right: "pending" }],
      });
    }
  }

  return (
    <AppFrame
      eyebrow="Strategy Builder"
      title="Pine-Lite Strategy Lab"
      subtitle="Create safe TradingView-style rule candidates, inspect why they pass or fail, then move validated ideas into scanner/backtest workflows."
      actions={<ModeSymbolControls mode={mode} setMode={setMode} symbol={symbol} setSymbol={setSymbol} />}
    >
      {error ? <ErrorCard error={error} /> : !payload ? <LoadingCard label="Opening strategy context..." /> : (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
          <Card className="p-5">
            <div className="flex flex-wrap items-center gap-2">
              <FieldBadge label={payload.language} tone="good" />
              <FieldBadge label={`${payload.supportedFields.length} fields`} />
              <FieldBadge label="no order execution" tone="warn" />
            </div>
            <textarea
              value={rule}
              onChange={(event) => setRule(event.target.value)}
              className="mt-5 min-h-36 w-full rounded-[26px] border border-white/10 bg-slate-950 p-4 font-mono text-sm leading-6 text-cyan-50 outline-none placeholder:text-slate-500 focus:border-cyan-300/40"
            />
            <div className="mt-4 flex flex-wrap gap-2">
              {payload.templates.map((item: any) => (
                <Button key={item.name} variant="secondary" size="sm" onClick={() => { setRule(item.rule); setResult(item.evaluation); }}>
                  {item.name}
                </Button>
              ))}
              <Button size="sm" onClick={evaluate}>Evaluate rule</Button>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {Object.entries(payload.context.snapshot).map(([key, value]) => (
                <Card key={key} className="bg-white/4 p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{key}</p>
                  <p className="mt-2 text-sm font-semibold text-white">{String(value)}</p>
                </Card>
              ))}
            </div>
          </Card>
          <Card className="p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Evaluation</p>
            {!result ? <EmptyNotice text="Evaluate a rule to see clause-by-clause evidence." /> : (
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-between rounded-3xl border border-white/8 bg-white/5 p-4">
                  <div>
                    <p className="text-sm text-slate-400">Result</p>
                    <p className="text-2xl font-semibold text-white">{result.passed ? "Matched" : "Blocked"}</p>
                  </div>
                  <FieldBadge label={`${Math.round(result.confidenceHint * 100)}% rule fit`} tone={result.passed ? "good" : "warn"} />
                </div>
                {result.conditions.map((item: any) => (
                  <div key={item.clause} className="rounded-2xl border border-white/8 bg-slate-950/70 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-mono text-xs text-slate-200">{item.clause}</p>
                      <FieldBadge label={item.passed ? "pass" : "fail"} tone={item.passed ? "good" : "warn"} />
                    </div>
                    <p className="mt-2 text-xs text-slate-500">Left {String(item.left)} vs right {String(item.right)}</p>
                  </div>
                ))}
                <p className="text-xs leading-5 text-slate-500">{result.decisionUse}</p>
              </div>
            )}
          </Card>
        </div>
      )}
    </AppFrame>
  );
}

export function TerminalClient() {
  const [symbols, setSymbols] = useState(primarySymbols.slice(0, 6));
  const [timeframe, setTimeframe] = useState("1d");
  const [symbol, setSymbol] = useState("SPY");
  const [payload, setPayload] = useState<any>(null);
  const [workspace, setWorkspace] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    setFallbackNotice(null);
    Promise.allSettled([fetchMultiChart(symbols, timeframe), fetchChartWorkspace(symbol)])
      .then(([chartResult, workspaceResult]) => {
        if (!active) return;
        const chartData = chartResult.status === "fulfilled" ? chartResult.value : terminalFallbackPayload(symbols, timeframe);
        const workspaceData = workspaceResult.status === "fulfilled" ? workspaceResult.value : terminalFallbackWorkspace(symbol);
        setPayload(chartData);
        setWorkspace(workspaceData);
        if (chartResult.status === "rejected" || workspaceResult.status === "rejected") {
          setFallbackNotice("Live terminal data was slow, so this page kept the workspace usable with a clearly labelled local fallback shell.");
        }
      })
      .catch((reason) => {
        if (!active) return;
        setPayload(terminalFallbackPayload(symbols, timeframe));
        setWorkspace(terminalFallbackWorkspace(symbol));
        setFallbackNotice(reason instanceof Error ? reason.message : "Terminal data is temporarily unavailable.");
      });
    return () => {
      active = false;
    };
  }, [symbols, timeframe, symbol]);

  function toggleSymbol(next: string) {
    setSymbols((current) => current.includes(next) ? current.filter((item) => item !== next) : [...current, next].slice(-8));
    setSymbol(next);
  }

  return (
    <AppFrame
      eyebrow="Research Terminal"
      title="Multi-Chart Workspace"
      subtitle="Multi-asset chart wall with saved layouts, comparison mode, automated support/resistance, and pattern confluence."
      actions={<div className="w-28"><NativeSelect value={timeframe} onChange={setTimeframe}>{["5m", "15m", "1h", "4h", "1d"].map((item) => <option key={item}>{item}</option>)}</NativeSelect></div>}
    >
      {error ? <ErrorCard error={error} /> : !payload || !workspace ? <LoadingCard label="Opening terminal workspace..." /> : (
        <div className="space-y-4">
          {fallbackNotice && (
            <Card className="border-amber-300/20 bg-amber-300/8 p-4 text-sm leading-6 text-amber-50">
              <span className="font-semibold">Data refresh notice:</span> {fallbackNotice}
            </Card>
          )}
          <Card className="p-4">
            <div className="flex flex-wrap gap-2">
              {primarySymbols.map((item) => (
                <Button key={item} size="sm" variant={symbols.includes(item) ? "default" : "secondary"} onClick={() => toggleSymbol(item)}>{item}</Button>
              ))}
            </div>
          </Card>
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
            <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
              {payload.charts.map((chart: any) => (
                <Card key={chart.symbol} className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Link href={`/asset/${chart.symbol}`} className="text-lg font-semibold text-white hover:text-cyan-100">{chart.symbol}</Link>
                      <p className="text-xs text-slate-500">{chart.name}</p>
                    </div>
                    <FieldBadge label={`${chart.changePct}%`} tone={chart.changePct >= 0 ? "good" : "warn"} />
                  </div>
                  <MiniLine points={chart.series} />
                  <p className="text-sm text-slate-400">Last {chart.lastPrice} - {chart.assetClass}</p>
                </Card>
              ))}
            </div>
            <div className="space-y-4">
              <Card className="p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Saved layouts</p>
                <div className="mt-4 space-y-3">
                  {workspace.savedLayouts.map((layout: any) => (
                    <div key={layout.name} className="rounded-2xl border border-white/8 bg-white/4 p-3">
                      <p className="font-medium text-white">{layout.name}</p>
                      <p className="mt-1 text-xs text-slate-500">{layout.timeframes.join(", ")} - {layout.indicators.join(", ")}</p>
                    </div>
                  ))}
                </div>
              </Card>
              <Card className="p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Auto drawings and patterns</p>
                <div className="mt-4 space-y-3">
                  {workspace.drawings.map((drawing: any) => (
                    <div key={`${drawing.kind}-${drawing.label}`} className="rounded-2xl border border-cyan-300/10 bg-cyan-300/5 p-3">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-cyan-50">{drawing.label}</p>
                        <FieldBadge label={`${Math.round(drawing.confidence * 100)}%`} />
                      </div>
                      <p className="mt-1 text-xs text-slate-400">{drawing.price ? `Price ${drawing.price}` : drawing.levels ? `${drawing.levels.length} fib levels` : `From ${drawing.from} to ${drawing.to}`}</p>
                    </div>
                  ))}
                </div>
              </Card>
              <Card className="p-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Correlation watch</p>
                <div className="mt-4 space-y-2">
                  {payload.comparison.correlations.slice(0, 6).map((item: any) => (
                    <div key={item.pair} className="flex items-center justify-between rounded-2xl bg-white/4 px-3 py-2 text-sm">
                      <span className="text-slate-300">{item.pair}</span>
                      <span className="font-semibold text-white">{item.correlation}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}
    </AppFrame>
  );
}

export function AlertBuilderClient() {
  const [payload, setPayload] = useState<any>(null);
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    fetchAlertBuilder().then(setPayload);
  }, []);

  return (
    <AppFrame eyebrow="Alert Center" title="Advanced Alert Builder" subtitle="Build explainable price, indicator, signal, provider, macro, filing, and stale-data alerts without any broker execution hooks.">
      {!payload ? <LoadingCard label="Opening alert templates..." /> : (
        <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
          <Card className="p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Templates</p>
            <div className="mt-4 space-y-2">
              {payload.templates.map((item: any, index: number) => (
                <button key={item.name} onClick={() => setSelected(index)} className={`w-full rounded-2xl border px-4 py-3 text-left transition ${selected === index ? "border-cyan-300/30 bg-cyan-300/10" : "border-white/8 bg-white/4 hover:bg-white/6"}`}>
                  <p className="text-sm font-semibold text-white">{item.name}</p>
                  <p className="mt-1 text-xs text-slate-500">{item.deliveries.join(", ")}</p>
                </button>
              ))}
            </div>
          </Card>
          <Card className="p-5">
            <div className="flex flex-wrap items-center gap-2">
              <FieldBadge label={payload.templates[selected].name} tone="good" />
              <FieldBadge label="explainable cooldown" />
              <FieldBadge label="safe delivery" tone="warn" />
            </div>
            <FriendlyRuleSummary rule={payload.templates[selected].rule} />
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {Object.entries(payload.deliveryPolicy).map(([key, value]) => (
                <Card key={key} className="bg-white/4 p-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{key}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{String(value)}</p>
                </Card>
              ))}
            </div>
            <div className="mt-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Existing local alerts</p>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {payload.existingAlerts.map((alert: any) => (
                  <div key={alert.id} className="rounded-2xl border border-white/8 bg-white/4 p-3 text-sm text-slate-300">
                    <span className="font-medium text-white">{alert.symbol}</span> - {alert.name} - {alert.enabled ? "enabled" : "disabled"}
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      )}
    </AppFrame>
  );
}

export function ReplayLabClient() {
  const [symbol, setSymbol] = useState("SPY");
  const [cursor, setCursor] = useState(120);
  const [payload, setPayload] = useState<any>(null);

  useEffect(() => {
    let active = true;
    fetchReplayLab(symbol, cursor)
      .then((data) => active && setPayload(data))
      .catch(() => active && setPayload(replayLabFallbackPayload(symbol, cursor)));
    return () => {
      active = false;
    };
  }, [symbol, cursor]);

  return (
    <AppFrame eyebrow="Market Replay" title="Replay Lab" subtitle="Step through cached bars, news, filings, and signal states at a historical cursor with no lookahead leakage." actions={<SymbolControl symbol={symbol} setSymbol={setSymbol} />}>
      {!payload ? <LoadingCard label="Opening replay lab..." /> : (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
          <Card className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Cursor</p>
                <p className="mt-2 text-lg font-semibold text-white">{payload.cursorTime}</p>
              </div>
              <div className="flex gap-2">{payload.controls.speeds.map((speed: string) => <FieldBadge key={speed} label={speed} />)}</div>
            </div>
            <input aria-label="Replay cursor" min={40} max={260} value={cursor} onChange={(event) => setCursor(Number(event.target.value))} type="range" className="mt-6 w-full accent-cyan-300" />
            <MiniLine points={payload.bars} valueKey="close" />
            <p className="mt-4 text-sm text-slate-400">{payload.guardrail}</p>
          </Card>
          <div className="space-y-4">
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Events revealed so far</p>
              <div className="mt-4 max-h-80 space-y-2 overflow-auto pr-1">
                {payload.events.length ? payload.events.map((event: any) => (
                  <div key={`${event.kind}-${event.time}-${event.title}`} className="rounded-2xl border border-white/8 bg-white/4 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-white">{event.title}</p>
                      <FieldBadge label={event.kind} />
                    </div>
                    <p className="mt-1 text-xs text-slate-500">{event.time} - {event.source}</p>
                  </div>
                )) : <EmptyNotice text="No news or filing events before this replay cursor." />}
              </div>
            </Card>
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Signal timeline</p>
              <div className="mt-4 grid grid-cols-5 gap-2">
                {payload.signals.slice(-15).map((signal: any) => (
                  <div key={signal.time} className="rounded-2xl bg-white/5 p-2 text-center">
                    <p className="text-[10px] text-slate-500">{signal.index}</p>
                    <p className="text-xs font-semibold text-white">{formatFriendlyValue(signal.action)}</p>
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

export function EventsCalendarClient() {
  const [mode, setMode] = useMarketMode();
  const [kind, setKind] = useState("all");
  const [payload, setPayload] = useState<any>(null);

  useEffect(() => {
    fetchEventsCalendar(mode).then(setPayload);
  }, [mode]);

  const events = useMemo(() => {
    if (!payload) return [];
    return kind === "all" ? payload.events : payload.events.filter((event: any) => event.kind === kind);
  }, [kind, payload]);

  return (
    <AppFrame eyebrow="Calendar" title="Economic, Earnings, News and Filing Calendar" subtitle="A single event radar for macro releases, demo earnings markers, SEC filings, and market-moving news context." actions={<ModeButtons mode={mode} setMode={setMode} />}>
      {!payload ? <LoadingCard label="Opening event calendar..." /> : (
        <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
          <Card className="p-5">
            <FieldBadge label={payload.macroRegime.regime} tone="good" />
            <p className="mt-4 text-sm leading-6 text-slate-300">{payload.macroRegime.summary}</p>
            <div className="mt-5"><NativeSelect value={kind} onChange={setKind}>{["all", "macro", "economic", "earnings", "filing", "news"].map((item) => <option key={item}>{item}</option>)}</NativeSelect></div>
            <p className="mt-4 text-xs leading-5 text-slate-500">{payload.caveat}</p>
          </Card>
          <div className="grid gap-3 md:grid-cols-2">
            {events.map((event: any) => (
              <Card key={`${event.time}-${event.title}`} className="p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <FieldBadge label={event.kind} />
                  <FieldBadge label={event.impact ?? "medium"} tone={event.impact === "high" ? "warn" : "neutral"} />
                  {event.symbol ? <FieldBadge label={event.symbol} /> : null}
                </div>
                <p className="mt-4 text-base font-semibold text-white">{event.title}</p>
                <p className="mt-2 text-xs text-slate-500">{event.time} - {event.source}</p>
              </Card>
            ))}
          </div>
        </div>
      )}
    </AppFrame>
  );
}

export function TearSheetClient() {
  const [mode, setMode] = useMarketMode();
  const [symbol, setSymbol] = useState("AAPL");
  const [payload, setPayload] = useState<any>(null);

  useEffect(() => {
    setPayload(null);
    fetchTearSheet(symbol, mode).then(setPayload);
  }, [mode, symbol]);

  return (
    <AppFrame eyebrow="Company Research" title="Fundamental Tear Sheet" subtitle="Koyfin-style asset profile combining market structure, fundamentals proxy, macro sensitivity, filings, news, and indicator state." actions={<ModeSymbolControls mode={mode} setMode={setMode} symbol={symbol} setSymbol={setSymbol} />}>
      {!payload ? <LoadingCard label="Opening tear sheet..." /> : (
        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{payload.profile.assetClass} - {payload.profile.venue}</p>
                <h2 className="mt-2 text-3xl font-semibold text-white">{payload.symbol} - {payload.profile.name}</h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">{payload.profile.description}</p>
              </div>
              <FieldBadge label={`${payload.profile.spreadBps} bps spread`} />
            </div>
          </Card>
          <div className="grid gap-4 xl:grid-cols-4">
            {Object.entries(payload.marketMetrics).map(([key, value]) => (
              <Card key={key} className="p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{key}</p>
                <p className="mt-2 text-lg font-semibold text-white">{formatFriendlyValue(value)}</p>
              </Card>
            ))}
          </div>
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Fundamental context</p>
              <div className="mt-4 space-y-3">
                {payload.fundamentalProxy.items.map((item: any) => (
                  <div key={item.label} className="rounded-2xl bg-white/4 p-3">
                    <p className="text-sm font-medium text-white">{item.label}</p>
                    <p className="mt-1 text-xs text-slate-500">{String(item.value)}</p>
                  </div>
                ))}
              </div>
            </Card>
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Macro sensitivity</p>
              <FieldBadge label={payload.macroSensitivity.regime} tone="good" />
              <p className="mt-4 text-sm leading-6 text-slate-300">{payload.macroSensitivity.summary}</p>
              <p className="mt-3 text-xs leading-5 text-slate-500">{payload.macroSensitivity.macroSummary}</p>
            </Card>
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Filings and news</p>
              <p className="mt-3 text-sm leading-6 text-slate-300">{payload.filings.headline}</p>
              <div className="mt-4 space-y-2">
                {payload.news.map((item: any) => (
                  <div key={item.title} className="rounded-2xl border border-white/8 bg-white/4 p-3 text-xs text-slate-400">{item.title} - {item.source}</div>
                ))}
              </div>
            </Card>
          </div>
          <p className="text-xs text-slate-500">{payload.caveat}</p>
        </div>
      )}
    </AppFrame>
  );
}

export function OpportunitiesClient() {
  const [scanner, setScanner] = useState<any>(null);
  const [ranked, setRanked] = useState<any>(null);
  const [visibleColumns, setVisibleColumns] = useState<string[]>([]);

  useEffect(() => {
    fetchScannerColumns().then((scannerData) => {
      setScanner(scannerData);
      setRanked({
        ranked: scannerData.rankedOpportunities,
        methodology: [
          "Ranks are deterministic from trend, RSI band, VWAP, MACD, ADX, and participation.",
          "News, filings, and macro context are shown as reasons but do not override risk gates.",
          "This list is for research triage and does not imply execution advice.",
        ],
      });
      setVisibleColumns(scannerData.defaultColumns);
    });
  }, []);

  function toggleColumn(column: string) {
    setVisibleColumns((current) => current.includes(column) ? current.filter((item) => item !== column) : [...current, column]);
  }

  function opportunityAction(row: any) {
    return String(row.action ?? row.signal ?? row.signalAction ?? row.status ?? "Research");
  }

  function opportunityTone(row: any): "good" | "warn" | "neutral" {
    const action = opportunityAction(row).toUpperCase();
    if (action.includes("BUY")) return "good";
    if (action.includes("SELL")) return "warn";
    return "neutral";
  }

  function opportunityReason(row: any) {
    if (Array.isArray(row.whyMatched)) return row.whyMatched.join(" + ");
    if (Array.isArray(row.reasons)) return row.reasons.join(" + ");
    return String(row.whyMatched ?? row.why ?? row.reason ?? "Matches deterministic scanner evidence and is ranked for human review.");
  }

  return (
    <AppFrame eyebrow="Opportunity Radar" title="Ranked Research Opportunities" subtitle="Trade Ideas-style triage list with custom scanner columns, saved presets, and an explicit why-this-ranked explanation.">
      {!scanner || !ranked ? <LoadingCard label="Opening opportunity radar..." /> : (
        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex flex-wrap gap-2">
              {scanner.availableColumns.map((column: string) => (
                <Button key={column} size="sm" variant={visibleColumns.includes(column) ? "default" : "secondary"} onClick={() => toggleColumn(column)}>{column}</Button>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">{scanner.savedPresets.map((preset: any) => <FieldBadge key={preset.name} label={preset.name} />)}</div>
          </Card>
          <div className="space-y-3 md:hidden">
            {ranked.ranked.map((row: any) => (
              <Link key={row.symbol} href={`/asset/${row.symbol}`} className="block rounded-[28px] border border-white/8 bg-white/4 p-4 transition hover:border-cyan-300/30 hover:bg-cyan-300/8">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-lg font-semibold text-white">{row.symbol}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">{humaniseKey(String(row.assetClass ?? row.category ?? "Research candidate"))}</p>
                  </div>
                  <FieldBadge label={humaniseKey(opportunityAction(row))} tone={opportunityTone(row)} />
                </div>
                <div className="mt-4 grid grid-cols-2 gap-2">
                  {visibleColumns.filter((column) => column !== "symbol").slice(0, 6).map((column) => (
                    <div key={column} className="rounded-2xl border border-white/8 bg-slate-950/40 p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">{humaniseKey(column)}</p>
                      <p className="mt-1 text-sm font-semibold text-white">{formatFriendlyValue(row[column])}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-4 text-sm leading-6 text-slate-300">
                  <span className="font-semibold text-cyan-100">Why ranked:</span> {opportunityReason(row)}
                </p>
              </Link>
            ))}
          </div>
          <Card className="hidden overflow-hidden p-0 md:block">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead className="border-b border-white/8 bg-white/5 text-xs uppercase tracking-[0.18em] text-slate-500">
                  <tr>{visibleColumns.map((column) => <th key={column} className="px-4 py-3">{column}</th>)}</tr>
                </thead>
                <tbody>
                  {ranked.ranked.map((row: any) => (
                    <tr key={row.symbol} className="border-b border-white/6 text-slate-300">
                      {visibleColumns.map((column) => (
                        <td key={column} className="px-4 py-3">
                          {column === "symbol" ? <Link href={`/asset/${row.symbol}`} className="font-semibold text-cyan-100 hover:text-white">{row.symbol}</Link> : String(row[column] ?? "-")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <Card className="p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Methodology</p>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              {ranked.methodology.map((item: string) => <div key={item} className="rounded-2xl bg-white/4 p-4 text-sm leading-6 text-slate-300">{item}</div>)}
            </div>
          </Card>
        </div>
      )}
    </AppFrame>
  );
}

function ModeButtons({ mode, setMode }: { mode: "demo" | "live"; setMode: (mode: "demo" | "live") => void }) {
  return (
    <div className="flex gap-2">
      <Button variant={mode === "demo" ? "default" : "secondary"} size="sm" onClick={() => setMode("demo")}>Demo</Button>
      <Button variant={mode === "live" ? "default" : "secondary"} size="sm" onClick={() => setMode("live")}>Live</Button>
    </div>
  );
}

function SymbolControl({ symbol, setSymbol }: { symbol: string; setSymbol: (symbol: string) => void }) {
  return <div className="w-32"><NativeSelect value={symbol} onChange={setSymbol}>{DEMO_SYMBOLS.map((item) => <option key={item}>{item}</option>)}</NativeSelect></div>;
}

function ModeSymbolControls({
  mode,
  setMode,
  symbol,
  setSymbol,
}: {
  mode: "demo" | "live";
  setMode: (mode: "demo" | "live") => void;
  symbol: string;
  setSymbol: (symbol: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <SymbolControl symbol={symbol} setSymbol={setSymbol} />
      <ModeButtons mode={mode} setMode={setMode} />
    </div>
  );
}
