import { IconGauge, IconSignal } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { DashboardResponse, MacroSnapshot, ProviderBadge } from "@/lib/types";

export function MacroStrip({
  macro,
  providerBadges,
  portfolioSummary,
}: {
  macro: MacroSnapshot;
  providerBadges: ProviderBadge[];
  portfolioSummary?: DashboardResponse["portfolioSummary"];
}) {
  return (
    <Card className="overflow-hidden p-4">
      <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr_0.8fr]">
        <div className="rounded-[24px] border border-cyan-300/12 bg-cyan-300/6 p-4">
          <div className="flex items-center gap-2">
            <IconGauge className="h-4 w-4 text-cyan-200" />
            <p className="text-xs uppercase tracking-[0.24em] text-cyan-100/80">Macro Regime</p>
          </div>
          <h2 className="mt-2 text-xl font-semibold text-white">{macro.regime.replaceAll("_", " ").toUpperCase()}</h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">{macro.summary}</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <MacroMetric label="Rates" value={macro.ratesTrend} />
          <MacroMetric label="Inflation" value={macro.inflationPressure} />
          <MacroMetric label="Credit" value={macro.creditStress} />
          <MacroMetric label="Growth" value={macro.growthMomentum} />
        </div>

        <div className="rounded-[24px] border border-white/8 bg-white/4 p-4">
          <div className="flex items-center gap-2">
            <IconSignal className="h-4 w-4 text-emerald-200" />
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Portfolio / Sources</p>
          </div>
          <p className="mt-2 text-lg font-semibold text-white">
            {Number(portfolioSummary?.openPositions ?? 0)} simulated paper positions
          </p>
          <p className="mt-1 text-sm text-slate-400">
            Local practice portfolio P&L {Number(portfolioSummary?.unrealizedPnl ?? 0).toFixed(2)}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {providerBadges.slice(0, 6).map((item) => (
              <Badge key={`${item.label}-${item.category}`} className={badgeTone(item.status)}>
                {item.label}: {item.status}
              </Badge>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

function MacroMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[20px] border border-white/8 bg-white/4 p-3">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-white">{value}</p>
    </div>
  );
}

function badgeTone(status: string) {
  if (status === "healthy") {
    return "border-emerald-300/20 bg-emerald-300/10 text-emerald-100";
  }
  if (status === "configured") {
    return "border-cyan-300/20 bg-cyan-300/10 text-cyan-100";
  }
  if (status === "degraded") {
    return "border-amber-300/20 bg-amber-300/10 text-amber-100";
  }
  if (status === "offline") {
    return "border-rose-300/20 bg-rose-300/10 text-rose-100";
  }
  return "border-white/10 bg-white/5 text-slate-300";
}
