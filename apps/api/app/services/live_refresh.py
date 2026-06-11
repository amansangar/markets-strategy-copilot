from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import os
import threading

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import Bar, NewsArticle
from app.repository import get_symbol


_REFRESH_CACHE: dict[str, datetime] = {}
_DAILY_REFRESH_CACHE: dict[str, datetime] = {}
_REFRESH_TTL_SECONDS = 55
_DAILY_REFRESH_TTL_SECONDS = 60 * 60 * 6
_NEWSAPI_SYMBOL_CACHE_MINUTES = 30
_NEWSAPI_TOP_HEADLINES_CACHE_MINUTES = 30
_PROVIDER_BUDGETS: dict[tuple[str, str], dict] = {}
_REFRESH_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="live-refresh")
_IN_FLIGHT: set[str] = set()
_REFRESH_LOCK = threading.Lock()
_BUDGET_LOCK = threading.Lock()


def _budget_allows(provider: str, scope: str, cooldown_seconds: int) -> tuple[bool, dict]:
    now = datetime.now(timezone.utc)
    key = (provider, scope)
    with _BUDGET_LOCK:
        entry = _PROVIDER_BUDGETS.get(key)
        if entry:
            next_allowed = entry.get("nextAllowedAt")
            if isinstance(next_allowed, datetime) and now < next_allowed:
                return False, dict(entry)
        entry = {
            "provider": provider,
            "scope": scope,
            "lastRequestAt": now,
            "nextAllowedAt": now + timedelta(seconds=cooldown_seconds),
            "lastStatus": "scheduled",
            "notes": "Request budget window reserved.",
        }
        _PROVIDER_BUDGETS[key] = entry
        return True, dict(entry)


def _record_budget_status(provider: str, scope: str, status: str, notes: str = "") -> None:
    now = datetime.now(timezone.utc)
    key = (provider, scope)
    with _BUDGET_LOCK:
        entry = _PROVIDER_BUDGETS.setdefault(
            key,
            {
                "provider": provider,
                "scope": scope,
                "lastRequestAt": now,
                "nextAllowedAt": now,
            },
        )
        entry["lastStatus"] = status
        entry["notes"] = notes


def provider_budget_snapshot() -> list[dict]:
    with _BUDGET_LOCK:
        rows = [dict(entry) for entry in _PROVIDER_BUDGETS.values()]
    for row in rows:
        for key in ("lastRequestAt", "nextAllowedAt"):
            value = row.get(key)
            if isinstance(value, datetime):
                row[key] = value.isoformat()
    return sorted(rows, key=lambda item: (item.get("provider", ""), item.get("scope", "")))


def schedule_live_symbol_refresh(symbol: str) -> dict:
    """Schedule a non-blocking refresh so live pages stay responsive."""

    now = datetime.now(timezone.utc)
    cached_at = _REFRESH_CACHE.get(symbol)
    if cached_at and (now - cached_at).total_seconds() < _REFRESH_TTL_SECONDS:
        return {"status": "cached", "symbol": symbol, "refreshedAt": cached_at.isoformat()}
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return {"status": "skipped", "symbol": symbol, "notes": ["Live refresh disabled during deterministic tests"]}

    with _REFRESH_LOCK:
        if symbol in _IN_FLIGHT:
            return {"status": "in_progress", "symbol": symbol}
        _IN_FLIGHT.add(symbol)

    _REFRESH_EXECUTOR.submit(_run_background_refresh, symbol)
    return {"status": "scheduled", "symbol": symbol, "scheduledAt": now.isoformat()}


def _run_background_refresh(symbol: str) -> None:
    try:
        with SessionLocal() as session:
            refresh_live_symbol(session, symbol)
    finally:
        with _REFRESH_LOCK:
            _IN_FLIGHT.discard(symbol)


