import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function AssistantLoading() {
  return (
    <div className="min-h-screen bg-[#07101d] p-4 text-white md:p-8">
      <div className="mx-auto max-w-6xl space-y-4">
        <div>
          <p className="text-xs uppercase tracking-[0.26em] text-cyan-200/80">AI Copilot</p>
          <h1 className="mt-2 text-3xl font-semibold">Loading market assistant</h1>
          <p className="mt-2 text-sm text-slate-400">Preparing the question panel first so the page feels instant.</p>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          <Card className="space-y-4 p-5">
            <Skeleton className="h-9 w-48" />
            <div className="grid gap-3 sm:grid-cols-2">
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
              <Skeleton className="h-28" />
            </div>
            <Skeleton className="h-32" />
          </Card>
          <Card className="space-y-4 p-5">
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-56" />
            <Skeleton className="h-20" />
          </Card>
        </div>
      </div>
    </div>
  );
}
