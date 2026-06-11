import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";

export function SummaryTile({
  label,
  value,
  hint,
  accent,
  icon,
  compact = false,
}: {
  label: string;
  value: string;
  hint: string;
  accent: string;
  icon: ReactNode;
  compact?: boolean;
}) {
  return (
    <Card className="relative overflow-hidden p-4">
      <div className="absolute inset-x-0 top-0 h-1" style={{ background: accent }} />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
          <h3 className={compact ? "mt-2 break-words text-lg font-semibold tracking-tight text-white" : "mt-3 break-words text-2xl font-semibold tracking-tight text-white"}>{value}</h3>
          <p className={compact ? "mt-1 text-xs leading-5 text-slate-400" : "mt-2 text-sm text-slate-400"}>{hint}</p>
        </div>
        <div className={compact ? "hidden rounded-2xl border border-white/10 bg-white/5 p-2 text-cyan-100 2xl:block" : "rounded-2xl border border-white/10 bg-white/5 p-3 text-cyan-100"}>{icon}</div>
      </div>
    </Card>
  );
}
