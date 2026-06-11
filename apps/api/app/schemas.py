from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ActionLiteral = Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL", "NO_SIGNAL"]
RegimeLiteral = Literal["TRENDING_BULL", "TRENDING_BEAR", "MEAN_REVERTING", "RANGE_BOUND", "RISK_OFF"]
ModeLiteral = Literal["demo", "live"]
StatusLiteral = Literal["healthy", "configured", "degraded", "offline", "disabled", "missing", "failed", "manual-check-needed", "checking"]


class ServiceHealth(BaseModel):
    name: str
    status: StatusLiteral
    latencyMs: int | None = None
    freshnessSeconds: float | None = None
    detail: str


class ReasonCode(BaseModel):
    code: str
    label: str
    weight: float
    detail: str


class RiskFlag(BaseModel):
    code: str
    severity: Literal["low", "medium", "high"]
    message: str


class Candle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorPoint(BaseModel):
    time: str
    value: float | None


class OscillatorPoint(BaseModel):
    time: str
    value: float | None
    signal: float | None = None


class SignalCard(BaseModel):
    symbol: str
    action: ActionLiteral
    confidence: float
    regime: RegimeLiteral
    horizon: str
    currentPrice: float
    stopLoss: float | None
    takeProfitLow: float | None
    takeProfitHigh: float | None
    positionSizePct: float
    dataFreshnessSeconds: float
    reasonCodes: list[ReasonCode]
    riskFlags: list[RiskFlag]
    policyBlockers: list[str]
    indicatorSnapshot: dict[str, float | str | None]
    newsSnapshot: dict[str, float | int | list[str]]
    lastUpdated: str
    provenance: dict[str, str]
    dataQuality: dict = Field(default_factory=dict)
    waterfall: dict = Field(default_factory=dict)


class WatchlistRow(BaseModel):
    symbol: str
    name: str
    lastPrice: float
    changePct: float
    signal: ActionLiteral
    confidence: float
    regime: RegimeLiteral
    sentiment: float
    volumeNote: str
    assetClass: str


class ChartPayload(BaseModel):
    symbol: str
    timeframe: str
    candles: list[Candle]
    overlays: dict[str, list[IndicatorPoint]]
    oscillators: dict[str, list[OscillatorPoint]]
    markers: list[dict] = Field(default_factory=list)
    attribution: str
    attributionUrl: str
    history: dict | None = None


class DashboardResponse(BaseModel):
    mode: ModeLiteral
    trackedAssets: int
    alertCount: int
    strongestBuy: str
    strongestSell: str
    marketRegimeSummary: str
    connectionSummary: str
    health: list[ServiceHealth]
    watchlist: list[WatchlistRow]
    chart: ChartPayload
    signal: SignalCard
    news: list[dict]
    audit: list[dict]
    backtestSummary: dict
    macro: dict
    providerBadges: list[dict]
    portfolioSummary: dict
    signalDiff: dict
    readiness: dict = Field(default_factory=dict)
    fallbackPlan: list[dict] = Field(default_factory=list)


class AssetDetailResponse(BaseModel):
    mode: ModeLiteral
    symbol: str
    metadata: dict
    chart: ChartPayload
    signal: SignalCard
    signalHistory: list[dict]
    newsTimeline: list[dict]
    auditTrail: list[dict]
    health: list[ServiceHealth]
    macro: dict
    filingTimeline: list[dict]
    filingDigest: dict
    signalDiff: dict
    replayScenarios: list[dict] = Field(default_factory=list)


class ScannerResponse(BaseModel):
    mode: ModeLiteral
    results: list[dict]
    filtersApplied: dict


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    preset: str = "Mean Reversion"
    feesBps: float = 2.0
    spreadBps: float = 2.0
    slippageBps: float = 1.0
    longShort: bool = False
    ablation: Literal["technical_only", "technical_news", "technical_news_tca"] = "technical_news_tca"


class BacktestResponse(BaseModel):
    runId: str
    symbol: str
    preset: str
    metrics: dict
    equityCurve: list[dict]
    drawdownCurve: list[dict]
    tradeList: list[dict]
    walkForward: list[dict]
    chartMarkers: list[dict]
    robustness: dict = Field(default_factory=dict)


class AlertResponse(BaseModel):
    id: str
    symbol: str
    kind: str
    name: str
    enabled: bool
    rule: dict
    history: list[dict]


class ReportRequest(BaseModel):
    symbol: str
    mode: ModeLiteral = "demo"
    preset: str = "Mean Reversion"


class ReportResponse(BaseModel):
    reportId: str
    symbol: str
    mode: ModeLiteral
    path: str
    downloadUrl: str | None = None
    createdAt: datetime


class SystemStatusResponse(BaseModel):
    mode: ModeLiteral
    generatedAt: str
    technicalOnlyMode: bool
    health: list[ServiceHealth]
    message: str
    providers: list[dict] = Field(default_factory=list)
    observability: dict = Field(default_factory=dict)


class PortfolioResponse(BaseModel):
    mode: ModeLiteral
    workspaceId: str
    source: str
    alpacaSync: dict
    summary: dict
    positions: list[dict]
    recentOrders: list[dict]
    journal: list[dict]
    riskHeatmap: dict = Field(default_factory=dict)


class WorkspaceResponse(BaseModel):
    workspaceId: str
    auth: dict
    savedWatchlists: list[dict]
    savedScanners: list[dict]
    chartLayouts: list[dict]
    symbolNotes: list[dict]
    reportHistory: list[dict]
