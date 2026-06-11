import { Card } from "@/components/ui/card";
import type { SignalWaterfall } from "@/lib/types";

export function SignalWaterfallCard({ waterfall }: { waterfall?: SignalWaterfall }) {
  if (!waterfall) return null;
  const max = Math.max(...waterfall.items.map((item) => Math.abs(item.value)), 1);
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Signal waterfall</p>
          <h2 className="mt-2 text-xl font-semibold text-white">{waterfall.finalConfidence.toFixed(1)}% confidence</h2>
        </div>
        <div className="rounded-2xl border border-white/8 bg-white/4 px-3 py-2 text-xs uppercase tracking-[0.18em] text-slate-300">
          Explainable
        </div>
      </div>
      <div className="mt-5 space-y-3">
        {waterfall.items.slice(0, 10).map((item) => {
          const positive = item.value >= 0;
          return (
            <div key={`${item.label}-${item.kind}`} className="rounded-2xl border border-white/8 bg-white/4 p-3">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium text-white">{formatWaterfallLabel(item.label)}</span>
                <span className={positive ? "text-emerald-200" : "text-rose-200"}>{item.value > 0 ? "+" : ""}{item.value.toFixed(2)}</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
                <div
                  className={positive ? "h-full rounded-full bg-emerald-300" : "ml-auto h-full rounded-full bg-rose-300"}
                  style={{ width: `${Math.max(5, (Math.abs(item.value) / max) * 100)}%` }}
                />
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">{item.detail}</p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function formatWaterfallLabel(label: string) {
  const labels: Record<string, string> = {
    MACD_UP: "MACD improving",
    MACD_DOWN: "MACD weakening",
    VWAP_ABOVE: "Above VWAP",
    VWAP_BELOW: "Below VWAP",
    NEWS_CONTEXT: "News context",
    MACRO_REGIME: "Macro backdrop",
    THIN_PARTICIPATION: "Light volume",
    STALE_DATA: "Stale price data",
    "FILING_N-CSR": "Filing caution",
    FILING_10K: "Annual filing",
    FILING_10Q: "Quarterly filing",
    HIGH_VOLATILITY: "High volatility",
    LOW_LIQUIDITY: "Liquidity watch",
  };
  return labels[label] ?? label.replaceAll("_", " ").replaceAll("-", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}
