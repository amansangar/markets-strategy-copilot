export type SignalAction = "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL" | "NO_SIGNAL";
export type Regime = "TRENDING_BULL" | "TRENDING_BEAR" | "MEAN_REVERTING" | "RANGE_BOUND" | "RISK_OFF";

export type WatchlistRow = {
  symbol: string;
  name: string;
  lastPrice: number;
  changePct: number;
  signal: SignalAction;
  confidence: number;
  regime: Regime;
  sentiment: number;
  volumeNote: string;
  assetClass: string;
};

export type ReasonCode = {
  code: string;
  label: string;
  weight: number;
  detail: string;
};

export type RiskFlag = {
  code: string;
  severity: "low" | "medium" | "high";
  message: string;
};

export type DataQuality = {
  score: number;
  label: string;
  generatedAt: string;
  factors: Array<{ label: string; status: string; impact: number; detail: string }>;
};

export type SignalWaterfall = {
  baseline: number;
  finalConfidence: number;
  items: Array<{ label: string; value: number; kind: string; detail: string }>;
};

export type Readiness = {
  score: number;
  status: string;
  checks: Array<{ label: string; status: string; detail: string }>;
  generatedAt: string;
};

export type FallbackGroup = {
  category: string;
  policy: string;
  providers: Array<{ name: string; label: string; role: string; status: string; configured: boolean; detail: string }>;
};

export type ChartPayload = {
  symbol: string;
  timeframe: string;
  candles: Array<{ time: string; open: number; high: number; low: number; close: number; volume: number }>;
  overlays: Record<string, Array<{ time: string; value: number | null }>>;
  oscillators: Record<string, Array<{ time: string; value: number | null; signal?: number | null }>>;
  markers: Array<{ time: string; position: string; color: string; shape: string; text: string }>;
  attribution: string;
  attributionUrl: string;
  history?: ChartPayload | null;
};

export type DashboardResponse = {
  mode: "demo" | "live";
  trackedAssets: number;
  alertCount: number;
  strongestBuy: string;
  strongestSell: string;
  marketRegimeSummary: string;
  connectionSummary: string;
  health: Array<{ name: string; status: string; latencyMs?: number | null; freshnessSeconds?: number | null; detail: string }>;
  watchlist: WatchlistRow[];
  chart: ChartPayload;
  signal: {
    symbol: string;
    action: SignalAction;
    confidence: number;
    regime: Regime;
    horizon: string;
    currentPrice: number;
    stopLoss: number | null;
    takeProfitLow: number | null;
    takeProfitHigh: number | null;
    positionSizePct: number;
    dataFreshnessSeconds: number;
    reasonCodes: ReasonCode[];
    riskFlags: RiskFlag[];
    policyBlockers: string[];
    indicatorSnapshot: Record<string, string | number | null>;
    newsSnapshot: { sentiment: number; relevance: number; articleCount: number; citations: string[] };
    lastUpdated: string;
    provenance: Record<string, string>;
    dataQuality: DataQuality;
    waterfall: SignalWaterfall;
  };
  news: Array<{ title: string; source: string; publishedAt: string; url: string; sentiment: number; relevance: number }>;
  audit: Array<{ createdAt: string; action: string; confidence: number; policyPass: boolean; reasonCodes: ReasonCode[]; riskFlags: RiskFlag[] }>;
  backtestSummary: Record<string, number | string | null>;
  macro: MacroSnapshot;
  providerBadges: ProviderBadge[];
  portfolioSummary: Record<string, number | string | boolean>;
  signalDiff: SignalDiff;
  readiness: Readiness;
  fallbackPlan: FallbackGroup[];
};

export type ProviderBadge = {
  label: string;
  status: string;
  category: string;
  freshnessSeconds?: number | null;
};

export type ProviderStatus = {
  name: string;
  label: string;
  category: string;
  status: string;
  keyPresent: boolean;
  configuredKeys: number;
  requiredKeys: number;
  browserExposed: boolean;
  freshnessSeconds?: number | null;
  lastSync?: string | null;
  capabilities: string[];
  detail: string;
  licensing: string;
};

export type MacroSnapshot = {
  regime: "risk_on" | "neutral" | "risk_off" | string;
  riskScore: number;
  ratesTrend: string;
  inflationPressure: string;
  creditStress: string;
  growthMomentum: string;
  summary: string;
  components: Record<string, unknown>;
  caveat?: string;
};

export type SignalDiff = {
  available: boolean;
  headline: string;
  changes: Array<Record<string, unknown>>;
};

export type PortfolioResponse = {
  mode: "demo" | "live";
  workspaceId: string;
  source: string;
  alpacaSync: { enabled: boolean; status: string; detail: string };
  summary: Record<string, number | string | boolean>;
  positions: Array<Record<string, string | number | boolean | null>>;
  recentOrders: Array<Record<string, unknown>>;
  journal: Array<Record<string, unknown>>;
  riskHeatmap: { grossExposure: number; cells: Array<Record<string, string | number | boolean | null>> };
};

export type WorkspaceResponse = {
  workspaceId: string;
  auth: { mode: string; roles: string[]; detail: string };
  savedWatchlists: Array<Record<string, unknown>>;
  savedScanners: Array<Record<string, unknown>>;
  chartLayouts: Array<Record<string, unknown>>;
  symbolNotes: Array<Record<string, unknown>>;
  reportHistory: Array<Record<string, unknown>>;
};
