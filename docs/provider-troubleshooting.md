# Provider Troubleshooting

This app reports provider state without exposing secret values. Treat the status labels as operational guidance:

- `healthy`: a lightweight read-only check responded successfully.
- `degraded`: the key is configured, but the provider check failed, timed out, hit a free-tier/rate/licensing limit, or returned unusable data.
- `missing`: a required variable is absent.
- `disabled`: an optional integration is intentionally off.
- `manual-check-needed`: automated checks would require sign-in, event emission, or sending email, so the app avoids side effects.

## Fixing Degraded Providers

Alpha Vantage commonly degrades when the free tier is throttled or the key is not enabled for the endpoint being checked. Wait for the quota window to reset, verify the key in the Alpha Vantage dashboard, or upgrade the plan if you need frequent checks.

Financial Modeling Prep can degrade when the endpoint is not available on the current plan or the key is restricted. Check that the key has access to the profile/fundamentals endpoints you want to use, and review FMP licensing before redistributing any enriched data.

For any provider, first confirm the variable name in `.env.example`, then restart the backend so Pydantic settings reload from the repo-root `.env`.

## Extra APIs Worth Considering

Do not add more providers unless they solve a clear gap. The current stack is already strong for an assessment build.

Useful optional additions:

- Twelve Data: broad multi-asset market data fallback, especially forex and crypto.
- Marketaux: stronger finance-news/entity metadata fallback if NewsAPI is too broad.
- Tiingo: equities/end-of-day and news fallback if you later want another simple provider.

Recommended priority:

1. Fix current degraded Alpha Vantage/FMP keys or limits first.
2. Add Twelve Data only if you want a second live quote/bar fallback.
3. Add a specialist news provider only if the project needs better real-time finance headlines than NewsAPI.

## Safety Rules

Never put provider keys in frontend code. Only `NEXT_PUBLIC_*` values may be read by the browser, and even those should not contain private secrets.
