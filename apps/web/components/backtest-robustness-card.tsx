import { Card } from "@/components/ui/card";

export function BacktestRobustnessCard({ robustness }: { robustness?: any }) {
  if (!robustness) return null;
  return (
    <Card className="p-5">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Backtest robustness</p>
      <h2 className="mt-2 text-xl font-semibold text-white">{robustness.score}/100 robustness score</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <Metric label="Positive folds" value={`${(Number(robustness.positiveFoldRatio ?? 0) * 100).toFixed(0)}%`} />
        <Metric label="Fold count" value={String(robustness.foldCount ?? 0)} />
        <Metric label="+5 bps cost drag" value={`${(Number(robustness.costSensitivity?.estimatedCostDrag ?? 0) * 100).toFixed(2)}%`} />
      </div>
      <div className="mt-4 space-y-2">
        {(robustness.warnings ?? []).map((warning: string) => (
          <div key={warning} className="rounded-2xl border border-amber-300/14 bg-amber-300/7 p-3 text-sm leading-6 text-slate-300">
            {warning}
          </div>
        ))}
      </div>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/4 p-3">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
