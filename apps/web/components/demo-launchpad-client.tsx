"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { IconChart, IconGauge, IconShield, IconSignal, IconTrendUp } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchDemoBriefing, warmDemo } from "@/lib/api";

const quickActions = [
  { href: "/", label: "Open Dashboard", detail: "Start with watchlist, chart, signal card, and macro strip.", icon: IconChart },
  { href: "/strategy-tester", label: "Run Backtest", detail: "Show costs, walk-forward, equity, drawdown, and trades.", icon: IconTrendUp },
  { href: "/reports", label: "Export PDF", detail: "Generate a clean professional investment note.", icon: IconShield },
  { href: "/settings", label: "Check Providers", detail: "Show configured, degraded, disabled, and manual states.", icon: IconSignal },
];

export function DemoLaunchpadClient() {
  const [briefing, setBriefing] = useState<any>(null);
  const [warmup, setWarmup] = useState<any>(null);
  const [warming, setWarming] = useState(false);

  useEffect(() => {
    fetchDemoBriefing().then(setBriefing);
  }, []);

  async function handleWarmup() {
    setWarming(true);
    try {
      setWarmup(await warmDemo());
    } finally {
      setWarming(false);
    }
  }

  return (
    <AppFrame
      eyebrow="Guided Mode"
      title="Demo Guide"
      subtitle="A guided route through the strongest product story: deterministic demo data, explainable signals, backtests, PDF export, provider health, and safety controls."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="secondary" className="rounded-full" onClick={handleWarmup} disabled={warming}>
            {warming ? "Warming..." : "Warm demo cache"}
          </Button>
          <Link href="/">
            <Button size="sm" className="rounded-full">Start demo</Button>
          </Link>
        </div>
      }
    >
      {!briefing ? (
        <Card className="p-8 text-sm text-slate-400">Preparing demo briefing...</Card>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
            <Card className="overflow-hidden p-0">
              <div className="border-b border-white/8 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.18),transparent_35%),linear-gradient(135deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))] p-6">
                <Badge className="border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Ready-to-demo flow</Badge>
                <h2 className="mt-5 max-w-2xl text-3xl font-semibold tracking-tight text-white">{briefing.title}</h2>
                <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">
                  Use this page as a safe starting point before showing the app. It keeps the product story crisp and makes sure the most useful working paths are one click away.
                </p>
              </div>
              <div className="grid gap-3 p-5 md:grid-cols-2">
                {quickActions.map((action) => {
                  const Icon = action.icon;
                  return (
                    <Link key={action.href} href={action.href} className="rounded-[24px] border border-white/8 bg-white/4 p-5 transition hover:border-cyan-300/25 hover:bg-cyan-300/8">
                      <Icon className="h-5 w-5 text-cyan-200" />
                      <h3 className="mt-4 text-lg font-semibold text-white">{action.label}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-400">{action.detail}</p>
                    </Link>
                  );
                })}
              </div>
            </Card>

            <Card className="p-5">
              <div className="flex items-center gap-2">
                <IconGauge className="h-5 w-5 text-emerald-200" />
                <h2 className="text-lg font-semibold text-white">Demo Readiness</h2>
              </div>
              <div className="mt-5 space-y-3">
                {briefing.readinessScore && (
                  <div className="rounded-[22px] border border-cyan-300/15 bg-cyan-300/8 p-4">
                    <p className="text-sm font-medium text-white">Overall readiness {briefing.readinessScore.score}/100</p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">Status: {briefing.readinessScore.status}. Use this as the final pre-demo confidence check.</p>
                  </div>
                )}
                {briefing.readiness.map((item: any) => (
                  <div key={item.label} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-white">{item.label}</p>
                      <Badge className={item.status === "ready" ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : "border-amber-300/20 bg-amber-300/10 text-amber-100"}>
                        {item.status}
                      </Badge>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{item.detail}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {warmup && (
            <Card className="border-cyan-300/14 bg-cyan-300/7 p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-cyan-100">Fast demo cache</p>
                  <h2 className="mt-2 text-xl font-semibold text-white">Warmup {warmup.status}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    Primed {warmup.warmed?.length ?? 0} demo paths in {Math.round(Number(warmup.durationMs ?? 0))}ms. Open the dashboard now for the fastest presentation path.
                  </p>
                </div>
                <Badge className={warmup.status === "ready" ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : "border-amber-300/20 bg-amber-300/10 text-amber-100"}>
                  {warmup.status}
                </Badge>
              </div>
            </Card>
          )}

          <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Live talking points</p>
              <div className="mt-4 space-y-3">
                {briefing.talkingPoints.map((point: string) => (
                  <div key={point} className="rounded-[20px] border border-white/8 bg-white/4 p-4 text-sm leading-6 text-slate-300">
                    {point}
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Suggested route order</p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {briefing.routeSequence.map((step: any, index: number) => (
                  <Link key={step.route} href={step.route} className="rounded-[22px] border border-white/8 bg-white/4 p-4 transition hover:border-cyan-300/20 hover:bg-cyan-300/8">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-white">{index + 1}. {step.label}</p>
                      <Badge>{step.route}</Badge>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{step.goal}</p>
                  </Link>
                ))}
              </div>
            </Card>
          </div>

          {briefing.checklist && (
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Timed walkthrough checklist</p>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                {briefing.checklist.map((item: any, index: number) => (
                  <Link key={item.route} href={item.route} className="rounded-[22px] border border-white/8 bg-white/4 p-4 transition hover:border-cyan-300/20 hover:bg-cyan-300/8">
                    <p className="text-sm font-semibold text-white">{index + 1}. {item.label}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.18em] text-cyan-100">{item.durationSeconds}s target</p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{item.proof}</p>
                  </Link>
                ))}
              </div>
            </Card>
          )}

          <div className="grid gap-4 md:grid-cols-4">
            <Metric label="Tracked assets" value={briefing.metrics.trackedAssets} />
            <Metric label="Alerts" value={briefing.metrics.alerts} />
            <Metric label="Reports" value={briefing.metrics.reports} />
            <Metric label="Macro regime" value={briefing.metrics.macroRegime} />
          </div>
        </div>
      )}
    </AppFrame>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="p-5">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <h2 className="mt-3 text-2xl font-semibold text-white">{value}</h2>
    </Card>
  );
}
