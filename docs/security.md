# Security

Security rules implemented for the v2 upgrade:

- Real keys belong only in `.env`, which is ignored and excluded from release ZIPs.
- `.env.example` contains blank placeholders only.
- Only `NEXT_PUBLIC_*` variables are allowed to reach the browser.
- Server-side keys for Clerk, Alpaca, FRED, Finnhub, Alpha Vantage, FMP, Resend, Polygon, NewsAPI, and OpenAI are never returned by API responses.
- Provider status reports key presence counts and enabled/disabled state, never key values.
- Packaging excludes `.env`, local databases, caches, build outputs, `node_modules`, virtualenvs, and runtime temp artefacts.
- If optional integrations are missing, features degrade to local/demo/disabled states.

Before sharing a release ZIP, rerun the release packaging script and inspect the archive if keys were ever added locally.
