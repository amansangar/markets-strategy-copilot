# Provider Matrix

Markets Strategy Copilot uses a provider registry so optional integrations can be enabled independently without breaking demo mode.

| Provider | Purpose | Env vars | Missing-key behaviour |
| --- | --- | --- | --- |
| Polygon | Historical bars and REST live-refresh market data | `POLYGON_API_KEY` | Live market data is offline; demo data remains available. |
| NewsAPI | Live tape and article discovery | `NEWSAPI_API_KEY` | Live news is offline; seeded demo news remains available. |
| OpenAI | Server-side classification/explanations/reports | `OPENAI_API_KEY` | Technical-only deterministic explanations are used. |
| Alpaca Paper | Paper account/portfolio sync | `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY` | Local simulated paper portfolio remains active. |
| FRED | Macro/economic series | `FRED_API_KEY` | Deterministic demo macro regime is used. |
| SEC EDGAR | Filings/submissions/company facts | `SEC_USER_AGENT` | Seeded filing/event markers are shown in demo mode. |
| Finnhub | Optional quote/news/metadata fallback | `FINNHUB_API_KEY` | Provider is disabled. |
| Alpha Vantage | Optional daily/reference/economic fallback | `ALPHAVANTAGE_API_KEY` | Provider is disabled. |
| FMP | Optional fundamentals/transcripts enrichment | `FMP_API_KEY` | Provider is disabled. |
| Twelve Data | Optional free-tier quote/time-series/indicator fallback | `TWELVEDATA_API_KEY` | Provider is disabled. |
| Marketaux | Optional finance-news fallback with entity metadata | `MARKETAUX_API_KEY` | Provider is disabled. |
| EODHD | Optional low-volume EOD/reference/fundamentals fallback | `EODHD_API_KEY` | Provider is disabled. |
| Clerk | Optional auth/workspaces | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` | Guest/local workspace mode remains open. |
| Resend | Optional email alerts/report delivery | `RESEND_API_KEY`, `RESEND_FROM_EMAIL` | Browser/in-app alerts remain active; email is disabled. |

The Settings page exposes provider status, key-present status without values, freshness, category, and licensing notes.

## Status Semantics

- `Configured` means the required environment variable names are present locally, but no live request has been made in the current check.
- `Healthy` means a lightweight read-only provider check succeeded.
- `Degraded`, `failed`, or `manual-check-needed` means the provider should not be treated as fully available.
- `Disabled` means the integration is optional and not configured; the app must continue in demo/local mode.

## Free-Tier Budget Guardrails

The app should prefer cached responses and avoid high-frequency polling for free-tier services. Safe working assumptions are:

| Provider | Conservative budget |
| --- | --- |
| Alpha Vantage | 25 requests/day |
| NewsAPI Developer | 100 requests/day |
| Resend free | 100 emails/day |
| FMP Basic | 250 requests/day |
| Polygon free | 5 requests/minute |
| Alpaca Basic | 200 requests/minute |
| Finnhub free | 60 requests/minute |
| SEC EDGAR | 10 requests/second |

News and enrichment providers should be cached for at least 15-30 minutes during live demos. Market bars should prefer cached history plus live/fallback refreshes rather than repeated full REST pulls.
