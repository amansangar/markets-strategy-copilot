from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.config import Settings, get_settings


ProviderStatus = Literal["healthy", "configured", "degraded", "offline", "disabled"]


@dataclass(frozen=True)
class ProviderDefinition:
    name: str
    label: str
    category: str
    env_keys: tuple[str, ...]
    capabilities: tuple[str, ...]
    licensing: str
    optional: bool = True
    browser_exposed: bool = False


PROVIDERS: tuple[ProviderDefinition, ...] = (
    ProviderDefinition("polygon", "Polygon", "market_data", ("polygon_api_key",), ("historical_bars", "rest_live_refresh", "backend_snapshot_websocket", "reference_data"), "Requires Polygon account/API plan. Live mode uses REST refresh plus the local backend WebSocket snapshot channel; respect market-data redistribution terms.", optional=False),
    ProviderDefinition("newsapi", "NewsAPI", "news", ("newsapi_api_key",), ("top_headlines", "everything", "headline_discovery"), "NewsAPI free tier has caching, latency, and production-use limitations.", optional=False),
    ProviderDefinition("openai", "OpenAI", "ai_enrichment", ("openai_api_key",), ("classification", "structured_explanations", "report_drafting"), "Server-side only. Used for explanation and categorisation, never direct price prediction.", optional=False),
    ProviderDefinition("alpaca", "Alpaca Paper", "brokerage_paper", ("apca_api_key_id", "apca_api_secret_key"), ("paper_account_sync", "paper_positions", "paper_orders"), "Paper trading only in this app. No real-money order execution is implemented.", optional=True),
    ProviderDefinition("fred", "FRED", "macro", ("fred_api_key",), ("macro_series", "economic_releases"), "FRED series availability and vintage/revision behaviour must be cited in reports.", optional=True),
    ProviderDefinition("sec", "SEC EDGAR", "filings", ("sec_user_agent",), ("submissions", "company_facts", "filing_timeline"), "Read-only SEC data. Requires a clear SEC_USER_AGENT per SEC fair-access guidance.", optional=True),
    ProviderDefinition("finnhub", "Finnhub", "optional_enrichment", ("finnhub_api_key",), ("fallback_quotes", "company_metadata", "news"), "Optional fallback/enrichment. Free-tier limits and licensing vary by endpoint.", optional=True),
    ProviderDefinition("alphavantage", "Alpha Vantage", "optional_enrichment", ("alphavantage_api_key",), ("daily_prices", "reference", "economic"), "Optional fallback. Free-tier throttling can be strict.", optional=True),
    ProviderDefinition("fmp", "Financial Modeling Prep", "optional_enrichment", ("fmp_api_key",), ("fundamentals", "transcripts", "earnings"), "Optional enrichment. Check licensing before redistribution or commercial use.", optional=True),
    ProviderDefinition("twelvedata", "Twelve Data", "free_tier_enrichment", ("twelvedata_api_key",), ("fallback_quotes", "time_series", "technical_indicators", "forex_crypto"), "Optional free-tier market-data fallback. Rate limits and exchange licensing apply.", optional=True),
    ProviderDefinition("marketaux", "Marketaux", "free_tier_enrichment", ("marketaux_api_key",), ("finance_news", "entity_mapping", "news_metadata"), "Optional financial-news fallback with a limited free tier.", optional=True),
    ProviderDefinition("eodhd", "EODHD", "free_tier_enrichment", ("eodhd_api_key",), ("eod_prices", "reference_data", "limited_fundamentals"), "Optional low-volume EOD/fundamentals fallback. Free tier is very limited.", optional=True),
    ProviderDefinition("clerk", "Clerk", "auth", ("next_public_clerk_publishable_key", "clerk_secret_key"), ("auth", "roles", "workspaces"), "Optional auth. Missing keys keep the app in guest/local mode.", optional=True, browser_exposed=True),
    ProviderDefinition("resend", "Resend", "email", ("resend_api_key", "resend_from_email"), ("signal_email", "weekly_digest", "report_delivery"), "Optional outbound email. Disabled unless sender and key are both present.", optional=True),
)


