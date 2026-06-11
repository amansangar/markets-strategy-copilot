import Link from "next/link";

import { IconShield, IconSignal, IconTrendDown, IconTrendUp } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { formatConfidence, formatPercent, formatPrice } from "@/lib/format";
import type { DashboardResponse, WatchlistRow } from "@/lib/types";
import { cn } from "@/lib/utils";

type TopOpportunitiesProps = {
  rows: WatchlistRow[];
  signal: DashboardResponse["signal"];
};

const actionTone: Record<string, string> = {
  STRONG_BUY: "border-emerald-300/24 bg-emerald-300/12 text-emerald-100",
  BUY: "border-emerald-300/20 bg-emerald-300/10 text-emerald-100",
  HOLD: "border-amber-300/20 bg-amber-300/10 text-amber-100",
  SELL: "border-rose-300/20 bg-rose-300/10 text-rose-100",
  STRONG_SELL: "border-rose-300/24 bg-rose-300/12 text-rose-100",
  NO_SIGNAL: "border-slate-300/15 bg-slate-300/10 text-slate-100",
};

export function TopOpportunities({ rows, signal }: TopOpportunitiesProps) {
  const directional = rows
    .slice()
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 3);
  const ranked = directional.length
    ? directional
    : rows
        .slice()
        .sort((a, b) => b.confidence - a.confidence)
        .slice(0, 3);
  const riskLabel = signal.riskFlags.length ? `${signal.riskFlags.length} warning${signal.riskFlags.length === 1 ? "" : "s"}` : "No major warnings";

  return (
    <Card className="overflow-hidden p-4">
      <div className="grid gap-4 xl:grid-cols-[1fr_1.5fr]">
        <div className="rounded-[24px] border border-cyan-300/14 bg-cyan-300/7 p-4">
          <div className="flex items-center gap-2">
            <IconSignal className="h-4 w-4 text-cyan-100" />
            <p className="text-xs uppercase tracking-[0.22em] text-cyan-100/80">What to look at now</p>
          </div>
          <h2 className="mt-3 text-2xl font-semibold text-white">
            {signal.symbol}: {signal.action.replaceAll("_", " ")}
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Confidence {formatConfidence(signal.confidence)}. {riskLabel}. Review the chart, then check the reasons before acting.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href={`/asset/${signal.symbol}`}>
              <Button size="sm">Open research</Button>
            </Link>
            <Link href={`/assistant?symbol=${signal.symbol}`}>
              <Button size="sm" variant="secondary">Ask AI why</Button>
            </Link>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {ranked.map((row) => {
            const positive = row.changePct >= 0;
            return (
              <Link key={row.symbol} href={`/asset/${row.symbol}`} className="group rounded-[24px] border border-white/8 bg-white/4 p-4 transition hover:-translate-y-0.5 hover:border-cyan-300/24 hover:bg-white/6">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Opportunity</p>
                    <h3 className="mt-2 text-xl font-semibold text-white">{row.symbol}</h3>
                    <p className="mt-1 line-clamp-1 text-xs text-slate-500">{row.name}</p>
                  </div>
                  <Badge className={actionTone[row.signal] ?? actionTone.BUY}>{row.signal.replaceAll("_", " ")}</Badge>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                  <Metric label="Price" value={formatPrice(row.lastPrice)} />
                  <Metric label="Move" value={formatPercent(row.changePct)} positive={positive} />
                  <Metric label="Confidence" value={formatConfidence(row.confidence)} />
                  <Metric label="Mood" value={row.sentiment > 0.1 ? "Positive" : row.sentiment < -0.1 ? "Negative" : "Neutral"} />
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

function Metric({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-slate-950/50 p-3">
      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className={cn("mt-1 inline-flex items-center gap-1 text-sm font-semibold text-white", positive === true && "text-emerald-200", positive === false && "text-rose-200")}>
        {positive === true ? <IconTrendUp className="h-3 w-3" /> : positive === false ? <IconTrendDown className="h-3 w-3" /> : null}
        {label === "Mood" && <IconShield className="h-3 w-3 text-slate-400" />}
        {value}
      </p>
    </div>
  );
}
