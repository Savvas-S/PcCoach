"""Product scoring — rates products by spec, price, and tier fit.

Score formula: spec_score × 0.45 + price_score × 0.30 + tier_score × 0.25

Each score component is normalized to [0.0, 1.0].
"""

from __future__ import annotations

import math
from typing import Any

from engine.config.loader import (
    Profile,
    TierConfig,
    get_chipset_rank,
    get_cpu_gaming_tier,
    get_cpu_workstation_tier,
    get_gpu_tier,
    load_tiers,
)
from engine.models.types import NotesPreferences, ProductRecord, ScoredProduct

# Scoring weights
_W_SPEC = 0.45
_W_PRICE = 0.30
_W_TIER = 0.25

# Spec normalization ranges (used to normalize raw spec values to 0-1)
_SPEC_RANGES: dict[str, tuple[float, float]] = {
    "cores": (2.0, 24.0),
    "threads": (4.0, 48.0),
    "boost_ghz": (3.0, 6.0),
    "tdp": (45.0, 450.0),
    "vram_gb": (4.0, 32.0),
    "capacity_gb": (8.0, 4000.0),
    "speed_mhz": (2400.0, 8000.0),
    "wattage": (400.0, 1600.0),
    "read_mbps": (1000.0, 14000.0),
    "radiator_mm": (120.0, 420.0),
}

# Maximum tier rank (for normalization)
_MAX_TIER = 12


def score_products(
    products: list[ProductRecord],
    category: str,
    category_budget: float,
    profile: Profile,
    budget_range: str,
    goal: str,
    notes_prefs: NotesPreferences | None = None,
    tiers: TierConfig | None = None,
) -> list[ScoredProduct]:
    """Score and rank products for a given category.

    Args:
        products: Candidate products (already filtered by family/category).
        category: Component category (cpu, gpu, etc.).
        category_budget: Target budget for this category in EUR.
        profile: Active build profile.
        budget_range: Budget range key (for tier guidance lookup).
        goal: Build goal (for tier type selection).
        notes_prefs: User notes preferences for bonus scoring.
        tiers: Hardware tier config (auto-loaded if None).

    Returns:
        List of ScoredProduct sorted by total_score descending.
    """
    if tiers is None:
        tiers = load_tiers()

    spec_weights = profile.priority_specs.get(category, {})
    tier_targets = _parse_tier_targets(profile, budget_range, category)

    scored: list[ScoredProduct] = []
    for product in products:
        spec = _compute_spec_score(product, category, spec_weights, tiers)
        price = _compute_price_score(product.best_price, category_budget)
        tier = _compute_tier_score(product, category, tier_targets, goal, tiers)

        # Notes preference bonus (up to +0.1 on total)
        bonus = _compute_notes_bonus(product, category, notes_prefs)

        total = spec * _W_SPEC + price * _W_PRICE + tier * _W_TIER + bonus

        scored.append(
            ScoredProduct(
                product=product,
                spec_score=spec,
                price_score=price,
                tier_score=tier,
                total_score=total,
            )
        )

    scored.sort(key=lambda s: s.total_score, reverse=True)
    return scored


# ---------------------------------------------------------------
# Spec score: weighted sum of normalized spec values
# ---------------------------------------------------------------


def _compute_spec_score(
    product: ProductRecord,
    category: str,
    weights: dict[str, float],
    tiers: TierConfig,
) -> float:
    """Compute spec score as weighted sum of normalized specs."""
    if not weights:
        return 0.5  # neutral score if no weights defined

    total = 0.0
    weight_sum = 0.0

    for spec_key, weight in weights.items():
        value = _get_spec_value(product, category, spec_key, tiers)
        if value is not None:
            total += value * weight
            weight_sum += abs(weight)

    if weight_sum == 0:
        return 0.5

    # Normalize: total/weight_sum gives a value in roughly [-1, 1]
    # Map to [0, 1]
    raw = total / weight_sum
    return max(0.0, min(1.0, (raw + 1.0) / 2.0))