def refresh_live_symbol(session: Session, symbol: str) -> dict:
    """Best-effort live refresh for the selected symbol.

    This is deliberately lightweight and safe: it performs at most one Polygon
    bar request and one NewsAPI request per symbol per minute, never raises into
    the UI, and never exposes credentials.
    """

    now = datetime.now(timezone.utc)
    cached_at = _REFRESH_CACHE.get(symbol)
    if cached_at and (now - cached_at).total_seconds() < _REFRESH_TTL_SECONDS:
        return {"status": "cached", "symbol": symbol, "refreshedAt": cached_at.isoformat()}

    settings = get_settings()
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return {"status": "skipped", "symbol": symbol, "notes": ["Live refresh disabled during deterministic tests"]}

    result = {"status": "refreshed", "symbol": symbol, "barsAdded": 0, "newsAdded": 0, "notes": []}

    try:
        meta = get_symbol(session, symbol)
    except KeyError:
        return {"status": "skipped", "symbol": symbol, "notes": ["Unknown symbol"]}

    bars_need_fallback = False
    if settings.polygon_api_key:
        try:
            result["barsAdded"] = _refresh_polygon_bars(session, symbol, meta.asset_class)
            result["dailyBarsAdded"] = _refresh_polygon_daily_bars(session, symbol, meta.asset_class)
        except Exception as exc:  # noqa: BLE001 - provider degradation should be visible but non-fatal.
            result["notes"].append(f"Polygon refresh skipped: {type(exc).__name__}")
            bars_need_fallback = True
    else:
        result["notes"].append("Polygon key missing")
        bars_need_fallback = True

    if _bar_needs_fallback(session, symbol, "5m", meta.asset_class):
        bars_need_fallback = True

    if bars_need_fallback and settings.twelvedata_api_key:
        try:
            result["twelveDataBarsAdded"] = _refresh_twelvedata_bars(session, symbol, meta.asset_class, "5min", "5m", 500)
            result["twelveDataDailyBarsAdded"] = _refresh_twelvedata_bars(session, symbol, meta.asset_class, "1day", "1d", 760)
        except Exception as exc:  # noqa: BLE001 - optional fallback must never crash live pages.
            result["notes"].append(f"Twelve Data fallback skipped: {type(exc).__name__}")
    elif bars_need_fallback:
        result["notes"].append("Twelve Data fallback key missing")

    news_added = 0
    if settings.newsapi_api_key:
        try:
            news_added = _refresh_news(session, symbol, meta.name)
            result["newsAdded"] = news_added
        except Exception as exc:  # noqa: BLE001 - provider degradation should be visible but non-fatal.
            result["notes"].append(f"News refresh skipped: {type(exc).__name__}")
    else:
        result["notes"].append("NewsAPI key missing")

    if news_added == 0 and settings.marketaux_api_key:
        try:
            result["marketauxNewsAdded"] = _refresh_marketaux_news(session, symbol)
        except Exception as exc:  # noqa: BLE001 - optional fallback must never crash live pages.
            result["notes"].append(f"Marketaux fallback skipped: {type(exc).__name__}")

    session.commit()
    _REFRESH_CACHE[symbol] = now
    result["refreshedAt"] = now.isoformat()
    return result


def _refresh_polygon_bars(session: Session, symbol: str, asset_class: str) -> int:
    settings = get_settings()
    ticker = _polygon_ticker(symbol, asset_class)
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=4)
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/5/minute/{start.isoformat()}/{end.isoformat()}"
    with httpx.Client(timeout=3.0) as client:
        response = client.get(url, params={"apiKey": settings.polygon_api_key, "adjusted": "true", "sort": "asc", "limit": 5000})
        response.raise_for_status()
        payload = response.json()

    rows = payload.get("results") or []
    if not rows:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=5)
    existing = {
        _normalise_dt(row.time): row
        for row in session.scalars(
            select(Bar).where(Bar.symbol == symbol, Bar.timeframe == "5m", Bar.time >= cutoff)
        )
    }

    added = 0
    for item in rows[-700:]:
        bar_time = datetime.fromtimestamp(float(item["t"]) / 1000.0, timezone.utc)
        row = existing.get(bar_time)
        if row:
            row.open = float(item["o"])
            row.high = float(item["h"])
            row.low = float(item["l"])
            row.close = float(item["c"])
            row.volume = float(item.get("v") or 0)
            continue
        session.add(
            Bar(
                symbol=symbol,
                timeframe="5m",
                time=bar_time,
                open=float(item["o"]),
                high=float(item["h"]),
                low=float(item["l"]),
                close=float(item["c"]),
                volume=float(item.get("v") or 0),
            )
        )
        added += 1
    return added


