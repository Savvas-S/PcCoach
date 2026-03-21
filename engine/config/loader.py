"""YAML configuration loading, validation, and caching.

Loads profiles.yaml and hardware_tiers.yaml once, caches results.
All configuration is immutable after load.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_CONFIG_DIR = Path(__file__).parent

# All 8 core categories that a build profile must allocate budget for
_REQUIRED_CATEGORIES = frozenset(
    {"cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooling"}
)

# All valid goal names (must match frontend/backend enums)
_VALID_GOALS = frozenset(
    {
        "high_end_gaming",
        "mid_range_gaming",
        "low_end_gaming",
        "light_work",
        "heavy_work",
        "designer",
        "architecture",
    }
)


@dataclass(frozen=True)
class Profile:
    """A build strategy profile for a specific goal."""

    goal: str
    description: str
    family_preference: list[str]
    selection_order: list[str]
    budget_allocation: dict[str, int]
    priority_specs: dict[str, dict[str, float]]
    tier_guidance: dict[str, dict[str, str]]


@dataclass(frozen=True)
class TierConfig:
    """Hardware tier rankings for scoring."""

    gpu_tiers: dict[str, int]
    cpu_gaming_tiers: dict[str, int]
    cpu_workstation_tiers: dict[str, int]
    chipset_rank: dict[str, int]


# ---------------------------------------------------------------
# Budget range → EUR mapping
# ---------------------------------------------------------------

BUDGET_RANGES: dict[str, tuple[float, float]] = {
    "0_1000": (0.0, 1000.0),
    "1000_1500": (1000.0, 1500.0),
    "1500_2000": (1500.0, 2000.0),
    "2000_3000": (2000.0, 3000.0),
    "over_3000": (3000.0, 5000.0),
}


def budget_range_to_eur(budget_range: str) -> tuple[float, float]:
    """Convert budget range key to (min, max) EUR tuple."""
    if budget_range not in BUDGET_RANGES:
        raise ValueError(f"Unknown budget range: {budget_range}")
    return BUDGET_RANGES[budget_range]


# ---------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_all_profiles() -> dict[str, Profile]:
    """Load and validate all profiles from YAML. Cached."""
    path = _CONFIG_DIR / "profiles.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)

    profiles_raw = raw.get("profiles", {})
    if not profiles_raw:
        raise ValueError("profiles.yaml: no profiles found")

    profiles: dict[str, Profile] = {}
    for goal, data in profiles_raw.items():
        _validate_profile(goal, data)
        profiles[goal] = Profile(
            goal=goal,
            description=data.get("description", ""),
            family_preference=data["family_preference"],
            selection_order=data["selection_order"],
            budget_allocation=data["budget_allocation"],
            priority_specs=data.get("priority_specs", {}),
            tier_guidance=data.get("tier_guidance", {}),
        )

    # Check all valid goals have profiles
    missing = _VALID_GOALS - set(profiles.keys())
    if missing:
        raise ValueError(f"profiles.yaml: missing profiles for goals: {missing}")

    return profiles


def _validate_profile(goal: str, data: dict[str, Any]) -> None:
    """Validate a single profile's structure and constraints."""
    if "family_preference" not in data:
        raise ValueError(f"Profile '{goal}': missing family_preference")
    if "selection_order" not in data:
        raise ValueError(f"Profile '{goal}': missing selection_order")
    if "budget_allocation" not in data:
        raise ValueError(f"Profile '{goal}': missing budget_allocation")

    alloc = data["budget_allocation"]
    alloc_total = sum(alloc.values())
    if abs(alloc_total - 100) > 2:
        raise ValueError(
            f"Profile '{goal}': budget_allocation sums to {alloc_total}, "
            f"expected ~100"
        )

    # All 8 categories must have budget allocation
    missing_cats = _REQUIRED_CATEGORIES - set(alloc.keys())
    if missing_cats:
        raise ValueError(
            f"Profile '{goal}': missing budget_allocation for {missing_cats}"
        )

    # Selection order must cover all required categories
    order_set = set(data["selection_order"])
    missing_order = _REQUIRED_CATEGORIES - order_set
    if missing_order:
        raise ValueError(
            f"Profile '{goal}': missing from selection_order: {missing_order}"
        )


def load_profile(goal: str) -> Profile:
    """Load a build profile by goal name."""
    profiles = _load_all_profiles()
    if goal not in profiles:
        raise ValueError(
            f"Unknown goal '{goal}'. Valid: {sorted(profiles.keys())}"
        )
    return profiles[goal]


def get_all_profiles() -> dict[str, Profile]:
    """Get all loaded profiles."""
    return _load_all_profiles()


# ---------------------------------------------------------------
# Hardware tier loading
# ---------------------------------------------------------------


@lru_cache(maxsize=1)
def load_tiers() -> TierConfig:
    """Load and validate hardware tiers from YAML. Cached."""
    path = _CONFIG_DIR / "hardware_tiers.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)

    required = {"gpu_tiers", "cpu_gaming_tiers", "cpu_workstation_tiers", "chipset_rank"}
    missing = required - set(raw.keys())
    if missing:
        raise ValueError(f"hardware_tiers.yaml: missing sections: {missing}")

    return TierConfig(
        gpu_tiers=raw["gpu_tiers"],
        cpu_gaming_tiers=raw["cpu_gaming_tiers"],
        cpu_workstation_tiers=raw["cpu_workstation_tiers"],
        chipset_rank=raw["chipset_rank"],
    )


def get_gpu_tier(model: str, tiers: TierConfig | None = None) -> int | None:
    """Look up GPU tier rank by model substring match."""
    if tiers is None:
        tiers = load_tiers()
    return _fuzzy_tier_lookup(model, tiers.gpu_tiers)


def get_cpu_gaming_tier(model: str, tiers: TierConfig | None = None) -> int | None:
    """Look up CPU gaming tier rank by model substring match."""
    if tiers is None:
        tiers = load_tiers()
    return _fuzzy_tier_lookup(model, tiers.cpu_gaming_tiers)


def get_cpu_workstation_tier(
    model: str, tiers: TierConfig | None = None
) -> int | None:
    """Look up CPU workstation tier rank by model substring match."""
    if tiers is None:
        tiers = load_tiers()
    return _fuzzy_tier_lookup(model, tiers.cpu_workstation_tiers)


def get_chipset_rank(chipset: str, tiers: TierConfig | None = None) -> int | None:
    """Look up chipset rank. Strips common prefixes like 'AMD ' or 'Intel '."""
    if tiers is None:
        tiers = load_tiers()
    # Strip vendor prefix (e.g. "AMD B650" → "B650")
    clean = chipset
    for prefix in ("AMD ", "Intel "):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
    return tiers.chipset_rank.get(clean)


def _fuzzy_tier_lookup(model: str, tier_map: dict[str, int]) -> int | None:
    """Match a product model string against tier map keys.

    Tries exact match first, then substring containment.
    Returns the tier rank or None if no match.
    """
    model_lower = model.lower()

    # Exact match (case-insensitive)
    for tier_key, rank in tier_map.items():
        if tier_key.lower() == model_lower:
            return rank

    # Substring match — model contains the tier key
    for tier_key, rank in tier_map.items():
        if tier_key.lower() in model_lower:
            return rank

    # Reverse — tier key contains model
    for tier_key, rank in tier_map.items():
        if model_lower in tier_key.lower():
            return rank

    return None
