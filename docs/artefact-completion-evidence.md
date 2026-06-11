# Artefact Completion Evidence

Target rubric band: Exceptional / 10.

Markets Strategy Copilot is delivered as a local-first decision-support and research artefact. It preserves the original project boundary: no real-money execution, no hidden black-box price prediction, deterministic demo behaviour, honest degraded states, and auditable recommendations.

## Evidence Checklist

| Requirement | Evidence | Status |
| --- | --- | --- |
| Deterministic demo mode | `/`, `/asset/SPY`, `artefacts/seeded_metrics.json`, `artefacts/screenshots/final-current-fullpages-*` | Complete with demo evidence |
| Live mode with graceful degradation | `/settings`, `/api/v1/providers/checks`, `artefacts/provider-health-live.json` | Complete with live fallback |
| Provider health transparency | `/settings`, `artefacts/provider-health-demo.json`, `artefacts/provider-health-live.json` | Complete |
| Polygon market data | Provider matrix and architecture docs describe Polygon REST live refresh plus backend WebSocket snapshots | Complete with honest implementation wording |
| NewsAPI and enrichment | `/asset/SPY`, `/reports`, provider budget notes and health evidence | Complete with live fallback |
| OpenAI copilot layer | `/assistant`, `/reports`, server-side provider status | Complete with live fallback |
| Technical indicators | `/asset/SPY`, `/`, `docs/indicators.md` | Complete |
| BUY / HOLD / SELL / NO SIGNAL logic | Dashboard and asset signal panels, backend signal tests | Complete |
| Explainable signals | Signal card, signal waterfall, audit trail, reason cards | Complete |
| Backtesting and walk-forward | `/strategy-tester`, `artefacts/strategy-benchmark-comparison.json`, `artefacts/ablation-results.json` | Complete with demo evidence |
| TCA and costs | `/strategy-tester`, `/reports`, `artefacts/ablation-results.json` | Complete |
| Paper portfolio | `/portfolio`, local portfolio summary and risk heatmap | Complete with demo evidence |
| Alerts | `/alerts`, delivery log and browser/email configuration states | Complete |
| Workspace research notes | `/workspace`, saved watchlists/scanners/layouts/notes | Complete |
| SEC filings and events | `/asset/SPY`, `/events`, filing timeline and risk flags | Complete |
| Macro regime | Dashboard macro strip, asset macro contribution, FRED provider docs | Complete |
| PDF investment note export | `/reports`, `artefacts/exports/SPY-investment-note-*.pdf` | Complete |
| Audit log extract | `/asset/SPY`, `artefacts/audit-log-extract.json` | Complete |
| Final UI screenshots | `artefacts/screenshots/final-current-fullpages-*` | Complete |
| Clean release packaging | `scripts/package_release.py`, `artefacts/release-validation.json`, release ZIP | Complete |

## Extra Features Beyond The Original Plan

| Extra area | Evidence | Status |
| --- | --- | --- |
| Advanced Research Toolkit | `/pro-terminal`, `/terminal`, `/replay-lab`, `/tear-sheet` | Optional / extra |
| Strategy builder and matrix | `/strategy-builder`, `/strategy-matrix` | Optional / extra |
| Universe and coverage tools | `/universe`, `/coverage` | Optional / extra |
| Governance and quality views | `/governance`, `/quality` | Optional / extra |
| Provider fallback priority | `/settings`, provider failover timeline | Complete |
| Beginner setup and walkthrough | `/setup`, first-run tutorial | Complete |

## Validation Commands

Use these from the repository root:

```powershell
python scripts/generate_artefacts.py
npm run screenshots:final
python scripts/run_checks.py
python scripts/run_smoke.py demo
python scripts/package_release.py
```

Live smoke checks can be run with configured provider keys:

```powershell
python scripts/run_smoke.py live
```

## Packaging Safety Summary

The release packager excludes `.env`, `.env.*`, `.git`, `node_modules`, `.next`, local databases, caches, logs, traces, videos, old screenshots, old releases, virtual environments, and build artefacts such as `*.tsbuildinfo` and `*.egg-info`. It fails if the final PDF, seeded metrics, audit extract, provider health artefacts, strategy comparison artefacts, release validation, completion evidence, or final screenshots are missing.

## Honest Limitations

Polygon is implemented as REST live refresh plus local backend WebSocket snapshot broadcasting. It should not be described as a direct Polygon WebSocket stream unless that is implemented later. Live provider results can be rate-limited or degraded by free-tier limits, so the app defaults to deterministic demo mode for first-time and assessment runs.
