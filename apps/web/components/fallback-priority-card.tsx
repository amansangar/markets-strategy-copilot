import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { FallbackGroup } from "@/lib/types";

function formatProviderStatus(status: string) {
  return status
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/^\w/, (letter) => letter.toUpperCase());
}

export function FallbackPriorityCard({ groups }: { groups?: FallbackGroup[] }) {
  if (!groups?.length) return null;
  return (
    <Card className="p-5">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Backup sources</p>
      <h2 className="mt-2 text-xl font-semibold text-white">What the app uses if a feed slows down</h2>
      <div className="mt-5 space-y-4">
        {groups.map((group) => (
          <div key={group.category} className="rounded-[24px] border border-white/8 bg-white/4 p-4">
            <p className="text-sm font-semibold text-white">{group.category}</p>
            <p className="mt-2 text-sm leading-6 text-slate-400">{group.policy}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {group.providers.map((provider) => (
                <Badge key={`${group.category}-${provider.name}`} className={provider.status === "healthy" ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : provider.status === "configured" ? "border-cyan-300/20 bg-cyan-300/10 text-cyan-100" : provider.status === "degraded" ? "border-amber-300/20 bg-amber-300/10 text-amber-100" : "border-white/10 bg-white/5 text-slate-300"}>
                  {provider.role}: {provider.label} ({formatProviderStatus(provider.status)})
                </Badge>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
