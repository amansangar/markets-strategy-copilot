from __future__ import annotations

def observability_status() -> dict:
    return {
        "localLogs": {
            "enabled": True,
            "detail": "Remote monitoring is not used in this build; keep local logs and test output for diagnostics.",
        },
        "privacy": {
            "telemetryToggleDefault": False,
            "secretFiltering": True,
            "browserSecretsRule": "Only NEXT_PUBLIC_* values are allowed in the frontend runtime.",
        },
    }
