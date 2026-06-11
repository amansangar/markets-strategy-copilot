"use client";

import { useEffect, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { ProviderFailoverTimeline } from "@/components/provider-failover-timeline";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchProviderFailoverTimeline, fetchSetupGuide, warmDemo } from "@/lib/api";
import { useMarketMode } from "@/lib/use-market-mode";

export function SetupGuideClient() {
  const [mode, setMode] = useMarketMode();
  const [guide, setGuide] = useState<any>(null);
  const [timeline, setTimeline] = useState<any>(null);
  const [warmup, setWarmup] = useState<any>(null);
  const [warming, setWarming] = useState(false);

  useEffect(() => {
    fetchSetupGuide(mode).then(setGuide);
    fetchProviderFailoverTimeline(mode).then(setTimeline);
  }, [mode]);

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
      eyebrow="Beginner Setup"
      title="Setup Guide"
      subtitle="A simple, no-secrets checklist for starting the app, understanding Live vs Demo, and getting ready for a smooth walkthrough."
      actions={
        <div className="flex items-center gap-2 rounded-full border border-white/8 bg-white/4 p-1">
          <Button variant={mode === "demo" ? "default" : "ghost"} size="sm" onClick={() => setMode("demo")}>Demo</Button>
          <Button variant={mode === "live" ? "default" : "ghost"} size="sm" onClick={() => setMode("live")}>Live</Button>
        </div>
      }
    >
      {!guide ? (
        <Card className="p-8 text-sm text-slate-400">Loading setup guide...</Card>
      ) : (
        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-cyan-100">{guide.headline}</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">How to use Markets Strategy Copilot</h2>
                <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-300">{guide.summary}</p>
              </div>
              <Button onClick={handleWarmup} disabled={warming} className="rounded-full">
                {warming ? "Warming demo..." : "Speed up demo"}
              </Button>
            </div>
            {warmup && (
              <div className="mt-4 rounded-[22px] border border-emerald-300/14 bg-emerald-300/8 p-4 text-sm text-slate-100">
                {warmup.message} Warmed {warmup.warmed?.length ?? 0} cache step(s) in {warmup.durationMs} ms.
              </div>
            )}
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {guide.checks.map((check: any) => (
              <Card key={check.label} className="p-5">
                <Badge className={check.status === "ready" ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : check.status === "attention" ? "border-amber-300/20 bg-amber-300/10 text-amber-100" : "border-rose-300/20 bg-rose-300/10 text-rose-100"}>
                  {check.status}
                </Badge>
                <h3 className="mt-3 text-lg font-semibold text-white">{check.label}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">{check.detail}</p>
              </Card>
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">First-run tutorial</p>
              <div className="mt-4 space-y-3">
                {guide.tutorial.map((step: any) => (
                  <div key={step.step} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                    <p className="text-sm font-medium text-white">{step.step}. {step.title}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{step.detail}</p>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Commands</p>
              <div className="mt-4 space-y-3">
                {guide.commands.map((command: any) => (
                  <div key={command.label} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                    <p className="text-sm font-medium text-white">{command.label}</p>
                    <code className="mt-2 block rounded-2xl border border-white/8 bg-slate-950/70 px-3 py-2 text-sm text-cyan-100">{command.command}</code>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <ProviderFailoverTimeline timeline={timeline} />
        </div>
      )}
    </AppFrame>
  );
}
