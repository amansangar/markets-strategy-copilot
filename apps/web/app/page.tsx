import { DashboardClient } from "@/components/dashboard-client";
import type { DashboardResponse } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function fetchInitialDashboard(mode: "demo" | "live", timeoutMs: number): Promise<DashboardResponse | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}/api/v1/dashboard?mode=${mode}&symbol=SPY`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as DashboardResponse;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

async function getInitialDashboard(): Promise<DashboardResponse | null> {
  return fetchInitialDashboard("demo", 8_000);
}

export default async function Home() {
  const initialDashboard = await getInitialDashboard();
  return <DashboardClient initialDashboard={initialDashboard} />;
}
