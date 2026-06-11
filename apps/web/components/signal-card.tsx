import { IconShield, IconSignal, IconWarning } from "@/components/icons";
import { DataQualityCard } from "@/components/data-quality-card";
import { SignalWaterfallCard } from "@/components/signal-waterfall-card";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatConfidence, formatDateTime, formatPrice } from "@/lib/format";
import type { DashboardResponse } from "@/lib/types";

type SignalCardProps = {
  signal: DashboardResponse["signal"];
  compact?: boolean;
};

export function SignalCard({ signal, compact = false }: SignalCardProps) {
  const actionTone = actionToneClasses(signal.action);
  const reasonLimit = compact ? 3 : 5;
  const riskLimit = compact ? 2 : signal.riskFlags.length;
  const regimeLabel = formatRegimeLabel(signal.regime);
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Current view</p>
          <h2 className="mt-2 text-2xl font-semibold text-white">{signal.action.replaceAll("_", " ")}</h2>
          <p className="mt-2 text-sm text-slate-400">Confidence {formatConfidence(signal.confidence)}</p>
        </div>
        <div className={`rounded-2xl border px-3 py-2 text-xs ${actionTone}`}>
          <span className="block text-[10px] uppercase tracking-[0.2em] opacity-70">Market state</span>
          <span className="mt-1 block font-semibold">{regimeLabel}</span>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3">
        <Metric label="Current price" value={formatPrice(signal.currentPrice)} />
        <Metric label="Position size" value={`${(signal.positionSizePct * 100).toFixed(1)}%`} />
        <Metric label="Stop / invalidation" value={signal.stopLoss ? formatPrice(signal.stopLoss) : "n/a"} />
        <Metric label="Target band" value={signal.takeProfitLow ? `${formatPrice(signal.takeProfitLow)} -> ${formatPrice(signal.takeProfitHigh ?? signal.takeProfitLow)}` : "n/a"} />
      </div>

      {compact ? (
        <div className="mt-5 grid gap-3 sm:grid-cols-2 2xl:grid-cols-1">
          <MiniEvidence
            label="Data quality"
            value={signal.dataQuality.label.replaceAll("_", " ")}
            detail={`${Math.round(signal.dataQuality.score)}/100 usable data score`}
          />
          <MiniEvidence
            label="Signal waterfall"
            value={`${formatConfidence(signal.confidence)} confidence`}
            detail={`${signal.waterfall.items.length} evidence checks combined`}
          />
        </div>
      ) : (
        <div className="mt-5 space-y-4">
          <DataQualityCard quality={signal.dataQuality} />
          <SignalWaterfallCard waterfall={signal.waterfall} />
        </div>
      )}

      <section className="mt-5">
        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Why this signal?</p>
        <div className="mt-3 space-y-3">
          {signal.reasonCodes.slice(0, reasonLimit).map((reason) => {
            const counterSignal = isCounterSignal(signal.action, reason.weight);
            return (
            <div key={reason.code} className="rounded-2xl border border-white/8 bg-white/4 p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-white">
                  {counterSignal ? `Risk check: ${reason.label}` : reason.label}
                </p>
                <Badge>{counterSignal ? "Counter-signal" : formatCodeLabel(reason.code)}</Badge>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-400">{reason.detail}</p>
            </div>
            );
          })}
        </div>
      </section>

      <section className="mt-5">
        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Safety checks</p>
        <div className="mt-3 space-y-3">
          {signal.riskFlags.length ? (
            signal.riskFlags.slice(0, riskLimit).map((flag) => (
              <div key={flag.code} className="flex items-start gap-3 rounded-2xl border border-amber-300/14 bg-amber-300/7 p-3">
                <IconWarning className="mt-0.5 h-4 w-4 text-amber-200" />
                <div>
                  <p className="text-sm font-medium text-white">{formatCodeLabel(flag.code)}</p>
                  <p className="mt-1 text-sm text-slate-300">{flag.message}</p>
                </div>
              </div>
            ))
          ) : (
            <div className="flex items-start gap-3 rounded-2xl border border-emerald-300/14 bg-emerald-300/7 p-3">
              <IconShield className="mt-0.5 h-4 w-4 text-emerald-200" />
              <div>
                <p className="text-sm font-medium text-white">No active blockers</p>
                <p className="mt-1 text-sm text-slate-300">No major data, cost, or risk warning is active right now.</p>
              </div>
            </div>
          )}
        </div>
      </section>

      <div className="mt-5 flex items-center justify-between rounded-2xl border border-white/8 bg-white/3 px-4 py-3 text-sm text-slate-400">
        <span className="inline-flex items-center gap-2">
          <IconSignal className="h-4 w-4 text-cyan-200" />
          Last updated
        </span>
        <span>{formatDateTime(signal.lastUpdated)}</span>
      </div>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/4 p-3">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-white">{value}</p>
    </div>
  );
}