def _refresh_polygon_daily_bars(session: Session, symbol: str, asset_class: str) -> int:
    """Refresh longer-range history used by 1M/3M/6M/ALL live charts.

    The short live path updates every minute, but the multi-month chart ranges
    need daily bars too. Keeping a separate cache avoids a heavy historical
    request on every live poll while still preventing stale seeded history from
    being mixed with fresh intraday prices.
    """

    now = datetime.now(timezone.utc)
    cached_at = _DAILY_REFRESH_CACHE.get(symbol)
    if cached_at and (now - cached_at).total_seconds() < _DAILY_REFRESH_TTL_SECONDS:
        return 0

    settings = get_settings()
    ticker = _polygon_ticker(symbol, asset_class)
    end = now.date()
    start = end - timedelta(days=900)
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start.isoformat()}/{end.isoformat()}"
    with httpx.Client(timeout=4.0) as client:
        response = client.get(url, params={"apiKey": settings.polygon_api_key, "adjusted": "true", "sort": "asc", "limit": 5000})
        response.raise_for_status()
        payload = response.json()

    rows = payload.get("results") or []
    if not rows:
        return 0

    existing_by_date: dict[object, list[Bar]] = {}
    for row in session.scalars(
        select(Bar).where(Bar.symbol == symbol, Bar.timeframe == "1d", Bar.time >= datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc))
    ):
        existing_by_date.setdefault(_normalise_dt(row.time).date(), []).append(row)

    added = 0
    for item in rows[-760:]:
        bar_time = datetime.fromtimestamp(float(item["t"]) / 1000.0, timezone.utc)
        same_day_rows = existing_by_date.get(bar_time.date(), [])
        row = next((candidate for candidate in same_day_rows if _normalise_dt(candidate.time) == bar_time), same_day_rows[0] if same_day_rows else None)
        if row:
            row.time = bar_time
            row.open = float(item["o"])
            row.high = float(item["h"])
            row.low = float(item["l"])
            row.close = float(item["c"])
            row.volume = float(item.get("v") or 0)
            for duplicate in same_day_rows:
                if duplicate is not row:
                    session.delete(duplicate)
            continue
        session.add(
            Bar(
                symbol=symbol,
                timeframe="1d",
                time=bar_time,
                open=float(item["o"]),
                high=float(item["h"]),
                low=float(item["l"]),
                close=float(item["c"]),
                volume=float(item.get("v") or 0),
            )
        )
        added += 1

    _DAILY_REFRESH_CACHE[symbol] = now
    return added


