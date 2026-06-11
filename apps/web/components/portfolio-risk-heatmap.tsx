import { Card } from "@/components/ui/card";

export function PortfolioRiskHeatmap({ heatmap }: { heatmap?: { cells?: Array<Record<string, any>> } }) {
  const cells = heatmap?.cells ?? [];
  if (!cells.length) return null;
  return (
    <Card className="p-5">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Portfolio risk heatmap</p>
      <h2 className="mt-2 text-xl font-semibold text-white">Exposure, P&L, and concentration</h2>
      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {cells.map((cell) => {
          const level = String(cell.riskLevel);
          const tone = level === "high" ? "border-rose-300/20 bg-rose-300/10" : level === "medium" ? "border-amber-300/20 bg-amber-300/10" : "border-emerald-300/20 bg-emerald-300/10";
          return (
            <div key={String(cell.symbol)} className={`rounded-[24px] border p-4 ${tone}`}>
              <div className="flex items-center justify-between gap-3">
                <p className="text-lg font-semibold text-white">{String(cell.symbol)}</p>
                <p className="text-xs uppercase tracking-[0.18em] text-slate-300">{level}</p>
              </div>
              <p className="mt-3 text-sm text-slate-300">Weight {(Number(cell.weight) * 100).toFixed(1)}%</p>
              <p className={Number(cell.pnlPct) >= 0 ? "mt-1 text-sm text-emerald-200" : "mt-1 text-sm text-rose-200"}>
                P&L {(Number(cell.pnlPct) * 100).toFixed(2)}%
              </p>
              <p className="mt-3 text-xs leading-5 text-slate-400">{String(cell.note)}</p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
