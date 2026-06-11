# Testing

This project uses a layered verification flow so demo mode stays deterministic while live integrations are checked separately and safely.

## Main Check

Run from the repo root:

```powershell
python scripts/run_checks.py
```

This runs:

- Backend pytest suite
- Frontend ESLint
- Frontend TypeScript typecheck
- Frontend production build
- Playwright desktop smoke tests

The smoke path also exercises the assessment-polish layer: readiness cards, provider fallback cards, data-quality scoring, signal waterfall, replay scenarios, command palette navigation, portfolio heatmap, and backtest robustness after a run.

## Demo Smoke

```powershell
python scripts/run_smoke.py demo
```

Demo smoke tests use seeded data and should not require external API keys for the core UI paths.

## Live Smoke

```powershell
python scripts/run_smoke.py live
```

Live smoke keeps UI assertions non-brittle and adds a provider-health endpoint check. It reports provider statuses only; it must not print or expose key values.

## Browser Coverage

Playwright covers these unauthenticated routes:

- `/`
- `/asset/SPY`
- `/scanner`
- `/strategy-tester`
- `/alerts`
- `/reports`
- `/settings`
- `/portfolio`
- `/workspace`

The Codex in-app browser is suitable for these unauthenticated routes. If Clerk sign-in is enabled, use a normal browser for hosted auth redirects and verify that guest/local mode still works when Clerk is absent.

## Artefacts

Useful screenshots are written to `artefacts/screenshots`. Temporary traces and Playwright HTML reports are written under `artefacts/playwright-results` and `artefacts/playwright-report`; these are excluded from release ZIPs.

The curated screenshot index lives in `docs/screenshots.md`. It links the latest full-page desktop/mobile route gallery and the before/after feature activation gallery.

## Packaging Safety

The packaging test and `scripts/package_release.py` validate that forbidden files are absent from the ZIP, including `.env`, `.env.*`, `.git`, `.next`, `node_modules`, local databases, caches, logs, and Playwright traces/reports.