def _refresh_news(session: Session, symbol: str, name: str) -> int:
    settings = get_settings()
    symbol_scope = f"symbol:{symbol.upper()}"
    headlines_scope = "top-headlines:business-us"
    symbol_allowed, symbol_budget = _budget_allows("newsapi", symbol_scope, _NEWSAPI_SYMBOL_CACHE_MINUTES * 60)
    headlines_allowed, headlines_budget = _budget_allows(
        "newsapi",
        headlines_scope,
        _NEWSAPI_TOP_HEADLINES_CACHE_MINUTES * 60,
    )
    if not symbol_allowed and not headlines_allowed:
        return 0

    query = f'"{symbol}" OR "{name}"'
    payload = {"articles": []}
    headline_payload = {"articles": []}
    with httpx.Client(timeout=3.0) as client:
        if symbol_allowed:
            try:
                response = client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": query,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 5,
                        "apiKey": settings.newsapi_api_key,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                _record_budget_status("newsapi", symbol_scope, "ok", "Symbol news refreshed.")
            except Exception as exc:
                _record_budget_status("newsapi", symbol_scope, "degraded", type(exc).__name__)
                raise
        if headlines_allowed:
            try:
                headline_response = client.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={
                        "country": "us",
                        "category": "business",
                        "pageSize": 5,
                        "apiKey": settings.newsapi_api_key,
                    },
                )
                headline_response.raise_for_status()
                headline_payload = headline_response.json()
                _record_budget_status("newsapi", headlines_scope, "ok", "Top headlines refreshed.")
            except Exception as exc:
                # Everything search remains the primary symbol-specific path.
                _record_budget_status("newsapi", headlines_scope, "degraded", type(exc).__name__)
                headline_payload = {"articles": []}
    if not symbol_allowed:
        _record_budget_status(
            "newsapi",
            symbol_scope,
            str(symbol_budget.get("lastStatus") or "cached"),
            "Using cached symbol news until the provider budget window reopens.",
        )
    if not headlines_allowed:
        _record_budget_status(
            "newsapi",
            headlines_scope,
            str(headlines_budget.get("lastStatus") or "cached"),
            "Using cached top headlines until the provider budget window reopens.",
        )

    candidates: list[tuple[str, dict]] = []
    seen_ids: set[str] = set()
    for article in [*(payload.get("articles") or []), *(headline_payload.get("articles") or [])]:
        title = str(article.get("title") or "").strip()
        url = str(article.get("url") or "").strip()
        if not title or not url:
            continue
        article_id = hashlib.sha1(url.encode("utf-8")).hexdigest()[:24]
        if article_id in seen_ids:
            continue
        seen_ids.add(article_id)
        candidates.append((article_id, article))

    if not candidates:
        return 0

    existing_ids = set(
        session.scalars(select(NewsArticle.id).where(NewsArticle.id.in_([article_id for article_id, _ in candidates])))
    )

    added = 0
    for article_id, article in candidates:
        if article_id in existing_ids:
            continue
        title = str(article.get("title") or "").strip()
        url = str(article.get("url") or "").strip()
        published_at = _parse_datetime(str(article.get("publishedAt") or ""))
        sentiment = _simple_sentiment(title, str(article.get("description") or ""))
        session.add(
            NewsArticle(
                id=article_id,
                source=str((article.get("source") or {}).get("name") or "NewsAPI"),
                title=title[:500],
                description=str(article.get("description") or "")[:2000],
                url=url[:500],
                published_at=published_at,
                symbols_csv=symbol,
                raw_sentiment=sentiment,
                relevance=0.72,
                enrichment_json={"provider": "newsapi", "mode": "live"},
            )
        )
        added += 1
    return added


