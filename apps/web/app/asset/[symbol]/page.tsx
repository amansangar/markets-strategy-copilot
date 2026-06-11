import { AssetDetailClient } from "@/components/asset-detail-client";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function fetchInitialAsset(symbol: string, mode: "demo" | "live", timeoutMs: number): Promise<any | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}/api/v1/assets/${encodeURIComponent(symbol)}?mode=${mode}`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      return null;
    }
    return response.json();
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

async function getInitialAsset(symbol: string): Promise<any | null> {
  return fetchInitialAsset(symbol, "demo", 15_000);
}

export default async function AssetDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params;
  const initialDetail = await getInitialAsset(symbol);
  return <AssetDetailClient symbol={symbol} initialDetail={initialDetail} />;
}
