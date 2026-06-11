# Working Notes For Future Contributors

## Product Intent

Markets Strategy Copilot is a reviewer-friendly research application, not an execution engine. Every change should preserve explainability, deterministic demo behaviour, and honest error states.

## Ground Rules

- Do not add broker execution or simulated order routing dressed up as live trading.
- Keep all third-party API access server-side.
- Preserve the distinction between `demo` and `live` modes.
- When a metric is not met, update artefacts and docs with the real value rather than smoothing it over.
- Audit logging is not optional. New recommendation paths must emit audit entries.
- If live data is stale or missing, prefer `HOLD` / `NO_SIGNAL` and a visible warning.

## Codebase Expectations

- Frontend follows Next.js App Router conventions.
- Backend uses small deterministic services with pure-function cores where possible.
- Indicators must stay consistent between chart display, signal generation, and backtesting.
- New pages should preserve the premium dark visual language already established.
