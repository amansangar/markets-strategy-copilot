import type { DashboardResponse, PortfolioResponse, WorkspaceResponse } from "@/lib/types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

async function fetchWithTimeout(url: string, init: RequestInit = {}, timeoutMs = 15_000): Promise<Response> {
  const controller = new AbortController();
  let timeout: ReturnType<typeof globalThis.setTimeout>;
  try {
    return await Promise.race([
      fetch(url, { ...init, signal: controller.signal }),
      new Promise<never>((_, reject) => {
        timeout = globalThis.setTimeout(() => {
          controller.abort();
          reject(new Error(`API request timed out after ${Math.round(timeoutMs / 1000)}s`));
        }, timeoutMs);
      }),
    ]);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`API request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw error;
  } finally {
    globalThis.clearTimeout(timeout!);
  }
}

export async function fetchDashboard(mode: "demo" | "live", symbol: string): Promise<DashboardResponse> {
  const timeoutMs = mode === "live" ? 10_000 : 20_000;
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/dashboard?mode=${mode}&symbol=${symbol}`, { cache: "no-store" }, timeoutMs);
  return parseJson<DashboardResponse>(response);
}

export async function fetchAssetDetail(symbol: string, mode: "demo" | "live") {
  const timeoutMs = mode === "live" ? 15_000 : 30_000;
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/assets/${symbol}?mode=${mode}`, { cache: "no-store" }, timeoutMs);
  return parseJson<any>(response);
}

export async function fetchScanner(params: URLSearchParams) {
  const timeoutMs = params.get("mode") === "live" ? 12_000 : 12_000;
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/scanner?${params.toString()}`, { cache: "no-store" }, timeoutMs);
  return parseJson<any>(response);
}

export async function runBacktest(body: Record<string, unknown>) {
  const response = await fetch(`${API_BASE}/api/v1/backtests/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJson<any>(response);
}

export async function fetchAlerts(): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/v1/alerts`, { cache: "no-store" });
  return parseJson<any[]>(response);
}

export async function toggleAlert(alertId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/alerts/${alertId}/toggle`, { method: "POST" });
  return parseJson<any>(response);
}

export async function fetchReports(): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/v1/reports`, { cache: "no-store" });
  return parseJson<any[]>(response);
}

export async function exportReport(symbol: string, mode: "demo" | "live", preset = "Mean Reversion"): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/reports/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, mode, preset }),
  });
  return parseJson<any>(response);
}

export function reportDownloadUrl(report: { reportId: string; downloadUrl?: string | null }): string {
  const path = report.downloadUrl || `/api/v1/reports/${report.reportId}/download`;
  return `${API_BASE}${path}`;
}

export async function fetchSystemStatus(mode: "demo" | "live"): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/system/status?mode=${mode}`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchProviderStatus(mode: "demo" | "live"): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/providers/status?mode=${mode}`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchReadiness(mode: "demo" | "live"): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/system/readiness?mode=${mode}`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchProviderChecks(): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/providers/checks`, { cache: "no-store" }, 12_000);
  return parseJson<any>(response);
}

export async function fetchProviderFailoverTimeline(mode: "demo" | "live"): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/providers/failover-timeline?mode=${mode}`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchProviderBudget(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/providers/budget`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchSignalQuality(mode: "demo" | "live"): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/signals/quality?mode=${mode}`, { cache: "no-store" }, mode === "live" ? 12_000 : 20_000);
  return parseJson<any>(response);
}

export async function fetchSignalGovernance(symbol: string, mode: "demo" | "live"): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/signals/governance/${symbol}?mode=${mode}`, { cache: "no-store" }, mode === "live" ? 12_000 : 20_000);
  return parseJson<any>(response);
}

