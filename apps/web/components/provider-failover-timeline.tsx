import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

export function ProviderFailoverTimeline({ timeline }: { timeline: any }) {
  if (!timeline) {
    return <Card className="p-5 text-sm text-slate-400">Loading connection backup plan...</Card>;
  }

  return (
    <Card className="p-5">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-start">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Connection backup plan</p>
          <h2 className="mt-2 text-xl font-semibold text-white">
            {timeline.criticalFallbackLikely ? "A backup source may be needed" : "Primary sources are ready"}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{timeline.policy}</p>
        </div>
        <Badge className={timeline.criticalFallbackLikely ? "border-amber-300/20 bg-amber-300/10 text-amber-100" : "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"}>
          {timeline.mode}
        </Badge>
      </div>
      <div className="mt-5 space-y-3">
        {timeline.events?.map((event: any, index: number) => (
          <div key={`${event.title}-${index}`} className="grid gap-3 rounded-[24px] border border-white/8 bg-white/4 p-4 text-sm md:grid-cols-[140px_1fr]">
            <div>
              <Badge className={event.status === "healthy" || event.status === "active" ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : event.status === "configured" ? "border-cyan-300/20 bg-cyan-300/10 text-cyan-100" : "border-amber-300/20 bg-amber-300/10 text-amber-100"}>
                {event.status}
              </Badge>
              <p className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-500">{event.kind}</p>
            </div>
            <div>
              <p className="font-medium text-white">{event.title}</p>
              <p className="mt-2 leading-6 text-slate-400">{event.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
