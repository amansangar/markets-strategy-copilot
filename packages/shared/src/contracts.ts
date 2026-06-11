import { z } from "zod";

export const actionValues = [
  "STRONG_BUY",
  "BUY",
  "HOLD",
  "SELL",
  "STRONG_SELL",
  "NO_SIGNAL",
] as const;

export const regimeValues = [
  "TRENDING_BULL",
  "TRENDING_BEAR",
  "MEAN_REVERTING",
  "RANGE_BOUND",
  "RISK_OFF",
] as const;

export const modeValues = ["demo", "live"] as const;
export const serviceStatusValues = [
  "healthy",
  "configured",
  "degraded",
  "offline",
  "disabled",
  "missing",
  "failed",
  "manual-check-needed",
  "checking",
] as const;

export const signalActionSchema = z.enum(actionValues);
export const regimeSchema = z.enum(regimeValues);
export const appModeSchema = z.enum(modeValues);
export const serviceStatusSchema = z.enum(serviceStatusValues);

export const reasonSchema = z.object({
  code: z.string(),
  label: z.string(),
  weight: z.number(),
  detail: z.string(),
});

export const riskFlagSchema = z.object({
  code: z.string(),
  severity: z.enum(["low", "medium", "high"]),
  message: z.string(),
});

export const serviceHealthSchema = z.object({
  name: z.string(),
  status: serviceStatusSchema,
  latencyMs: z.number().nullable(),
  freshnessSeconds: z.number().nullable(),
  detail: z.string(),
});

export const providerStatusSchema = z.object({
  name: z.string(),
  label: z.string(),
  category: z.string(),
  status: serviceStatusSchema,
  mode: appModeSchema,
  keyPresent: z.boolean(),
  configuredKeys: z.number(),
  requiredKeys: z.number(),
  browserExposed: z.boolean(),
  freshnessSeconds: z.number().nullable().optional(),
  lastSync: z.string().nullable().optional(),
  capabilities: z.array(z.string()),
  detail: z.string(),
  licensing: z.string(),
});

export const macroSnapshotSchema = z.object({
  regime: z.string(),
  riskScore: z.number(),
  ratesTrend: z.string(),
  inflationPressure: z.string(),
  creditStress: z.string(),
  growthMomentum: z.string(),
  summary: z.string(),
  components: z.record(z.string(), z.unknown()),
  caveat: z.string().optional(),
});

export const signalDiffSchema = z.object({
  available: z.boolean(),
  headline: z.string(),
  changes: z.array(z.record(z.string(), z.unknown())),
});

export const candleSchema = z.object({
  time: z.string(),
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  volume: z.number(),
});

export const signalCardSchema = z.object({
  symbol: z.string(),
  action: signalActionSchema,
  confidence: z.number(),
  regime: regimeSchema,
  horizon: z.string(),
  currentPrice: z.number(),
  stopLoss: z.number().nullable(),
  takeProfitLow: z.number().nullable(),
  takeProfitHigh: z.number().nullable(),
  positionSizePct: z.number(),
  dataFreshnessSeconds: z.number(),
  reasonCodes: z.array(reasonSchema),
  riskFlags: z.array(riskFlagSchema),
  lastUpdated: z.string(),
});

export const watchlistRowSchema = z.object({
  symbol: z.string(),
  name: z.string(),
  lastPrice: z.number(),
  changePct: z.number(),
  signal: signalActionSchema,
  confidence: z.number(),
  regime: regimeSchema,
  sentiment: z.number(),
  volumeNote: z.string(),
  assetClass: z.string(),
});

export const dashboardSchema = z.object({
  mode: appModeSchema,
  trackedAssets: z.number(),
  alertCount: z.number(),
  strongestBuy: z.string(),
  strongestSell: z.string(),
  marketRegimeSummary: z.string(),
  connectionSummary: z.string(),
  health: z.array(serviceHealthSchema),
  providerBadges: z.array(z.object({ label: z.string(), status: z.string(), category: z.string(), freshnessSeconds: z.number().nullable().optional() })),
  macro: macroSnapshotSchema,
  portfolioSummary: z.record(z.string(), z.union([z.string(), z.number(), z.boolean()])),
  signalDiff: signalDiffSchema,
  watchlist: z.array(watchlistRowSchema),
  chart: z.object({
    symbol: z.string(),
    timeframe: z.string(),
    candles: z.array(candleSchema),
    overlays: z.record(z.string(), z.array(z.object({ time: z.string(), value: z.number().nullable() }))),
    oscillators: z.record(
      z.string(),
      z.array(z.object({ time: z.string(), value: z.number().nullable(), signal: z.number().nullable().optional() })),
    ),
  }),
  signal: signalCardSchema,
});

export type SignalAction = z.infer<typeof signalActionSchema>;
export type Regime = z.infer<typeof regimeSchema>;
export type AppMode = z.infer<typeof appModeSchema>;
export type ServiceStatus = z.infer<typeof serviceStatusSchema>;
export type ServiceHealth = z.infer<typeof serviceHealthSchema>;
export type ProviderStatus = z.infer<typeof providerStatusSchema>;
export type MacroSnapshot = z.infer<typeof macroSnapshotSchema>;
export type SignalDiff = z.infer<typeof signalDiffSchema>;
export type WatchlistRow = z.infer<typeof watchlistRowSchema>;
export type SignalCard = z.infer<typeof signalCardSchema>;
export type DashboardResponse = z.infer<typeof dashboardSchema>;
