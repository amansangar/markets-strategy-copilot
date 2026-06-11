# Requirements Traceability

This document maps the attached interim report and proposal into implementation checkpoints for this repository. The report and proposal are treated as hard requirements and assessment constraints.

## Extracted Hard Requirements

| Requirement ID | Extracted requirement | Source |
| --- | --- | --- |
| HR-01 | Cover at least four assets from different classes | Proposal + Interim report objectives |
| HR-02 | Provide deterministic seeded demo mode reproducible within 1 bp on repeated runs on the same machine | Proposal + Interim report objectives |
| HR-03 | Support live mode with honest status reporting and public-data adapters | Proposal |
| HR-04 | Generate explainable recommendations with reason codes, headlines used, and policy outcomes | Proposal + Interim report |
| HR-05 | Reach 100% audit coverage for recommendation evidence | Proposal + Interim report |
| HR-06 | Include TCA with gross vs net reporting and turnover-waste comparison | Proposal + Interim report |
| HR-07 | Export a concise PDF investment note with rationale, risk, costs, and citations | Proposal + Interim report |
| HR-08 | Run locally with Docker Compose and clear README / user guide / demo script | Proposal deliverables |
| HR-09 | Demonstrate walk-forward evaluation with fees and slippage and report Sharpe / drawdown honestly | Proposal + Interim report |
| HR-10 | Complete demo flow in under 60 seconds on standard lab hardware where practical | Proposal + Interim report |

## Implementation Mapping

| Requirement | Planned implementation | Evidence |
| --- | --- | --- |
| HR-01 | `data/demo/symbols.json` plus multi-asset dashboards, scanner, and backtests | UI screenshots, seeded metrics JSON |
| HR-02 | Fixed-seed generator in `scripts/generate_demo_data.py` and golden tests | `artefacts/seeded_metrics.json`, backend tests |
| HR-03 | FastAPI live service adapters with stale-data detection and UI health badges | settings page, API status response |
| HR-04 | Deterministic signal engine with reason codes and risk flags | signal card, audit extract |
| HR-05 | audit events persisted for every recommendation path | `artefacts/audit-log-extract.json`, tests |
| HR-06 | TCA module applied in backtests and note export | strategy tester, PDF, metrics JSON |
| HR-07 | report service writing PDFs to `artefacts/exports` | sample PDF |
| HR-08 | root Docker Compose, README, `docs/user-guide.md`, `docs/demo-script.md` | repository artefacts |
| HR-09 | walk-forward engine with next-bar execution and ablation switches | strategy tester, metrics JSON |
| HR-10 | demo-first architecture with repo-seeded data and lightweight services | supervisor demo script |

## Honest Status Reporting

Targets in the report such as Sharpe `>= 0.8`, max drawdown `<= 15%`, 98% alignment quality, and TCA waste reduction `>= 20%` are treated as evaluation objectives. The implementation records actual results in artefacts rather than claiming success in advance.

## V2 Upgrade Coverage

| Area | Implementation evidence |
| --- | --- |
| Multi-provider data layer | Provider registry, adapter interface, provider matrix API, Settings matrix UI |
| Macro regime | FRED-style deterministic macro snapshot, dashboard macro strip, signal reason contribution |
| SEC filings/event intelligence | Filing timeline API/UI, digest, risk/event flags |
| Paper portfolio | `/portfolio` route with local simulated positions, orders, journal, Alpaca paper readiness |
| Workspace | `/workspace` route with guest/local saved watchlists, scanners, chart layouts, notes, report history |
| Alerts upgrade | Alert center endpoint, delivery channel state, delivery log, supported multi-factor alert types |
| Signal change / replay | Signal-diff endpoint/UI and replay endpoint/controls with lookahead-guard language |
| Security / licensing / observability | Provider, licensing, security, and observability docs plus packaging exclusions |

## Advanced Research-Terminal Enhancement Coverage

| Enhancement | Implementation evidence |
| --- | --- |
| Pine Script-style strategy builder | `/strategy-builder`, `/api/v1/strategy-builder/{symbol}`, rule evaluation endpoint |
| Multi-chart layout | `/terminal`, `/api/v1/terminal/multi-chart`, multi-asset chart cards |
| Drawing tools and saved chart layouts | `/terminal`, `/api/v1/chart-workspace/{symbol}`, auto support/resistance/trendline/fib overlays |
| Advanced alert builder | `/alert-builder`, `/api/v1/alerts/builder`, cooldown and delivery-policy templates |
| Full market replay mode | `/replay-lab`, `/api/v1/replay-lab/{symbol}`, cursor, events, signal timeline |
| Custom scanner columns | `/opportunities`, `/api/v1/scanner/columns`, selectable columns and saved presets |
| Signal markers and pattern context | `/terminal`, `/replay-lab`, `/api/v1/patterns/{symbol}` |
| Comparison/correlation mode | `/terminal`, `/api/v1/compare`, ranked correlation pairs |
| Economic and earnings calendar | `/events`, `/api/v1/events/calendar`, macro, earnings, filings, news events |
| Automated support/resistance and confluence | `/terminal`, `/api/v1/patterns/{symbol}`, levels and multi-timeframe confluence |
| Tear sheets and macro dashboard context | `/tear-sheet`, `/events`, macro sensitivity and fundamentals proxy |
| Questions over filings/news with citations | `/assistant` plus existing server-side research assistant |
| Ranked opportunity lists | `/opportunities`, `/api/v1/opportunities/ranked`, why-ranked explanations |

## Advanced Research Console

The `/pro-terminal` page and `/api/v1/pro-terminal` endpoint provide a single fast evidence console for the additional research-platform ideas requested from Trading 212, TradingView, Robinhood, eToro, Interactive Brokers, Saxo, Coinbase, Webull, Moomoo, Koyfin, and Bloomberg-style inspiration. The console keeps the project boundary intact: modules are implemented as research, simulation, education, paper-portfolio, provider-status, or explainability tools, with no real-money execution.

| Final feature area | Evidence |
| --- | --- |
| Portfolio pies, paper allocation, rebalance explainers | `/pro-terminal` portfolio pie cards and risk notes |
| Market heatmap, unusual activity, breadth, sector rotation | `/pro-terminal` heatmap, discovery cards, breadth and rotation payloads |
| Risk navigator, stress testing, risk budgeting | `/pro-terminal` risk navigator and stress-test scenarios |
| Learning centre, glossary, beginner/advanced mode | `/pro-terminal` learning + lineage cards and global status strip |
| Source confidence, data lineage, compliance mode | `/pro-terminal` lineage payload, requirements traceability, provider status |
| Evidence pack and report workflow | `/reports`, `artefacts/`, safe packaging scripts |
