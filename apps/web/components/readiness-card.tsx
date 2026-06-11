import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { Readiness } from "@/lib/types";

export function ReadinessCard({ readiness }: { readiness?: Readiness }) {
  if (!readiness) return null;
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">System health</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">{readiness.score}/100</h2>
          <p className="mt-2 text-sm text-slate-400">A quick check that data, alerts, exports, and safeguards are ready.</p>
        </div>
        <Badge className={readiness.status === "ready" ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : "border-amber-300/20 bg-amber-300/10 text-amber-100"}>
          {readiness.status === "ready" ? "Ready" : "Check"}
        </Badge>
      </div>
      <div className="mt-4 space-y-2">
        {readiness.checks.map((check) => (
          <div key={check.label} className="rounded-2xl border border-white/8 bg-white/4 p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-white">{check.label}</p>
              <span className="text-xs uppercase tracking-[0.18em] text-slate-500">{check.status === "ready" ? "Ready" : "Check"}</span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-400">{check.detail}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}