class ProviderAdapter:
    """Small adapter interface used by live integrations and tests.

    Network calls are intentionally optional: demo mode and missing credentials
    return structured degraded responses instead of raising into the UI.
    """

    def __init__(self, definition: ProviderDefinition, settings: Settings | None = None) -> None:
        self.definition = definition
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return all(_present(self.settings, key) for key in self.definition.env_keys)

    def health(self, mode: str = "demo") -> dict:
        row = next(item for item in provider_matrix(mode) if item["name"] == self.definition.name)
        return row

    async def fetch(self, *_args, **_kwargs) -> dict:
        if not self.configured:
            return {
                "status": "disabled" if self.definition.optional else "offline",
                "provider": self.definition.name,
                "data": None,
                "detail": f"{self.definition.label} is not fully configured.",
            }
        return {
            "status": "deferred",
            "provider": self.definition.name,
            "data": None,
            "detail": "Provider-specific network fetch is intentionally routed through dedicated clients or future background jobs.",
        }


def adapter_registry() -> dict[str, ProviderAdapter]:
    settings = get_settings()
    return {definition.name: ProviderAdapter(definition, settings) for definition in PROVIDERS}


def _present(settings: Settings, attr: str) -> bool:
    value = getattr(settings, attr, None)
    return bool(value and str(value).strip())


def provider_matrix(mode: str = "demo") -> list[dict]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    for provider in PROVIDERS:
        present_count = sum(1 for key in provider.env_keys if _present(settings, key))
        total = len(provider.env_keys)
        fully_configured = present_count == total
        partially_configured = 0 < present_count < total

        if mode == "demo" and provider.name in {"polygon", "newsapi", "openai"}:
            if provider.name == "openai" and not fully_configured:
                status: ProviderStatus = "disabled"
                detail = "OpenAI is not called in demo mode. Live AI explanations enable when OPENAI_API_KEY is configured."
            else:
                status = "healthy"
                detail = (
                    "Demo mode intentionally uses deterministic repository data; live credentials are not required."
                    if provider.name != "openai"
                    else "OpenAI is connected for live mode. Demo mode uses deterministic local explanations so the app stays fast and repeatable."
                )
        elif fully_configured:
            status = "configured"
            detail = f"{provider.label} is configured. Run Check connections to verify live health without exposing keys."
        elif partially_configured:
            status = "degraded"
            detail = f"{provider.label} is partially configured; missing companion values keep related features limited."
        elif provider.optional:
            status = "disabled"
            detail = f"{provider.label} is optional and disabled because its environment variables are missing."
        else:
            status = "offline"
            detail = f"{provider.label} is required for live enrichment but is missing credentials."

        if provider.name == "resend" and not _present(settings, "resend_from_email"):
            status = "disabled"
            detail = "Outbound email is disabled because RESEND_FROM_EMAIL is missing."
        if provider.name == "clerk" and not fully_configured:
            status = "disabled"
            detail = "Auth is disabled; guest/local workspace mode is active."
        if provider.name == "openai" and fully_configured:
            if settings.openai_model.strip().lower() in {"latest", "auto", "default", ""}:
                detail = f"OpenAI is configured. Model selection uses the latest supported server-side model for this app ({settings.resolved_openai_model}). Runtime errors are shown honestly."
            else:
                detail = f"{detail} Model: {settings.resolved_openai_model}."

        rows.append(
            {
                "name": provider.name,
                "label": provider.label,
                "category": provider.category,
                "status": status,
                "mode": mode,
                "keyPresent": fully_configured,
                "configuredKeys": present_count,
                "requiredKeys": total,
                "browserExposed": provider.browser_exposed,
                "freshnessSeconds": 0 if mode == "demo" and status == "healthy" else None,
                "lastSync": now.isoformat() if mode == "demo" and status in {"healthy", "degraded"} else None,
                "capabilities": list(provider.capabilities),
                "detail": detail,
                "licensing": provider.licensing,
            }
        )
    return rows


def provider_health(mode: str = "demo") -> list[dict]:
    return [
        {
            "name": item["name"],
            "status": item["status"],
            "latencyMs": 0 if mode == "demo" and item["status"] in {"healthy", "degraded"} else None,
            "freshnessSeconds": item["freshnessSeconds"],
            "detail": item["detail"],
        }
        for item in provider_matrix(mode)
        if item["name"] in {"polygon", "newsapi", "openai", "fred", "sec", "alpaca"}
    ]


def provider_badges(mode: str = "demo") -> list[dict]:
    return [
        {"label": row["label"], "status": row["status"], "category": row["category"], "freshnessSeconds": row["freshnessSeconds"]}
        for row in provider_matrix(mode)
        if row["category"] in {"market_data", "news", "ai_enrichment", "macro", "filings", "brokerage_paper", "free_tier_enrichment"}
    ]
