import type { MarketMode } from "@/lib/use-market-mode";

type ProviderHealthLike = {
  name?: string;
  status?: string;
  detail?: string;
};

const CRITICAL_LIVE_PROVIDERS = new Map<string, Set<string>>([
  ["polygon", new Set(["offline", "degraded", "missing", "error", "unhealthy"])],
  ["newsapi", new Set(["offline", "missing", "error", "unhealthy"])],
]);

export function shouldAttemptLiveFallback(mode: MarketMode): boolean {
  return mode === "live";
}

export function liveFallbackReasonFromHealth(health: ProviderHealthLike[] | null | undefined): string | null {
  const issue = (health ?? []).find((item) => {
    const provider = String(item.name ?? "").toLowerCase();
    const status = String(item.status ?? "").toLowerCase();
    const fallbackStatuses = CRITICAL_LIVE_PROVIDERS.get(provider);
    return fallbackStatuses?.has(status);
  });

  if (!issue) {
    return null;
  }

  const providerName = issue.name ?? "Live provider";
  const status = issue.status ?? "unavailable";
  const detail = issue.detail ? ` ${issue.detail}` : "";
  return `${providerName} is ${status}.${detail} Live mode stays selected while the app shows a labelled local fallback until the next refresh succeeds.`;
}

export function liveFallbackReasonFromError(error: unknown): string {
  const message = error instanceof Error ? error.message : "The live request could not be completed.";
  return `${message} Live mode stays selected, and the app is using a clearly labelled local fallback because live data or internet access is currently unavailable.`;
}
