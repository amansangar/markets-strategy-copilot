import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { DataQuality } from "@/lib/types";

export function DataQualityCard({ quality }: { quality?: DataQuality }) {
  if (!quality) return null;
  const tone =
    quality.score >= 85
      ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"
      : quality.score >= 65
        ? "border-amber-300/20 bg-amber-300/10 text-amber-100"
        : "border-rose-300/20 bg-rose-300/10 text-rose-100";
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Data quality score</p>
          <h2 className="mt-2 text-3xl font-semibold text-white">{quality.score}/100</h2>
          <p className="mt-2 text-sm text-slate-400">Provider, freshness, news, risk, and policy coverage.</p>
        </div>
        <Badge className={tone}>{quality.label}</Badge>
      </div>
      <div className="mt-5 space-y-3">
        {quality.factors.slice(0, 5).map((factor) => (
          <div key={factor.label} className="rounded-2xl border border-white/8 bg-white/4 p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-white">{factor.label}</p>
              <span className={factor.impact < 0 ? "text-amber-200" : "text-emerald-200"}>{factor.impact}</span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-400">{factor.detail}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
