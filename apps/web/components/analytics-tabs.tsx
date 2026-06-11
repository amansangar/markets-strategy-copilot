import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatDateTime, formatPercent } from "@/lib/format";
import type { DashboardResponse } from "@/lib/types";

export function AnalyticsTabs({
  dashboard,
}: {
  dashboard: DashboardResponse;
}) {
  return (
    <Card className="p-4">
      <Tabs defaultValue="news">
        <TabsList>
          <TabsTrigger value="news">News & Events</TabsTrigger>
          <TabsTrigger value="indicators">Indicators</TabsTrigger>
          <TabsTrigger value="backtest">Backtest</TabsTrigger>
          <TabsTrigger value="trades">Trades</TabsTrigger>
          <TabsTrigger value="audit">Audit</TabsTrigger>
          <TabsTrigger value="risk">Risk</TabsTrigger>
        </TabsList>

        <TabsContent value="news">
          <div className="space-y-3">
            <div className="rounded-[24px] border border-cyan-300/12 bg-cyan-300/7 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-cyan-100/80">Market news tape</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    Headlines are linked to the selected symbol, deduplicated, sentiment-scored, and refreshed with provider-safe caching in live mode.
                  </p>
                </div>
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
                  {dashboard.news.length} items
                </span>
              </div>
            </div>
            <div className="grid gap-3 lg:grid-cols-2">
              {dashboard.news.length ? dashboard.news.map((item) => (
                <div key={`${item.url}-${item.publishedAt}`} className="rounded-[24px] border border-white/8 bg-white/4 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold leading-6 text-white">{item.title}</p>
                      <p className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">{item.source}</p>
                    </div>
                    <span className={`shrink-0 rounded-full border px-3 py-1 text-xs font-semibold ${
                      Number(item.sentiment) > 0.15
                        ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"
                        : Number(item.sentiment) < -0.15
                          ? "border-rose-300/20 bg-rose-300/10 text-rose-100"
                          : "border-white/10 bg-white/5 text-slate-300"
                    }`}>
                      {Number(item.sentiment) > 0.15 ? "Positive" : Number(item.sentiment) < -0.15 ? "Negative" : "Neutral"}
                    </span>
                  </div>
                  <div className="mt-4 grid gap-2 text-xs text-slate-400 sm:grid-cols-3">
                    <span>Sentiment {Number(item.sentiment).toFixed(2)}</span>
                    <span>Relevance {Number(item.relevance).toFixed(2)}</span>
                    <span>{formatDateTime(item.publishedAt)}</span>
                  </div>
                  {item.url ? (
                    <a href={item.url} target="_blank" rel="noreferrer" className="mt-4 inline-flex rounded-full border border-white/10 px-3 py-1 text-xs font-semibold text-cyan-100 hover:border-cyan-300/30">
                      Open source
                    </a>
                  ) : null}
                </div>
              )) : (
                <div className="rounded-[24px] border border-white/8 bg-white/4 p-5 text-sm leading-6 text-slate-300">
                  No linked headlines are available for this symbol yet. The signal remains technical-only until news providers return relevant articles.
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="indicators">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {Object.entries(dashboard.signal.indicatorSnapshot).map(([key, value]) => (
              <div key={key} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{key}</p>
                <p className="mt-3 text-lg font-semibold text-white">{String(value)}</p>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="backtest">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {Object.entries(dashboard.backtestSummary).map(([key, value]) => (
              <div key={key} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{key}</p>
                <p className="mt-3 text-lg font-semibold text-white">{typeof value === "number" ? formatPercent(value) : String(value)}</p>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="trades">
          <div className="rounded-[24px] border border-white/8 bg-white/4 p-5 text-sm leading-7 text-slate-300">
            Backtest trade-by-trade detail is available in the Strategy Tester page, where you can rerun presets with fees, spread, slippage, and ablation controls.
          </div>
        </TabsContent>

        <TabsContent value="audit">
          <div className="space-y-3">
            {dashboard.audit.map((item) => (
              <div key={item.createdAt} className="rounded-[24px] border border-white/8 bg-white/4 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-medium text-white">
                    {item.action} at {(item.confidence * 100).toFixed(0)}% confidence
                  </p>
                  <span className="text-xs text-slate-500">{formatDateTime(item.createdAt)}</span>
                </div>
                <p className="mt-2 text-sm text-slate-400">
                  Policy pass: {item.policyPass ? "yes" : "no"} • {item.reasonCodes.map((reason: { code: string }) => reason.code).join(", ")}
                </p>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="risk">
          <div className="space-y-3">
            {dashboard.signal.riskFlags.length ? (
              dashboard.signal.riskFlags.map((flag) => (
                <div key={flag.code} className="rounded-[24px] border border-amber-300/14 bg-amber-300/8 p-4">
                  <p className="text-sm font-medium text-white">{flag.code}</p>
                  <p className="mt-2 text-sm text-slate-300">{flag.message}</p>
                </div>
              ))
            ) : (
              <div className="rounded-[24px] border border-emerald-300/14 bg-emerald-300/8 p-4 text-sm text-slate-200">
                No current risk flags. Data freshness, spread, and policy checks are all passing for the active snapshot.
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </Card>
  );
}
