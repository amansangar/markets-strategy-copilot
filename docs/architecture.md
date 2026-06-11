# Architecture Overview

## System Summary

Markets Strategy Copilot is a local-first monorepo with a React frontend and a FastAPI backend. It supports two operating modes:

- `demo`: deterministic seeded bars and headlines from `data/demo`
- `live`: Polygon REST live refresh plus local backend WebSocket snapshot updates, NewsAPI for headlines, OpenAI for server-side enrichment

The application is API-first. The web client consumes REST endpoints for snapshots and uses the backend WebSocket for incremental local snapshot and health updates. The current implementation does not claim a direct Polygon WebSocket subscription; it uses Polygon REST refresh with safe throttling.

## High-Level Components

### Frontend (`apps/web`)

- App Router pages for dashboard, asset detail, scanner, strategy tester, alerts, reports, and settings
- premium responsive shell with left watchlist / center chart / right signal card layout
- Lightweight Charts integration with overlay toggles and oscillator panes
- status-aware UI that surfaces demo/live mode, freshness, and degraded services

### Backend (`apps/api`)

- FastAPI routers for dashboard data, scanner results, backtests, alerts, reports, and system status
- deterministic market-engine services for indicators, signal scoring, risk policy, TCA, and backtesting
- live adapters for Polygon REST refresh, NewsAPI, and OpenAI with graceful fallbacks
- SQLAlchemy models for persistence

### Shared Contracts (`packages/shared`)

- TypeScript enums and response shapes used by the web app
- frontend validators and API-client typing

## Data Flow

1. Seed or live adapters load bars and headlines.
2. Validation checks missing values, ordering, and freshness.
3. Indicator engine computes overlays and oscillators.
4. Signal engine scores trend, momentum, volume, volatility, confluence, and news context.
5. Policy and risk layer applies caps, stale-data checks, spread checks, and drawdown guards.
6. Backtest engine simulates next-bar execution with fees, spread, and slippage.
7. Audit events are persisted for each recommendation path.
8. Report service compiles an exportable investment note PDF.

## Persistence Model

Core persisted entities:

- `symbols`
- `bars`
- `news_articles`
- `headline_enrichments`
- `signals`
- `backtest_runs`
- `backtest_trades`
- `alerts`
- `audit_events`
- `exported_reports`

## WebSocket Design

The backend exposes a WebSocket endpoint that streams:

- latest per-symbol price snapshot
- freshness and mode status
- strongest signal summaries
- alert count deltas

In demo mode the stream is deterministic and replay-safe. In live mode the stream wraps provider health and automatically flips to degraded status when feeds become stale.

## Deployment Model

- local development via Docker Compose
- PostgreSQL container for persistence
- FastAPI and Next.js containers for app services
- release ZIP excludes secrets, caches, git history, and runtime volumes
