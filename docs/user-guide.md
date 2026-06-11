# User Guide

## What The App Does

Markets Strategy Copilot helps you analyse assets, explain current signals, review risk flags, and export investment notes. It is not an execution bot.

## Modes

- `Demo mode`: deterministic repo-seeded data for reliable demonstrations and tests
- `Live mode`: real market and news feeds when valid API keys are configured

## Main Pages

- Demo Guide: guided supervisor route, readiness checks, and demo talking points
- Pro Terminal: advanced research toolkit with portfolio pies, heatmap, risk navigator, stress tests, learning centre, data lineage, and API-key guidance
- Dashboard: market overview, watchlist, chart, signal panel, analytics tabs
- Asset Detail: deeper chart controls, news timeline, signal history, audit trail
- Scanner: filterable symbol screening with explainability
- Terminal: multi-chart workspace, comparison/correlation view, automated drawing overlays, saved layouts, and pattern confluence
- Opportunities: ranked research list with custom scanner columns and "why this ranked" explanations
- Strategy Builder: Pine-lite deterministic rule builder for safe strategy prototyping
- Strategy Tester: backtests with TCA-aware metrics and walk-forward view
- Replay Lab: historical market replay with cursor-based bars, events, and signal timeline
- Tear Sheet: asset profile, market metrics, macro sensitivity, filings, news, and fundamentals context
- Events: macro, earnings, filing, and news calendar
- Alerts: local rule monitoring and alert history
- Alert Builder: advanced explainable alert templates with cooldowns and safe delivery policies
- Reports: export and review investment notes
- Settings: service health, provider diagnostics, API status, mode, and policy summary

## Advanced Research Workflow

Use `Terminal` to compare assets and inspect automated support/resistance, then open `Opportunities` to find ranked candidates. If an idea looks useful, test the logic in `Strategy Builder`, validate it in `Strategy Tester`, and use `Replay Lab` to step through historical evidence without seeing future events. `Tear Sheet`, `Events`, and `Assistant` provide context for writing reports and explaining the recommendation.

## Exporting A PDF

1. Navigate to `Reports`.
2. Select an asset or use the current dashboard context.
3. Click `Export Investment Note`.
4. The PDF is saved to `artefacts/exports` and indexed in the backend metadata store.

## Live Mode Notes

- Add `OPENAI_API_KEY`, `POLYGON_API_KEY`, and `NEWSAPI_API_KEY` in your local `.env`.
- OpenAI enrichment is optional. If unavailable, the app falls back to technical-only mode and labels that state clearly.
- If market data becomes stale, the UI warns you and the signal engine becomes conservative.