def _get_spec_value(
    product: ProductRecord,
    category: str,
    spec_key: str,
    tiers: TierConfig,
) -> float | None:
    """Get a normalized spec value (0-1 range) for scoring.

    Handles special computed specs like tier_rank, gaming_rank, etc.
    """
    # Special computed specs
    if spec_key == "tier_rank":
        return _get_tier_normalized(product, category, tiers)
    if spec_key == "gaming_rank":
        rank = get_cpu_gaming_tier(product.model, tiers)
        if rank is None:
            return 0.3
        return 1.0 - (rank - 1) / (_MAX_TIER - 1)
    if spec_key == "workstation_rank":
        rank = get_cpu_workstation_tier(product.model, tiers)
        if rank is None:
            return 0.3
        return 1.0 - (rank - 1) / (_MAX_TIER - 1)
    if spec_key == "chipset_rank":
        chipset = product.specs.get("chipset", "")
        rank = get_chipset_rank(chipset, tiers)
        if rank is None:
            return 0.3
        return 1.0 - (rank - 1) / 8.0
    if spec_key == "feature_score":
        # Generic feature score — use price as proxy (more expensive = more features)
        return min(1.0, product.best_price / 200.0)
    if spec_key == "efficiency_rank":
        eff = product.specs.get("efficiency", "").lower()
        ranks = {"80 plus titanium": 1.0, "80 plus platinum": 0.85,
                 "80 plus gold": 0.7, "80 plus silver": 0.5,
                 "80 plus bronze": 0.3, "80 plus": 0.2}
        for key, val in ranks.items():
            if key in eff:
                return val
        return 0.5
    if spec_key == "cooling_capacity":
        # Approximate by type and radiator size
        if product.specs.get("type") == "liquid":
            rad = _safe_float(product.specs.get("radiator_mm", "240"))
            return min(1.0, rad / 360.0)
        return 0.5  # air coolers get moderate score
    if spec_key == "noise":
        # Lower noise = better; liquid generally quieter at load
        if product.specs.get("type") == "liquid":
            return 0.7
        return 0.5
    if spec_key == "interface_rank":
        iface = product.specs.get("interface", "").lower()
        if "pcie 5.0" in iface:
            return 1.0
        if "pcie 4.0" in iface:
            return 0.7
        if "pcie 3.0" in iface:
            return 0.4
        return 0.3

    # Raw numeric spec from product.specs
    raw = product.specs.get(spec_key)
    if raw is None:
        return None

    value = _safe_float(raw)
    if value is None:
        return None

    # Normalize using known ranges
    lo, hi = _SPEC_RANGES.get(spec_key, (0.0, value * 2))
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def _get_tier_normalized(
    product: ProductRecord, category: str, tiers: TierConfig
) -> float:
    """Get normalized tier score (1.0 = best tier, 0.0 = worst)."""
    if category == "gpu":
        rank = get_gpu_tier(product.model, tiers)
    elif category == "cpu":
        rank = get_cpu_gaming_tier(product.model, tiers)
    else:
        return 0.5

    if rank is None:
        return 0.3  # unknown product gets below-average tier score
    return 1.0 - (rank - 1) / (_MAX_TIER - 1)


# ---------------------------------------------------------------
# Price score: gaussian proximity to target budget
# ---------------------------------------------------------------


def _compute_price_score(price: float, target_budget: float) -> float:
    """Score based on how close the price is to the category budget target.

    Uses a gaussian curve centered on the target. Products at ±50% of
    target still get a decent score; products way off get low scores.
    """
    if target_budget <= 0:
        return 0.5

    # Slightly under budget is better than over budget
    if price <= target_budget:
        # Under budget: gentle penalty (you're getting good value)
        sigma = target_budget * 0.5
        diff = target_budget - price
        return math.exp(-(diff ** 2) / (2 * sigma ** 2))
    else:
        # Over budget: steeper penalty
        sigma = target_budget * 0.35
        diff = price - target_budget
        return math.exp(-(diff ** 2) / (2 * sigma ** 2))


# ---------------------------------------------------------------
# Tier score: proximity to tier guidance
# ---------------------------------------------------------------


def _compute_tier_score(
    product: ProductRecord,
    category: str,
    tier_targets: list[int],
    goal: str,
    tiers: TierConfig,
) -> float:
    """Score based on how close the product is to the recommended tier.

    Products within ±1 tier of target get high scores. Products farther
    away get exponentially lower scores.
    """
    if not tier_targets:
        return 0.5  # no tier guidance for this category

    # Get product's tier
    if category == "gpu":
        product_tier = get_gpu_tier(product.model, tiers)
    elif category == "cpu":
        if goal in ("light_work", "heavy_work", "designer", "architecture"):
            product_tier = get_cpu_workstation_tier(product.model, tiers)
        else:
            product_tier = get_cpu_gaming_tier(product.model, tiers)
    else:
        return 0.5  # tier guidance only for GPU and CPU

    if product_tier is None:
        return 0.3

    # Distance to nearest target tier
    min_dist = min(abs(product_tier - t) for t in tier_targets)

    # Within ±1 tier → high score; drops off with distance
    if min_dist == 0:
        return 1.0
    elif min_dist == 1:
        return 0.8
    elif min_dist == 2:
        return 0.5
    else:
        return max(0.1, 0.5 - min_dist * 0.1)


def _parse_tier_targets(
    profile: Profile, budget_range: str, category: str
) -> list[int]:
    """Extract target tier ranks from profile's tier_guidance."""
    guidance = profile.tier_guidance.get(budget_range, {})

    if category == "gpu":
        raw = guidance.get("gpu_tier", "")
    elif category == "cpu":
        raw = guidance.get("cpu_tier", "")
    else:
        return []

    if not raw:
        return []

    # Parse "5070/5070Ti" → look up each in tier tables
    tiers_config = load_tiers()
    targets: list[int] = []
    for name in raw.split("/"):
        name = name.strip()
        if category == "gpu":
            rank = get_gpu_tier(name, tiers_config)
        else:
            rank = get_cpu_gaming_tier(name, tiers_config)
        if rank is not None:
            targets.append(rank)

    return targets


# ---------------------------------------------------------------
# Notes preference bonus
# ---------------------------------------------------------------


def _compute_notes_bonus(
    product: ProductRecord,
    category: str,
    prefs: NotesPreferences | None,
) -> float:
    """Small bonus for products matching user's notes preferences."""
    if not prefs:
        return 0.0

    bonus = 0.0
    model_lower = product.model.lower()
    brand_lower = product.brand.lower()

    # Brand match
    for brand in prefs.brands:
        if brand.lower() in brand_lower or brand.lower() in model_lower:
            bonus += 0.05
            break

    # Specific model match
    for model in prefs.specific_models:
        if model.lower() in model_lower:
            bonus += 0.08
            break

    return min(bonus, 0.1)  # cap at +0.1


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _safe_float(value: Any) -> float | None:
    """Safely convert a spec value to float."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None
