import { IconSignal } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { SignalDiff } from "@/lib/types";

export function SignalDiffPanel({ diff }: { diff: SignalDiff }) {
  return (
    <Card className="self-start p-5">
      <div className="flex items-center gap-2">
        <IconSignal className="h-4 w-4 text-cyan-200" />
        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Why Did The Signal Change?</p>
      </div>
      <h2 className="mt-2 text-lg font-semibold text-white">{diff.headline}</h2>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {diff.changes.slice(0, 4).map((change, index) => (
          <div key={`${String(change.kind)}-${index}`} className="rounded-[20px] border border-white/8 bg-white/4 p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-white">{String(change.label ?? change.kind)}</p>
              <Badge>{String(change.kind ?? "change")}</Badge>
            </div>
            <p className="mt-2 text-sm text-slate-400">
              {formatChange(change)}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function formatChange(change: Record<string, unknown>) {
  if ("delta" in change) {
    return `Before ${String(change.before)} -> after ${String(change.after)} (delta ${String(change.delta)})`;
  }
  if ("before" in change || "after" in change) {
    return `Before ${String(change.before)} -> after ${String(change.after)}`;
  }
  if ("detail" in change) {
    return String(change.detail);
  }
  if ("added" in change || "removed" in change) {
    return `Added ${String(change.added)}; removed ${String(change.removed)}`;
  }
  return "No material detail available for this change.";
}
