from __future__ import annotations

from datetime import datetime, timezone

import httpx
from openai import OpenAI

from app.config import Settings, get_settings
from app.services.providers import provider_health


POLYGON_REST = "https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{date_from}/{date_to}"
NEWSAPI_TOP = "https://newsapi.org/v2/top-headlines"
NEWSAPI_EVERYTHING = "https://newsapi.org/v2/everything"


def service_health(mode: str) -> list[dict]:
    _ = datetime.now(timezone.utc).isoformat()
    return provider_health(mode)


class PolygonClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def historical_bars(self, symbol: str, multiplier: int, timespan: str, date_from: str, date_to: str) -> dict:
        if not self.settings.polygon_api_key:
            raise RuntimeError("POLYGON_API_KEY is missing")
        url = POLYGON_REST.format(
            symbol=symbol,
            multiplier=multiplier,
            timespan=timespan,
            date_from=date_from,
            date_to=date_to,
        )
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, params={"apiKey": self.settings.polygon_api_key})
            response.raise_for_status()
            return response.json()


class NewsApiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def top_headlines(self, query: str) -> dict:
        if not self.settings.newsapi_api_key:
            raise RuntimeError("NEWSAPI_API_KEY is missing")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(NEWSAPI_TOP, params={"q": query, "apiKey": self.settings.newsapi_api_key, "language": "en"})
            response.raise_for_status()
            return response.json()

    async def everything(self, query: str) -> dict:
        if not self.settings.newsapi_api_key:
            raise RuntimeError("NEWSAPI_API_KEY is missing")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                NEWSAPI_EVERYTHING,
                params={"q": query, "apiKey": self.settings.newsapi_api_key, "language": "en", "sortBy": "publishedAt"},
            )
            response.raise_for_status()
            return response.json()


class OpenAIEnrichmentClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def classify_headline(self, headline: str, description: str) -> dict:
        if not self.client:
            return {"status": "offline", "sentiment": 0.0, "relevance": 0.0, "summary": "OpenAI unavailable; technical-only mode in effect."}
        response = self.client.responses.create(
            model=self.settings.resolved_openai_model,
            input=[
                {
                    "role": "system",
                    "content": "Return compact JSON with keys sentiment, relevance, summary. Do not predict prices.",
                },
                {"role": "user", "content": f"Headline: {headline}\nDescription: {description}"},
            ],
        )
        return {"status": "ok", "raw": response.output_text}
