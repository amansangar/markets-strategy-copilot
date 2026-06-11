# UI Screenshot Gallery

This repository includes a small curated screenshot set for GitHub review. Full screenshot runs, local PDFs, validation JSON, logs, and other generated evidence stay in `artefacts/` and are intentionally ignored by Git.

## Curated Screens

| Screen | Image |
| --- | --- |
| Dashboard overview | [01-dashboard-overview.jpg](screenshots/01-dashboard-overview.jpg) |
| Asset research | [02-asset-research.jpg](screenshots/02-asset-research.jpg) |
| Scanner opportunities | [03-scanner-opportunities.jpg](screenshots/03-scanner-opportunities.jpg) |
| Strategy tester | [04-strategy-tester.jpg](screenshots/04-strategy-tester.jpg) |
| Governance comparison | [05-governance-comparison.jpg](screenshots/05-governance-comparison.jpg) |
| Reports and investment notes | [06-reports-investment-notes.jpg](screenshots/06-reports-investment-notes.jpg) |
| Mobile research workflow | [07-mobile-triptych.jpg](screenshots/07-mobile-triptych.jpg) |

## Regeneration

Run `npm run screenshots:final` after starting the API and web app. The raw output is written under `artefacts/screenshots/`; copy only selected, presentation-ready images into `docs/screenshots/` before committing.
