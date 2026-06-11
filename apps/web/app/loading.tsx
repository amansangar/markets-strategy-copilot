import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="min-h-screen px-4 py-4 md:px-6 md:py-6">
      <div className="mx-auto grid max-w-[1600px] gap-4 lg:grid-cols-[248px_minmax(0,1fr)]">
        <Skeleton className="hidden min-h-[calc(100vh_-_2rem)] lg:block" />
        <div className="space-y-4 rounded-[32px] border border-white/8 bg-slate-950/70 p-4 md:p-5">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-3">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-9 w-72" />
              <Skeleton className="h-4 w-96 max-w-full" />
            </div>
            <Skeleton className="h-10 w-28 rounded-full" />
          </div>
          <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
            <Skeleton className="h-[680px]" />
            <Skeleton className="h-[680px]" />
          </div>
        </div>
      </div>
    </div>
  );
}
