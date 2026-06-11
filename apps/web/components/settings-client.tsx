"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { FallbackPriorityCard } from "@/components/fallback-priority-card";
import { ProviderFailoverTimeline } from "@/components/provider-failover-timeline";
import { ReadinessCard } from "@/components/readiness-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchProviderBudget, fetchProviderChecks, fetchProviderFailoverTimeline, fetchProviderStatus, fetchReadiness, fetchSystemStatus } from "@/lib/api";
import type { ProviderStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const advancedTools = [
  { href: "/demo", label: "Demo Guide", detail: "Guided route sequence and product walkthrough." },
  { href: "/setup", label: "Setup Guide", detail: "First-run onboarding and local setup steps." },
  { href: "/pro-terminal", label: "Research Toolkit", detail: "Power-user overview of the extended research toolkit." },
  { href: "/quality", label: "Signal Quality", detail: "Distribution, confidence, and audit quality checks." },
  { href: "/governance", label: "Governance", detail: "Signal comparison, ablation, and model-boundary evidence." },
  { href: "/coverage", label: "Data Coverage", detail: "Bars, news, filings, and audit coverage map." },
  { href: "/universe", label: "Market Universe", detail: "Tracked asset universe and coverage notes." },
  { href: "/events", label: "Events Calendar", detail: "Macro, earnings, filings, and news event context." },
  { href: "/opportunities", label: "Ranked Opportunities", detail: "Power-user ranking and custom scanner columns." },
  { href: "/strategy-builder", label: "Strategy Builder", detail: "Rule lab for custom deterministic strategy logic." },
  { href: "/strategy-matrix", label: "Strategy Matrix", detail: "Preset comparison and robustness summary." },
  { href: "/replay-lab", label: "Replay Lab", detail: "Historical replay with no-lookahead wording." },
  { href: "/tear-sheet", label: "Tear Sheet", detail: "Fundamental and macro context page." },
  { href: "/alert-builder", label: "Advanced Alert Builder", detail: "Multi-factor alert templates and cooldown rules." },
];

export function SettingsClient() {
  const [demoStatus, setDemoStatus] = useState<any>(null);
  const [liveStatus, setLiveStatus] = useState<any>(null);
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [observability, setObservability] = useState<any>(null);
  const [providerChecks, setProviderChecks] = useState<any>(null);
  const [fallbackPlan, setFallbackPlan] = useState<any[]>([]);
  const [failoverTimeline, setFailoverTimeline] = useState<any>(null);
  const [providerBudget, setProviderBudget] = useState<any>(null);
  const [readiness, setReadiness] = useState<any>(null);
  const [checkingProviders, setCheckingProviders] = useState(false);
  const [showDisabledProviders, setShowDisabledProviders] = useState(false);

  const visibleProviders = showDisabledProviders
    ? providers
    : providers.filter((provider) => !(provider.status === "disabled" && provider.configuredKeys === 0));
  const hiddenDisabledProviderCount = providers.length - visibleProviders.length;
  const openAiProvider = providers.find((provider) => provider.name === "openai");
  const liveDataProviders = providers.filter((provider) => ["market_data", "free_tier_enrichment"].includes(provider.category));
  const configuredProviders = providers.filter((provider) => isReadyStatus(provider.status)).length;
  const needsAttention = providers.filter((provider) => ["degraded", "offline", "failed", "missing"].includes(provider.status)).length;

  useEffect(() => {
    fetchSystemStatus("demo").then(setDemoStatus);
    fetchSystemStatus("live").then(setLiveStatus);
    fetchProviderStatus("live").then((payload) => {
      setProviders(payload.providers);
      setObservability(payload.observability);
      setFallbackPlan(payload.fallbackPlan ?? []);
    });
    fetchProviderFailoverTimeline("live").then(setFailoverTimeline);
    fetchProviderBudget().then(setProviderBudget);
    fetchReadiness("demo").then(setReadiness);
  }, []);

  function runProviderChecks() {
    setCheckingProviders(true);
    fetchProviderChecks()
      .then(setProviderChecks)
      .finally(() => setCheckingProviders(false));
  }

  return (
    <AppFrame
      eyebrow="App Controls"
      title="Settings"
      subtitle="Connect data sources, check live readiness, and keep optional services tidy without exposing any API key values."
    >
      <div className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-4">
          <HumanStatusCard
            title="Live data"
            value={`${liveDataProviders.filter((provider) => isReadyStatus(provider.status)).length}/${Math.max(liveDataProviders.length, 1)} configured`}
            detail="Configured means the app can try the source; Healthy means a live check succeeded."
            tone={liveDataProviders.some((provider) => isReadyStatus(provider.status)) ? "good" : "warn"}
          />
          <HumanStatusCard
            title="AI Copilot"
            value={openAiProvider ? friendlyStatus(openAiProvider.status) : "Checking"}
            detail={openAiProvider?.detail ?? "OpenAI status will appear here once the backend responds."}
            tone={openAiProvider && isReadyStatus(openAiProvider.status) ? "good" : "warn"}
          />
          <HumanStatusCard
            title="Connections"
            value={`${configuredProviders} configured`}
            detail={needsAttention ? `${needsAttention} item(s) need attention.` : "No required provider is currently blocking the app."}
            tone={needsAttention ? "warn" : "good"}
          />
          <HumanStatusCard
            title="Privacy"
            value={observability?.privacy?.telemetryToggleDefault ? "Telemetry on" : "Private by default"}
            detail="Secrets stay server-side; browser-facing keys are clearly labelled."
            tone="neutral"
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
          <ReadinessCard readiness={readiness} />
          <FallbackPriorityCard groups={fallbackPlan} />
        </div>

        <ProviderFailoverTimeline timeline={failoverTimeline} />

        <Card className="p-5">
          <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">API usage budget</p>
              <h2 className="mt-2 text-xl font-semibold text-white">Refreshes are throttled and cached</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                Live mode only refreshes selected/visible work. Budget windows protect free APIs from repeated calls while showing cached data when needed.
              </p>
            </div>
            <Badge className="border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Free-tier safe</Badge>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(providerBudget?.budgets?.length ? providerBudget.budgets : [
              { provider: "newsapi", scope: "symbol news", lastStatus: "cached", nextAllowedAt: "After first live request", notes: "Symbol news is limited to one request per symbol every 30 minutes." },
              { provider: "polygon", scope: "selected symbol", lastStatus: "throttled", nextAllowedAt: "Every safe refresh window", notes: "REST refreshes are limited and reused by the local backend." },
              { provider: "openai", scope: "manual explanations", lastStatus: "on demand", nextAllowedAt: "User action only", notes: "AI calls are never run on every price update." },
            ]).slice(0, 6).map((budget: any) => (
              <div key={`${budget.provider}-${budget.scope}`} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{humaniseKey(String(budget.provider))}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">{humaniseKey(String(budget.scope))}</p>
                  </div>
                  <Badge className={budget.lastStatus === "failed" ? statusClasses("degraded") : "border-white/10 bg-white/5 text-slate-300"}>{humaniseKey(String(budget.lastStatus ?? "cached"))}</Badge>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-400">{budget.notes ?? "Cached unless the next safe refresh window is available."}</p>
                <p className="mt-3 text-xs text-slate-500">Next allowed: {formatBudgetTime(budget.nextAllowedAt)}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Connection check</p>
              <h2 className="mt-2 text-xl font-semibold text-white">Check live connections</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                Runs one small read-only check for each configured service. It only shows whether each service is healthy, degraded, missing, or disabled.
              </p>
            </div>
            <Button onClick={runProviderChecks} disabled={checkingProviders} className="rounded-full">
              {checkingProviders ? "Checking..." : "Check connections"}
            </Button>
          </div>

          {providerChecks && (
            <div className="mt-5 space-y-3">
              <div className="flex flex-wrap gap-2">
                {Object.entries(providerChecks.summary ?? {}).map(([status, count]) => (
                  <Badge key={status} className={status === "healthy" ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : status === "degraded" ? "border-amber-300/20 bg-amber-300/10 text-amber-100" : "border-white/10 bg-white/5 text-slate-300"}>
                    {status}: {String(count)}
                  </Badge>
                ))}
              </div>
              <div className="overflow-hidden rounded-[24px] border border-white/8">
                {providerChecks.checks.map((check: any) => (
                  <div key={check.name} className="grid gap-3 border-b border-white/8 bg-white/3 p-4 text-sm last:border-b-0 md:grid-cols-[150px_130px_1fr_120px]">
                    <div>
                      <p className="font-medium text-white">{check.name}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">{check.configured ? "configured" : "not configured"}</p>
                    </div>
                    <Badge className={statusClasses(check.status)}>
                      {friendlyStatus(check.status)}
                    </Badge>
                    <p className="text-slate-400">{check.note}</p>
                    <p className="text-xs text-slate-500">{check.latencyMs !== null && check.latencyMs !== undefined ? `${check.latencyMs} ms` : "manual"}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card className="p-5">
          <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Provider configuration</p>
              <p className="mt-2 text-sm text-slate-400">
                Your active data, AI, news, alerts, auth, and monitoring setup. Optional services with no keys are hidden unless you want to inspect them.
              </p>
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setShowDisabledProviders((value) => !value)}
              disabled={hiddenDisabledProviderCount === 0 && !showDisabledProviders}
            >
              {showDisabledProviders ? "Hide disabled optional APIs" : `Show disabled optional APIs${hiddenDisabledProviderCount ? ` (${hiddenDisabledProviderCount})` : ""}`}
            </Button>
          </div>
          <div className="mt-4 overflow-hidden rounded-[24px] border border-white/8">
            {visibleProviders.map((provider) => (
              <div key={provider.name} className="grid gap-3 border-b border-white/8 bg-white/3 p-4 text-sm last:border-b-0 md:grid-cols-[170px_120px_1fr_160px]">
                <div>
                  <p className="font-medium text-white">{provider.label}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">{categoryLabel(provider.category)}</p>
                </div>
                <Badge className={statusClasses(provider.status)}>
                  {friendlyStatus(provider.status)}
                </Badge>
                <p className="text-slate-400">{provider.detail}</p>
                <p className="text-xs text-slate-500">
                  {connectionLabel(provider)}
                  {provider.browserExposed ? " • browser-safe split" : " • private server-side"}
                </p>
              </div>
            ))}
          </div>
        </Card>

        {observability && (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-4">
            <StatusCard title="Local diagnostics" value={observability.localLogs?.enabled ? "Available" : "Off"} detail={observability.localLogs?.detail ?? "Local logs and automated test output remain the diagnostics path."} />
            <StatusCard title="Privacy" value={observability.privacy.telemetryToggleDefault ? "Telemetry on" : "Telemetry off by default"} detail={observability.privacy.browserSecretsRule} />
          </div>
        )}

        <Card className="p-5">
          <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Advanced tools</p>
              <h2 className="mt-2 text-xl font-semibold text-white">Extra screens kept out of the main workflow</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                These pages are useful for deeper analysis and power-user workflows, but they are kept out of the main navigation so the app stays easy to use day to day.
              </p>
            </div>
            <Badge className="border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Available on demand</Badge>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {advancedTools.map((tool) => (
              <Link
                key={tool.href}
                href={tool.href}
                className="rounded-[22px] border border-white/8 bg-white/4 p-4 transition hover:border-cyan-300/24 hover:bg-cyan-300/8"
              >
                <p className="text-sm font-semibold text-white">{tool.label}</p>
                <p className="mt-2 text-xs leading-5 text-slate-400">{tool.detail}</p>
              </Link>
            ))}
          </div>
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
        {[demoStatus, liveStatus].filter(Boolean).map((status: any) => (
          <Card key={status.mode} className="p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{status.mode} mode</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">
              {status.technicalOnlyMode ? "Limited enrichment" : "Ready for research"}
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-400">{status.message}</p>
            <div className="mt-5 space-y-3">
              {status.health.map((item: any) => (
                <div key={item.name} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-white">{item.name}</p>
                    <span className="text-xs uppercase tracking-[0.22em] text-slate-400">{item.status}</span>
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{item.detail}</p>
                </div>
              ))}
            </div>
          </Card>
        ))}
        </div>
      </div>
    </AppFrame>
  );
}

function StatusCard({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <Card className="p-5">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{title}</p>
      <h2 className="mt-2 text-xl font-semibold text-white">{value}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-400">{detail}</p>
    </Card>
  );
}

function HumanStatusCard({ title, value, detail, tone }: { title: string; value: string; detail: string; tone: "good" | "warn" | "neutral" }) {
  return (
    <Card className="p-5">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{title}</p>
      <h2 className={cn("mt-2 text-xl font-semibold", tone === "good" ? "text-emerald-100" : tone === "warn" ? "text-amber-100" : "text-white")}>{value}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-400">{detail}</p>
    </Card>
  );
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

function formatBudgetTime(value: unknown) {
  if (!value) return "After first live request";
  if (typeof value !== "string") return String(value);
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return value;
  return new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" }).format(parsed);
}

function friendlyStatus(status: string) {
  const labels: Record<string, string> = {
    healthy: "Verified healthy",
    configured: "Configured",
    degraded: "Needs attention",
    offline: "Offline",
    disabled: "Disabled",
    missing: "Missing",
    failed: "Failed",
    checking: "Checking",
    untested: "Manual check",
    "manual-check-needed": "Manual check",
  };
  return labels[status] ?? status;
}

function statusClasses(status: string) {
  if (status === "healthy") return "border-emerald-300/20 bg-emerald-300/10 text-emerald-100";
  if (status === "configured") return "border-cyan-300/20 bg-cyan-300/10 text-cyan-100";
  if (status === "degraded") return "border-amber-300/20 bg-amber-300/10 text-amber-100";
  if (status === "offline" || status === "missing" || status === "failed") return "border-rose-300/20 bg-rose-300/10 text-rose-100";
  return "border-white/10 bg-white/5 text-slate-300";
}

function categoryLabel(category: string) {
  const labels: Record<string, string> = {
    market_data: "Live prices",
    news: "News",
    ai_enrichment: "AI assistant",
    brokerage_paper: "Paper portfolio",
    macro: "Macro",
    filings: "Filings",
    optional_enrichment: "Extra research",
    free_tier_enrichment: "Free fallback",
    auth: "Sign-in",
    observability: "Error monitoring",
    email: "Email alerts",
    analytics: "Analytics",
  };
  return labels[category] ?? category.replaceAll("_", " ");
}

function connectionLabel(provider: ProviderStatus) {
  if (provider.status === "healthy") return "Verified by live check";
  if (provider.status === "configured") return "Configured, not checked this session";
  if (provider.status === "degraded") return `Partly configured (${provider.configuredKeys}/${provider.requiredKeys})`;
  if (provider.status === "disabled" && provider.configuredKeys === 0) return "Optional, not configured";
  if (provider.status === "disabled") return "Disabled";
  return `Needs setup (${provider.configuredKeys}/${provider.requiredKeys})`;
}

function isReadyStatus(status: string) {
  return status === "healthy" || status === "configured";
}
