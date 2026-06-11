from __future__ import annotations

from functools import lru_cache

import yaml

from app.demo_store import demo_paths


@lru_cache
def load_policy() -> dict:
    path = demo_paths()["policy"]
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def evaluate_policy(
    *,
    asset_class: str,
    action: str,
    freshness_seconds: float,
    spread_bps: float,
    position_size_pct: float,
) -> tuple[bool, list[str]]:
    policy = load_policy()
    blockers: list[str] = []
    stale_limit = policy["stale_price_threshold_minutes"] * 60
    if freshness_seconds > stale_limit and action in policy["blocked_actions_when_stale"]:
        blockers.append("STALE_DATA_BLOCK")

    max_spread = policy["max_spread_bps"].get(asset_class, 10)
    if spread_bps > max_spread:
        blockers.append("SPREAD_TOO_WIDE")

    if position_size_pct > policy["max_asset_weight"]:
        blockers.append("POSITION_SIZE_CAP")

    return len(blockers) == 0, blockers
