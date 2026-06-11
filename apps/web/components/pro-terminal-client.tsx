"use client";

import { useEffect, useMemo, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { BrandLogo } from "@/components/brand-logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchProTerminal } from "@/lib/api";
import { useMarketMode } from "@/lib/use-market-mode";

function ToneBadge({ label, tone = "neutral" }: { label: string; tone?: "positive" | "negative" | "neutral" | "warn" }) {
  const className =
    tone === "positive"
      ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"
      : tone === "negative"
        ? "border-rose-300/20 bg-rose-300/10 text-rose-100"
        : tone === "warn"
          ? "border-amber-300/20 bg-amber-300/10 text-amber-100"
          : "";
  return <Badge className={className}>{label}</Badge>;
}

export function ProTerminalClient() {
  const [mode, setMode] = useMarketMode();
  const [payload, setPayload] = useState<any>(null);
  const [category, setCategory] = useState("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setPayload(null);
    setError(null);
    fetchProTerminal(mode)
      .then((data) => active && setPayload(data))
      .catch((reason) => {
        if (!active) return;
        if (mode === "live") {
          setError("Live Pro Terminal data is temporarily unavailable. Stay in Live to retry, or switch to Demo for deterministic local evidence.");
          return;
        }
        setError(reason instanceof Error ? reason.message : "Pro Terminal failed");
      });
    return () => {
      active = false;
    };
  }, [mode, setMode]);

  const categories = useMemo(() => {
    if (!payload) return ["all"];
    return ["all", ...Array.from(new Set(payload.featureCoverage.map((item: any) => item.category))).sort() as string[]];
  }, [payload]);

  const features = useMemo(() => {
    if (!payload) return [];
    if (category === "all") return payload.featureCoverage;
    return payload.featureCoverage.filter((item: any) => item.category === category);
  }, [category, payload]);

  return (
    <AppFrame
      eyebrow="Advanced Research"
      title="Professional Research Toolkit"
      subtitle="A fast showcase of the advanced research toolkit, adapted from premium broker and research-platform workflows while staying paper-only and decision-support focused."
      actions={
        <div className="flex gap-2">
          <Button size="sm" variant={mode === "demo" ? "default" : "secondary"} onClick={() => setMode("demo")}>Demo</Button>
          <Button size="sm" variant={mode === "live" ? "default" : "secondary"} onClick={() => setMode("live")}>Live</Button>
        </div>
      }
    >
      {error ? (
        <Card className="border-rose-400/20 bg-rose-500/8 p-5 text-sm text-rose-100">{error}</Card>
      ) : !payload ? (
        <Card className="p-5 text-sm text-slate-400">Preparing the research toolkit...</Card>
      ) : (
        <div className="space-y-5">
          <Card className="overflow-hidden p-5">
            <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
              <div className="rounded-[30px] border border-cyan-300/10 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.18),transparent_32%),linear-gradient(135deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))] p-6">
                <BrandLogo />
                <p className="mt-5 text-sm leading-6 text-slate-300">
                  Advanced workspace for the upgraded application: research workflow, risk controls, learning support, provider transparency, and demo-safe evidence in one place.
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                  <ToneBadge label={`${payload.featureCoverage.length} research modules`} tone="positive" />
                  <ToneBadge label="paper only" tone="warn" />
                  <ToneBadge label={payload.mode} />
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <MetricCard label="Portfolio health" value={`${payload.riskNavigator.portfolioHealthScore}/100`} detail="IBKR-style risk summary" />
                <MetricCard label="Breadth risk-on" value={`${payload.breadth.riskOnScore}%`} detail="participation across local universe" />
                <MetricCard label="API keys needed" value={payload.apiKeyGuidance.needMoreKeys ? "Yes" : "No"} detail={payload.apiKeyGuidance.summary} />
              </div>
            </div>
          </Card>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
            <div className="space-y-4">
              <Card className="p-5">
                <SectionHeader title="Market Heat Map" subtitle="Moomoo/Bloomberg-style colour blocks by recent move." />
                <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-6">
                  {payload.marketHeatmap.slice(0, 18).map((item: any) => (
                    <div
                      key={item.symbol}
                      className={`rounded-2xl border p-3 ${item.tone === "positive" ? "border-emerald-300/15 bg-emerald-400/10" : "border-rose-300/15 bg-rose-400/10"}`}
                      style={{ opacity: 0.55 + item.intensity * 0.45 }}
                    >
                      <p className="font-semibold text-white">{item.symbol}</p>
                      <p className="mt-1 text-xs text-slate-400">{item.group}</p>
                      <p className={`mt-2 text-sm font-semibold ${item.tone === "positive" ? "text-emerald-100" : "text-rose-100"}`}>{item.value}%</p>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5">
                <SectionHeader title="Research Modules" subtitle="Advanced tools are categorised and linked to a research-safe implementation path." />
                <div className="mt-4 flex max-h-32 flex-wrap gap-2 overflow-auto pr-1">
                  {categories.map((item) => (
                    <Button key={item} size="sm" variant={category === item ? "default" : "secondary"} onClick={() => setCategory(item)}>
                      {item}
                    </Button>
                  ))}
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {features.map((item: any) => (
                    <div key={item.id} className="rounded-2xl border border-white/8 bg-white/4 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm font-semibold text-white">{item.id}. {item.name}</p>
                        <ToneBadge label={item.status} tone="positive" />
                      </div>
                      <p className="mt-2 text-xs leading-5 text-slate-500">{item.implementation}</p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <div className="space-y-4">
              <Card className="p-5">
                <SectionHeader title="Discovery Cards" subtitle="Broker-app style opportunity tiles." />
                <div className="mt-4 space-y-3">
                  {payload.assetDiscovery.map((item: any) => (
                    <div key={item.label} className="rounded-2xl border border-white/8 bg-white/4 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium text-white">{item.label}</p>
                        <ToneBadge label={item.symbol} />
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{item.detail}</p>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5">
                <SectionHeader title="Portfolio Pies" subtitle="Trading 212-inspired, paper-only model allocation." />
                <div className="mt-4 space-y-3">
                  {payload.portfolioPies.map((pie: any) => (
                    <div key={pie.name} className="rounded-2xl border border-cyan-300/10 bg-cyan-300/5 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-white">{pie.name}</p>
                        <ToneBadge label={pie.risk} tone={pie.risk.includes("high") ? "warn" : "neutral"} />
                      </div>
                      <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-slate-900">
                        {pie.weights.map((weight: any) => (
                          <div key={weight.symbol} title={`${weight.symbol} ${weight.weight}%`} className="bg-cyan-300/70" style={{ width: `${weight.weight}%` }} />
                        ))}
                      </div>
                      <p className="mt-2 text-xs leading-5 text-slate-500">{pie.drift}</p>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="p-5">
                <SectionHeader title="Risk Navigator" subtitle="Portfolio stress, concentration, and macro guardrails." />
                <div className="mt-4 space-y-3">
                  {payload.riskNavigator.stressTests.map((test: any) => (
                    <div key={test.scenario} className="rounded-2xl bg-white/4 p-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium text-white">{test.scenario}</p>
                        <ToneBadge label={`${test.estimatedImpactPct}%`} tone={test.estimatedImpactPct < 0 ? "negative" : "positive"} />
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{test.note}</p>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="p-5">
              <SectionHeader title="Notification Inbox" subtitle="Signal, provider, macro, and evidence events." />
              <div className="mt-4 space-y-2">
                {payload.notificationInbox.map((item: any) => (
                  <div key={`${item.time}-${item.title}`} className="rounded-2xl border border-white/8 bg-white/4 p-3">
                    <ToneBadge label={item.kind} tone={item.severity === "medium" ? "warn" : "neutral"} />
                    <p className="mt-2 text-sm text-slate-200">{item.title}</p>
                  </div>
                ))}
              </div>
            </Card>
            <Card className="p-5">
              <SectionHeader title="Scenario Planner" subtitle="Bull/base/bear risk-reward framing." />
              <div className="mt-4 space-y-2">
                {payload.scenarioPlanner.cases.map((item: any) => (
                  <div key={item.case} className="rounded-2xl bg-white/4 p-3">
                    <div className="flex items-center justify-between">
                      <p className="font-medium capitalize text-white">{item.case}</p>
                      <ToneBadge label={`${item.target}`} />
                    </div>
                    <p className="mt-1 text-xs text-slate-500">Probability {item.probability} - invalidation: {item.invalidations[0]}</p>
                  </div>
                ))}
              </div>
            </Card>
            <Card className="p-5">
              <SectionHeader title="Learning + Lineage" subtitle="Beginner-friendly, marker-friendly evidence." />
              <div className="mt-4 space-y-2">
                {payload.learningCenter.lessons.slice(0, 5).map((item: any) => (
                  <div key={item.term} className="rounded-2xl bg-white/4 p-3">
                    <p className="text-sm font-semibold text-white">{item.term}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">{item.plainEnglish}</p>
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

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-[26px] border border-white/8 bg-white/4 p-5">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
      <p className="mt-2 text-sm leading-6 text-slate-400">{detail}</p>
    </div>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{title}</p>
      <p className="mt-2 text-sm leading-6 text-slate-400">{subtitle}</p>
    </div>
  );
}
