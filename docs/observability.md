# Observability

Observability is local-first in this build.

## Local Diagnostics

Remote monitoring is not part of the current application. Diagnostics use backend logs, frontend console output during development, automated test output, generated screenshots, and package-validation logs.

Product analytics are intentionally not enabled in the current local-first build. No secret values, raw API keys, or private `.env` content should ever be logged or sent to telemetry.