export async function fetchUniverse(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/universe`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchDataCoverage(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/data/coverage`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchStrategyMatrix(symbol: string, mode: "demo" | "live"): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/backtests/compare?symbol=${symbol}&mode=${mode}`, { cache: "no-store" }, mode === "live" ? 12_000 : 15_000);
  return parseJson<any>(response);
}

export async function askResearchAssistant(body: { question: string; symbol: string; mode: "demo" | "live" }): Promise<any> {
  const response = await fetchWithTimeout(
    `${API_BASE}/api/v1/assistant/research`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    12_000,
  );
  return parseJson<any>(response);
}

export async function fetchSetupGuide(mode: "demo" | "live"): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/system/setup-guide?mode=${mode}`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchDemoBriefing(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/demo/briefing`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function warmDemo(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/demo/warmup`, { method: "POST", cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchPortfolio(mode: "demo" | "live"): Promise<PortfolioResponse> {
  const response = await fetch(`${API_BASE}/api/v1/portfolio?mode=${mode}`, { cache: "no-store" });
  return parseJson<PortfolioResponse>(response);
}

export async function fetchWorkspace(): Promise<WorkspaceResponse> {
  const response = await fetch(`${API_BASE}/api/v1/workspace`, { cache: "no-store" });
  return parseJson<WorkspaceResponse>(response);
}

export async function fetchAlertCenter(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/alerts/center`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchReplay(symbol: string, cursor: number, mode: "demo" | "live"): Promise<any> {
  const params = new URLSearchParams({ cursor: String(cursor), mode });
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/replay/${symbol}?${params.toString()}`, { cache: "no-store" }, mode === "live" ? 12_000 : 15_000);
  return parseJson<any>(response);
}

export async function fetchAudit(symbol: string): Promise<any[]> {
  const response = await fetch(`${API_BASE}/api/v1/audit/${symbol}`, { cache: "no-store" });
  return parseJson<any[]>(response);
}

export async function fetchStrategyBuilder(symbol: string, mode: "demo" | "live"): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/strategy-builder/${symbol}?mode=${mode}`, { cache: "no-store" }, mode === "live" ? 10_000 : 12_000);
  return parseJson<any>(response);
}

export async function evaluateStrategyRule(body: { symbol: string; mode: "demo" | "live"; rule: string }): Promise<any> {
  const response = await fetchWithTimeout(
    `${API_BASE}/api/v1/strategy-builder/evaluate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    12_000,
  );
  return parseJson<any>(response);
}

export async function fetchMultiChart(symbols: string[], timeframe = "1d"): Promise<any> {
  const params = new URLSearchParams({ symbols: symbols.join(","), timeframe });
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/terminal/multi-chart?${params.toString()}`, { cache: "no-store" }, 12_000);
  return parseJson<any>(response);
}

export async function fetchChartWorkspace(symbol: string): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/chart-workspace/${symbol}`, { cache: "no-store" }, 12_000);
  return parseJson<any>(response);
}

export async function fetchAlertBuilder(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/alerts/builder`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchReplayLab(symbol: string, cursor: number): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/replay-lab/${symbol}?cursor=${cursor}`, { cache: "no-store" }, 10_000);
  return parseJson<any>(response);
}

export async function fetchScannerColumns(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/scanner/columns`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchComparison(symbols: string[]): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/compare?symbols=${encodeURIComponent(symbols.join(","))}`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchEventsCalendar(mode: "demo" | "live"): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/events/calendar?mode=${mode}`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchTearSheet(symbol: string, mode: "demo" | "live"): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/tear-sheet/${symbol}?mode=${mode}`, { cache: "no-store" }, mode === "live" ? 10_000 : 12_000);
  return parseJson<any>(response);
}

export async function fetchPatterns(symbol: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/patterns/${symbol}`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchRankedOpportunities(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/opportunities/ranked`, { cache: "no-store" });
  return parseJson<any>(response);
}

export async function fetchProTerminal(mode: "demo" | "live"): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/pro-terminal?mode=${mode}`, { cache: "no-store" }, mode === "live" ? 8_000 : 20_000);
  return parseJson<any>(response);
}

export function websocketUrl(): string {
  return API_BASE.replace(/^http/, "ws") + "/ws/market";
}