function MiniEvidence({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/4 p-3">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold capitalize text-white">{value}</p>
      <p className="mt-1 text-xs leading-5 text-slate-400">{detail}</p>
    </div>
  );
}

function formatRegimeLabel(regime: string) {
  const labels: Record<string, string> = {
    TRENDING_BULL: "Bullish trend",
    TRENDING_BEAR: "Bearish trend",
    MEAN_REVERTING: "Mean reversion",
    RANGE_BOUND: "Range bound",
    RISK_ON: "Risk-on",
    RISK_OFF: "Risk-off",
  };
  return labels[regime] ?? toTitleCase(regime);
}

function formatCodeLabel(code: string) {
  const labels: Record<string, string> = {
    MACD_UP: "MACD improving",
    MACD_DOWN: "MACD weakening",
    VWAP_ABOVE: "Above VWAP",
    VWAP_BELOW: "Below VWAP",
    NEWS_CONTEXT: "News context",
    MACRO_REGIME: "Macro backdrop",
    DAILY_TREND_BULL: "Daily uptrend",
    DAILY_TREND_BEAR: "Daily downtrend",
    DMI_BULL: "DMI buyers",
    DMI_BEAR: "DMI sellers",
    SUPERTREND_BULL: "Supertrend bullish",
    SUPERTREND_BEAR: "Supertrend bearish",
    BOLLINGER_REVERSION_BUY: "Lower-band bounce",
    BOLLINGER_REVERSION_SELL: "Upper-band fade",
    MIXED_EVIDENCE_HOLD: "Mixed evidence",
    STALE_FEED_HOLD: "Wait for fresh data",
    STALE_FEED_NO_SIGNAL: "No fresh signal",
    POLICY_HOLD: "Policy says wait",
    DATA_QUALITY_NO_SIGNAL: "No data signal",
    STALE_DATA: "Stale price data",
    "FILING_N-CSR": "Filing caution",
    FILING_10K: "Annual filing",
    FILING_10Q: "Quarterly filing",
    THIN_PARTICIPATION: "Light volume",
    HIGH_VOLATILITY: "High volatility",
    LOW_LIQUIDITY: "Liquidity watch",
  };
  return labels[code] ?? toTitleCase(code);
}

function actionToneClasses(action: string) {
  if (action.includes("BUY")) return "border-emerald-300/20 bg-emerald-300/10 text-emerald-100";
  if (action.includes("SELL")) return "border-rose-300/20 bg-rose-300/10 text-rose-100";
  if (action === "HOLD") return "border-amber-300/20 bg-amber-300/10 text-amber-100";
  return "border-slate-300/15 bg-slate-300/10 text-slate-100";
}

function isCounterSignal(action: string, weight: number) {
  if (action.includes("BUY")) return weight < 0;
  if (action.includes("SELL")) return weight > 0;
  return false;
}

function toTitleCase(value: string) {
  return value
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
