# Architecture Decisions

## ADR-001: Use a real frontend + backend split

The interim report mentions Streamlit as an efficient option, but the final build deliberately uses Next.js + FastAPI to satisfy the stronger implementation brief for a production-sensible web application with clean module boundaries, typed contracts, and richer UX.

## ADR-002: Demo mode is deterministic and repo-seeded

Demo data is generated from a fixed seed and written into `data/demo`. This guarantees reproducibility on the same machine and allows golden tests to assert metrics within one basis point. The data is clearly documented as deterministic demo data, not live market truth.

## ADR-003: Live mode is honest-first

Polygon, NewsAPI, and OpenAI integrations are server-side only. If a service is missing credentials, stale, rate-limited, or unavailable, the backend emits degraded health and the frontend surfaces that state instead of pretending the feed is fresh.

## ADR-004: Shared contracts are kept lightweight

TypeScript contracts in `packages/shared` define core enums and response shapes used by the frontend. The backend mirrors those contracts with Pydantic models. This keeps coupling manageable while still providing strong typing at the API boundary.

## ADR-005: PostgreSQL is the default persistence target

The runtime stack uses PostgreSQL to satisfy the persistence requirement for bars, news, signals, backtests, alerts, audit events, and exported reports. Tests may use isolated temporary databases where appropriate, but the primary deployment target remains PostgreSQL.

## ADR-006: No auto-trading and no secret exposure

No order-routing or broker execution code is included. API keys are never exposed to the browser. OpenAI is used only for server-side enrichment and report-quality text generation, never as a price-prediction oracle.

## ADR-007: Performance metrics are reported honestly

Targets from the report and proposal such as Sharpe, drawdown, and TCA improvement are treated as objectives, not guaranteed claims. Generated artefacts record achieved metrics exactly as measured by the demo engine.

## ADR-008: Optional providers degrade instead of blocking the app

Alpaca, FRED, SEC EDGAR, Finnhub, Alpha Vantage, FMP, Clerk, and Resend are added through a provider registry. Missing keys produce disabled or degraded status rows and the app continues in local-first demo/guest mode. Remote monitoring and analytics providers are intentionally outside the main build to avoid trial expiry and privacy confusion.

## ADR-009: Macro and filings are context, not prediction

The macro regime layer and SEC filing/event intelligence can add explanation and risk context to signals, but they do not become black-box price forecasts or override the deterministic signal engine.

## ADR-010: Verification paths avoid high-frequency audit writes

Dashboard watchlists, scanner rows, and WebSocket snapshots compute explainable signals without persisting every read-only refresh. Deliberate asset-detail, report, and recommendation paths still persist signals and audit entries. This keeps UI smoke tests and daily use responsive while preserving recommendation coverage.

## ADR-011: Release packaging uses one validated implementation

The shell and PowerShell release scripts delegate to `scripts/package_release.py`. This prevents exclusion-list drift and keeps `.env`, `.env.*`, local databases, build outputs, Playwright traces/reports, and other runtime junk out of release ZIPs.

## ADR-012: Add a supervisor launchpad instead of hiding demo flow in docs

The `/demo` route gives assessors a safe, guided path through the strongest working features. This reduces presentation risk without adding fake data or changing the decision-support boundary.

## ADR-013: Improve perceived local speed with demo response caching

Demo dashboard responses use a short in-memory TTL cache. Live mode remains uncached at this layer so freshness and degraded-state reporting stay honest.

## ADR-014: Add assessment polish as explainability, not fake certainty

The v3 enhancement layer adds readiness scoring, data-quality scoring, signal waterfalls, replay scenarios, portfolio heatmaps, and robustness summaries. These features are deliberately framed as decision-support evidence and demo assurance; they do not manufacture performance claims or let an LLM directly decide BUY/SELL/HOLD actions.

## ADR-015: Keep the local UI fast when live infrastructure is slow

Live mode now prefers fast local/demo snapshots for first paint, then refreshes live context in the background with visible fallback notices. In development, an unreachable PostgreSQL service fails fast and falls back to the local SQLite database so the app remains demonstrable instead of hanging on startup.

## ADR-015: Critical live failures revert to Demo mode

If critical live providers such as Polygon market data or NewsAPI are offline, degraded, or unreachable, the frontend writes the shared market mode back to `demo` and shows a visible fallback notice. This keeps the app usable for assessment and daily research while still making the live failure explicit.

## ADR-016: Demo-first startup with live opt-in

Fresh browser sessions default to `demo` so the first run is deterministic, safe, and fast for assessment. Live mode remains one click away and is clearly labelled with provider health, cached-data, and degraded-state information.

## ADR-017: Extra product features must strengthen evidence, not trading authority

The governance comparison, universe builder, data coverage map, strategy matrix, chart UX upgrades, offline banner, and read-only research assistant are intentionally framed as research, explainability, and operational evidence. They do not add broker execution, hidden optimisation claims, or LLM-driven price prediction.

## ADR-018: TradingView-style upgrades are safe local research modules

The terminal workspace, Pine-lite strategy builder, advanced alerts, replay lab, tear sheets, event calendar, and ranked opportunity radar are implemented as deterministic decision-support views. They help users research, compare, prototype, and explain ideas, but they do not replace the governed signal engine, do not execute trades, and do not claim exact parity with proprietary platforms.

## ADR-019: Advanced requests are consolidated into a Research Toolkit

The final premium-app additions are exposed through `/pro-terminal` as fast deterministic research modules. This avoids slowing the dashboard, keeps the app demonstrable, and preserves assessment safety: portfolio pies are paper-only, social/copy features become strategy-profile research, AI features are explanatory only, and API guidance states that no further keys are required.
