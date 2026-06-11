from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import perf_counter
from typing import Awaitable, Callable

import httpx

from app.config import get_settings


Status = str


def _configured(*values: str | None) -> bool:
    return all(bool(value and value.strip()) for value in values)


def _result(name: str, configured: bool, status: Status, note: str, latency_ms: int | None = None) -> dict:
    return {
        "name": name,
        "configured": configured,
        "status": status,
        "lastChecked": datetime.now(timezone.utc).isoformat(),
        "latencyMs": latency_ms,
        "note": note,
    }


async def _timed(name: str, configured: bool, check: Callable[[], Awaitable[bool]], success_note: str, fail_note: str) -> dict:
    if not configured:
        return _result(name, False, "missing", "Required environment variable(s) are not configured.")
    started = perf_counter()
    try:
        ok = await check()
        latency = int((perf_counter() - started) * 1000)
        return _result(name, configured, "healthy" if ok else "degraded", success_note if ok else fail_note, latency)
    except Exception:
        latency = int((perf_counter() - started) * 1000)
        return _result(name, configured, "degraded", fail_note, latency)


async def run_provider_checks(timeout_seconds: float = 4.0) -> dict:
    settings = get_settings()
    timeout = httpx.Timeout(timeout_seconds)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        checks = [
            _timed(
                "openai",
                _configured(settings.openai_api_key),
                lambda: _status_ok(client.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {settings.openai_api_key}"})),
                "OpenAI models endpoint responded.",
                "OpenAI check failed or was rate-limited; app should use technical-only fallback if needed.",
            ),
            _timed(
                "polygon",
                _configured(settings.polygon_api_key),
                lambda: _json_status(client.get("https://api.polygon.io/v1/marketstatus/now", params={"apiKey": settings.polygon_api_key})),
                "Polygon market-status endpoint responded.",
                "Polygon check failed or was rate-limited; live market data should show degraded state.",
            ),
            _timed(
                "newsapi",
                _configured(settings.newsapi_api_key),
                lambda: _json_status(client.get("https://newsapi.org/v2/top-headlines", params={"q": "markets", "pageSize": 1, "language": "en", "apiKey": settings.newsapi_api_key})),
                "NewsAPI top-headlines endpoint responded.",
                "NewsAPI check failed or was rate-limited; seeded/demo news remains available.",
            ),
            _timed(
                "alpaca",
                _configured(settings.apca_api_key_id, settings.apca_api_secret_key),
                lambda: _json_status(client.get("https://paper-api.alpaca.markets/v2/account", headers={"APCA-API-KEY-ID": settings.apca_api_key_id or "", "APCA-API-SECRET-KEY": settings.apca_api_secret_key or ""})),
                "Alpaca paper account endpoint responded.",
                "Alpaca paper check failed; local simulated portfolio remains active.",
            ),
            _timed(
                "fred",
                _configured(settings.fred_api_key),
                lambda: _json_status(client.get("https://api.stlouisfed.org/fred/series/observations", params={"series_id": "DGS10", "api_key": settings.fred_api_key, "file_type": "json", "limit": 1, "sort_order": "desc"})),
                "FRED observations endpoint responded.",
                "FRED check failed or was rate-limited; deterministic macro fallback remains available.",
            ),
            _timed(
                "sec",
                _configured(settings.sec_user_agent),
                lambda: _json_status(client.get("https://data.sec.gov/submissions/CIK0000320193.json", headers={"User-Agent": settings.sec_user_agent or "Markets Strategy Copilot local verification"})),
                "SEC submissions endpoint responded.",
                "SEC check failed; cached/demo filing intelligence remains available.",
            ),
            _timed(
                "finnhub",
                _configured(settings.finnhub_api_key),
                lambda: _json_status(client.get("https://finnhub.io/api/v1/quote", params={"symbol": "AAPL", "token": settings.finnhub_api_key})),
                "Finnhub quote endpoint responded.",
                "Finnhub check failed or free-tier limit was reached.",
            ),
            _timed(
                "alphavantage",
                _configured(settings.alphavantage_api_key),
                lambda: _json_status(client.get("https://www.alphavantage.co/query", params={"function": "GLOBAL_QUOTE", "symbol": "AAPL", "apikey": settings.alphavantage_api_key})),
                "Alpha Vantage quote endpoint responded.",
                "Alpha Vantage check failed or free-tier limit was reached.",
            ),
            _timed(
                "fmp",
                _configured(settings.fmp_api_key),
                lambda: _json_status(client.get("https://financialmodelingprep.com/api/v3/profile/AAPL", params={"apikey": settings.fmp_api_key})),
                "FMP profile endpoint responded.",
                "FMP check failed or licensing/free-tier limit blocked the request.",
            ),
            _timed(
                "twelvedata",
                _configured(settings.twelvedata_api_key),
                lambda: _json_status(client.get("https://api.twelvedata.com/price", params={"symbol": "AAPL", "apikey": settings.twelvedata_api_key})),
                "Twelve Data price endpoint responded.",
                "Twelve Data check failed or the free-tier rate limit was reached.",
            ),
            _timed(
                "marketaux",
                _configured(settings.marketaux_api_key),
                lambda: _json_status(client.get("https://api.marketaux.com/v1/news/all", params={"api_token": settings.marketaux_api_key, "symbols": "AAPL", "limit": 1, "language": "en"})),
                "Marketaux finance-news endpoint responded.",
                "Marketaux check failed or the free-tier request limit was reached.",
            ),
            _timed(
                "eodhd",
                _configured(settings.eodhd_api_key),
                lambda: _json_status(client.get("https://eodhd.com/api/real-time/AAPL.US", params={"api_token": settings.eodhd_api_key, "fmt": "json"})),
                "EODHD endpoint responded.",
                "EODHD check failed, the free-tier endpoint is unavailable, or the daily limit was reached.",
            ),
        ]
        results = await asyncio.gather(*checks)

    product = [
        _result("clerk", _configured(settings.next_public_clerk_publishable_key, settings.clerk_secret_key), "manual-check-needed" if _configured(settings.next_public_clerk_publishable_key, settings.clerk_secret_key) else "disabled", "Clerk config can be validated locally; browser sign-in should be manually checked in a normal browser."),
        _result("resend", _configured(settings.resend_api_key, settings.resend_from_email), "manual-check-needed" if _configured(settings.resend_api_key, settings.resend_from_email) else "disabled", "Resend config was not used to send real email during automated verification."),
    ]
    all_results = results + product
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "checks": all_results,
        "summary": {
            status: sum(1 for item in all_results if item["status"] == status)
            for status in ["healthy", "degraded", "missing", "disabled", "manual-check-needed"]
        },
    }


async def _status_ok(response_coro) -> bool:
    response = await response_coro
    return 200 <= response.status_code < 300


async def _json_status(response_coro) -> bool:
    response = await response_coro
    if not (200 <= response.status_code < 300):
        return False
    try:
        response.json()
    except ValueError:
        return False
    return True