def _refresh_twelvedata_bars(
    session: Session,
    symbol: str,
    asset_class: str,
    interval: str,
    timeframe: str,
    outputsize: int,
) -> int:
    settings = get_settings()
    if not settings.twelvedata_api_key:
        return 0

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": _twelvedata_symbol(symbol, asset_class),
        "interval": interval,
        "outputsize": outputsize,
        "format": "JSON",
        "apikey": settings.twelvedata_api_key,
    }
    with httpx.Client(timeout=3.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    values = payload.get("values") or []
    if not values:
        return 0

    parsed_rows: list[tuple[datetime, float, float, float, float, float]] = []
    for item in reversed(values):
        try:
            bar_time = _parse_datetime(str(item.get("datetime") or ""))
            parsed_rows.append(
                (
                    bar_time,
                    float(item["open"]),
                    float(item["high"]),
                    float(item["low"]),
                    float(item["close"]),
                    float(item.get("volume") or 0),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    if not parsed_rows:
        return 0

    return _upsert_bar_rows(session, symbol, timeframe, parsed_rows, dedupe_by_date=timeframe == "1d")


def _refresh_marketaux_news(session: Session, symbol: str) -> int:
    settings = get_settings()
    if not settings.marketaux_api_key:
        return 0

    with httpx.Client(timeout=3.0) as client:
        response = client.get(
            "https://api.marketaux.com/v1/news/all",
            params={
                "api_token": settings.marketaux_api_key,
                "symbols": symbol,
                "language": "en",
                "limit": 5,
                "filter_entities": "true",
            },
        )
        response.raise_for_status()
        payload = response.json()

    articles = payload.get("data") or []
    if not articles:
        return 0

    candidates: list[tuple[str, dict]] = []
    for article in articles:
        title = str(article.get("title") or "").strip()
        url = str(article.get("url") or "").strip()
        if not title or not url:
            continue
        article_id = hashlib.sha1(url.encode("utf-8")).hexdigest()[:24]
        candidates.append((article_id, article))

    if not candidates:
        return 0

    existing_ids = set(
        session.scalars(select(NewsArticle.id).where(NewsArticle.id.in_([article_id for article_id, _ in candidates])))
    )

    added = 0
    for article_id, article in candidates:
        if article_id in existing_ids:
            continue
        title = str(article.get("title") or "").strip()
        description = str(article.get("description") or article.get("snippet") or "")[:2000]
        source = article.get("source") or "Marketaux"
        session.add(
            NewsArticle(
                id=article_id,
                source=str(source),
                title=title[:500],
                description=description,
                url=str(article.get("url") or "")[:500],
                published_at=_parse_datetime(str(article.get("published_at") or article.get("publishedAt") or "")),
                symbols_csv=symbol,
                raw_sentiment=_simple_sentiment(title, description),
                relevance=0.68,
                enrichment_json={"provider": "marketaux", "mode": "live"},
            )
        )
        added += 1
    return added


def _upsert_bar_rows(
    session: Session,
    symbol: str,
    timeframe: str,
    rows: list[tuple[datetime, float, float, float, float, float]],
    *,
    dedupe_by_date: bool = False,
) -> int:
    if not rows:
        return 0

    start = min(item[0] for item in rows)
    existing_rows = list(
        session.scalars(select(Bar).where(Bar.symbol == symbol, Bar.timeframe == timeframe, Bar.time >= start - timedelta(days=1)))
    )
    if dedupe_by_date:
        existing: dict[object, list[Bar]] = {}
        for row in existing_rows:
            existing.setdefault(_normalise_dt(row.time).date(), []).append(row)
    else:
        existing = {_normalise_dt(row.time): [row] for row in existing_rows}

    added = 0
    for bar_time, open_, high, low, close, volume in rows:
        key = bar_time.date() if dedupe_by_date else bar_time
        same_time_rows = existing.get(key, [])
        row = same_time_rows[0] if same_time_rows else None
        if row:
            row.time = bar_time
            row.open = open_
            row.high = high
            row.low = low
            row.close = close
            row.volume = volume
            for duplicate in same_time_rows[1:]:
                session.delete(duplicate)
            continue
        session.add(
            Bar(
                symbol=symbol,
                timeframe=timeframe,
                time=bar_time,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
        added += 1
    return added


def _bar_needs_fallback(session: Session, symbol: str, timeframe: str, asset_class: str) -> bool:
    row = session.scalars(
        select(Bar).where(Bar.symbol == symbol, Bar.timeframe == timeframe).order_by(Bar.time.desc()).limit(1)
    ).first()
    if not row:
        return True

    now = datetime.now(timezone.utc)
    latest_time = _normalise_dt(row.time)
    age = max((now - latest_time).total_seconds(), 0.0)
    normalized_class = (asset_class or "").strip().lower()
    if normalized_class == "crypto":
        return age > 15 * 60
    if now.weekday() >= 5:
        return age > 72 * 60 * 60
    if now.weekday() < 5 and now.hour < 14:
        return age > 20 * 60 * 60
    return age > 75 * 60


def _twelvedata_symbol(symbol: str, asset_class: str) -> str:
    normalized_class = (asset_class or "").strip().lower()
    if normalized_class in {"crypto", "forex"} and len(symbol) >= 6 and "/" not in symbol:
        return f"{symbol[:3]}/{symbol[3:]}"
    return symbol


def _polygon_ticker(symbol: str, asset_class: str) -> str:
    if asset_class.lower() == "crypto" and not symbol.startswith("X:"):
        return f"X:{symbol}"
    if asset_class.lower() == "forex" and not symbol.startswith("C:"):
        return f"C:{symbol}"
    return symbol


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _normalise_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _simple_sentiment(title: str, description: str) -> float:
    text = f"{title} {description}".lower()
    positive = sum(1 for word in ("beats", "surges", "rises", "growth", "record", "upgrade", "bullish") if word in text)
    negative = sum(1 for word in ("misses", "falls", "drops", "lawsuit", "warning", "downgrade", "bearish") if word in text)
    score = (positive - negative) / max(positive + negative, 1)
    return max(-1.0, min(1.0, round(score, 3)))
