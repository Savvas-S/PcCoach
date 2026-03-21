"""Greedy build selection algorithm with budget balancing.

This is the heart of the engine. It orchestrates dedup, family computation,
scoring, selection, optimization, and validation to produce a complete build.
"""

from __future__ import annotations

import logging

from engine.config.loader import (
    Profile,
    budget_range_to_eur,
    load_profile,
    load_tiers,
)
from engine.core.dedup import deduplicate
from engine.core.families import (
    FAMILY_INDEPENDENT,
    compute_families,
    get_family_independent_products,
)
from engine.core.notes_parser import parse_notes
from engine.core.optimizer import (
    find_downgrade_candidate,
    find_upgrade_candidate,
    optimize_budget,
)
from engine.core.scorer import score_products
from engine.core.validator import validate_build
from engine.models.result import BuildEngineResult, SelectedComponent
from engine.models.types import (
    CompatibilityFamily,
    NotesPreferences,
    ProductRecord,
    ScoredProduct,
)
from engine.ports import CatalogPort

log = logging.getLogger(__name__)

# Core categories that must be in every build (unless user has existing parts)
_CORE_CATEGORIES = frozenset(
    {"cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooling"}
)

# Peripheral categories (only if include_peripherals)
_PERIPHERAL_CATEGORIES = frozenset({"monitor", "keyboard", "mouse"})

# Budget target as fraction of max
_BUDGET_TARGET_RATIO = 0.85

# Max flex for a single category (fraction of remaining budget)
_CATEGORY_FLEX = 1.5


async def run_selection(
    *,
    goal: str,
    budget_range: str,
    form_factor: str = "atx",
    cpu_brand: str = "no_preference",
    gpu_brand: str = "no_preference",
    cooling_preference: str = "no_preference",
    existing_parts: list[str],
    notes: str | None = None,
    catalog: CatalogPort,
    include_peripherals: bool = False,
) -> BuildEngineResult:
    """Run the complete build selection algorithm.

    Steps:
    1. Load profile and budget
    2. Fetch and deduplicate products
    3. Compute compatibility families
    4. Select best family
    5. Compute per-category budgets
    6. Score candidates per category
    7. Greedy selection in priority order
    8. Budget optimization
    9. Identify upgrade/downgrade candidates
    10. Validate and resolve listings
    """
    # Step 1: Load config
    profile = load_profile(goal)
    budget_min, budget_max = budget_range_to_eur(budget_range)
    budget_target = budget_max * _BUDGET_TARGET_RATIO
    tiers = load_tiers()
    notes_prefs = parse_notes(notes)

    # Determine required categories
    excluded = set(existing_parts)
    required = _CORE_CATEGORIES - excluded
    if include_peripherals:
        required |= _PERIPHERAL_CATEGORIES - excluded

    log.info(
        "Selection: goal=%s budget=%s (€%.0f–€%.0f) target=€%.0f "
        "required=%s excluded=%s",
        goal, budget_range, budget_min, budget_max, budget_target,
        sorted(required), sorted(excluded),
    )

    # Step 2: Fetch & deduplicate
    all_products = await catalog.get_all_products()
    products = deduplicate(all_products)
    log.info("Fetched %d products, %d after dedup", len(all_products), len(products))

    # Step 3: Compute compatibility families
    families = compute_families(
        products, form_factor, cpu_brand, cooling_preference
    )
    independent = get_family_independent_products(products)

    # Apply GPU brand filter to independent pool
    if gpu_brand != "no_preference" and "gpu" in independent:
        brand_lower = gpu_brand.lower()
        # Map preference to brand names
        brand_map = {"nvidia": "nvidia", "amd": "amd"}
        target_brand = brand_map.get(brand_lower, brand_lower)
        independent["gpu"] = [
            g for g in independent["gpu"]
            if g.brand.lower() == target_brand
        ] or independent["gpu"]  # fallback to all if filter empties

    if not families:
        raise ValueError("No compatible product families found for the given filters")

    # Step 4: Select best family
    family = _select_family(families, profile, budget_target)
    log.info("Selected family: %s", family.name)

    # Step 5: Compute per-category budgets
    cat_budgets = _compute_category_budgets(
        profile, budget_target, required, excluded
    )

    # Step 6: Score candidates per category
    ranked: dict[str, list[ScoredProduct]] = {}
    for category in required:
        if category in FAMILY_INDEPENDENT:
            pool = independent.get(category, [])
        else:
            pool = family.pool(category)

        if not pool:
            log.warning("No products available for category: %s", category)
            continue

        ranked[category] = score_products(
            pool, category, cat_budgets.get(category, 0),
            profile, budget_range, goal, notes_prefs, tiers,
        )

    # Step 7: Greedy selection
    selections: dict[str, ProductRecord] = {}
    remaining = budget_target

    for category in profile.selection_order:
        if category not in required or category not in ranked:
            continue

        candidates = ranked[category]
        cat_budget = cat_budgets.get(category, 0)

        selected = _select_best_within_budget(
            candidates, remaining, cat_budget
        )
        if selected:
            selections[category] = selected
            remaining -= selected.best_price

    # Check for missing categories — try to fill with cheapest option
    for category in required:
        if category not in selections and category in ranked:
            cheapest = min(
                (s.product for s in ranked[category]),
                key=lambda p: p.best_price,
                default=None,
            )
            if cheapest:
                selections[category] = cheapest
                remaining -= cheapest.best_price

    # Step 8: Optimize budget
    selections = optimize_budget(
        selections, ranked, budget_target, budget_max, profile
    )

    # Step 9: Identify upgrade/downgrade candidates
    upgrade_info = find_upgrade_candidate(selections, ranked, profile)
    downgrade_info = find_downgrade_candidate(selections, ranked, profile)

    # Step 10: Validate
    issues = validate_build(selections)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        log.warning("Validation errors: %s", errors)
        # Try to fix by swapping offending components
        selections = _try_fix_validation(selections, ranked, errors)

    # Build result
    total = sum(p.best_price for p in selections.values())
    utilization = total / budget_max if budget_max > 0 else 0

    components: dict[str, SelectedComponent] = {}
    for cat, product in selections.items():
        listing = product.best_listing
        components[cat] = SelectedComponent(
            component_id=listing.component_id,
            category=cat,
            brand=product.brand,
            model=product.model,
            specs=product.specs,
            price_eur=listing.price_eur,
            store=listing.store,
            affiliate_url=listing.affiliate_url,
        )

    upgrade_comp = None
    upgrade_cat = None
    if upgrade_info:
        u_cat, u_prod = upgrade_info
        u_listing = u_prod.best_listing
        upgrade_cat = u_cat
        upgrade_comp = SelectedComponent(
            component_id=u_listing.component_id,
            category=u_cat,
            brand=u_prod.brand,
            model=u_prod.model,
            specs=u_prod.specs,
            price_eur=u_listing.price_eur,
            store=u_listing.store,
            affiliate_url=u_listing.affiliate_url,
        )

    downgrade_comp = None
    downgrade_cat = None
    if downgrade_info:
        d_cat, d_prod = downgrade_info
        d_listing = d_prod.best_listing
        downgrade_cat = d_cat
        downgrade_comp = SelectedComponent(
            component_id=d_listing.component_id,
            category=d_cat,
            brand=d_prod.brand,
            model=d_prod.model,
            specs=d_prod.specs,
            price_eur=d_listing.price_eur,
            store=d_listing.store,
            affiliate_url=d_listing.affiliate_url,
        )

    # Metadata for debugging
    metadata = {
        "family": family.name,
        "budget_target": budget_target,
        "budget_max": budget_max,
        "notes_prefs": {
            "brands": notes_prefs.brands,
            "resolution": notes_prefs.resolution,
            "keywords": notes_prefs.keywords,
        } if notes_prefs.brands or notes_prefs.resolution else {},
        "validation_warnings": [
            i.message for i in issues if i.severity == "warning"
        ],
    }

    return BuildEngineResult(
        components=components,
        upgrade_candidate=upgrade_comp,
        downgrade_candidate=downgrade_comp,
        upgrade_category=upgrade_cat,
        downgrade_category=downgrade_cat,
        family_used=family.name,
        total_price_eur=total,
        budget_utilization=utilization,
        metadata=metadata,
    )


# ---------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------


def _select_family(
    families: list[CompatibilityFamily],
    profile: Profile,
    budget_target: float,
) -> CompatibilityFamily:
    """Select the best family based on profile preference and feasibility."""
    # Try profile-preferred families first
    family_map = {f.name: f for f in families}

    for pref_name in profile.family_preference:
        if pref_name in family_map:
            family = family_map[pref_name]
            if _family_feasible(family, budget_target):
                return family

    # Fallback: cheapest family (even if over feasibility threshold)
    return min(families, key=_family_floor_cost)


def _family_feasible(family: CompatibilityFamily, budget_target: float) -> bool:
    """Quick check: can we afford the cheapest CPU + mobo + RAM from this family?"""
    try:
        cheapest_cpu = min(p.best_price for p in family.cpus)
        cheapest_mobo = min(p.best_price for p in family.motherboards)
        cheapest_ram = min(p.best_price for p in family.ram)
        floor = cheapest_cpu + cheapest_mobo + cheapest_ram
        return floor <= budget_target * 0.40
    except ValueError:
        return False


def _family_floor_cost(family: CompatibilityFamily) -> float:
    """Minimum cost for family-bound components."""
    try:
        return (
            min(p.best_price for p in family.cpus)
            + min(p.best_price for p in family.motherboards)
            + min(p.best_price for p in family.ram)
        )
    except ValueError:
        return float("inf")


def _compute_category_budgets(
    profile: Profile,
    budget_target: float,
    required: set[str],
    excluded: set[str],
) -> dict[str, float]:
    """Compute per-category budget from profile allocation.

    Redistributes budget from excluded categories proportionally.
    """
    alloc = profile.budget_allocation
    active_cats = {c for c in alloc if c in required}
    excluded_pct = sum(alloc.get(c, 0) for c in excluded if c in alloc)

    budgets: dict[str, float] = {}
    total_active_pct = sum(alloc[c] for c in active_cats)

    for cat in active_cats:
        base_pct = alloc[cat]
        # Redistribute excluded budget proportionally
        if total_active_pct > 0 and excluded_pct > 0:
            bonus_pct = excluded_pct * (base_pct / total_active_pct)
            base_pct += bonus_pct
        budgets[cat] = budget_target * base_pct / 100.0

    return budgets


def _select_best_within_budget(
    candidates: list[ScoredProduct],
    remaining_budget: float,
    category_budget: float,
) -> ProductRecord | None:
    """Select the best-scoring product that fits within budget constraints."""
    # Allow spending up to FLEX times the category budget, but not more
    # than remaining total budget
    max_spend = min(remaining_budget, category_budget * _CATEGORY_FLEX)

    for scored in candidates:
        if scored.product.best_price <= max_spend:
            return scored.product

    # If nothing fits within flex, take the cheapest available
    if candidates:
        cheapest = min(candidates, key=lambda s: s.product.best_price)
        if cheapest.product.best_price <= remaining_budget:
            return cheapest.product

    return None


def _try_fix_validation(
    selections: dict[str, ProductRecord],
    ranked: dict[str, list[ScoredProduct]],
    errors: list,
) -> dict[str, ProductRecord]:
    """Attempt to fix validation errors by swapping components."""
    # Simple strategy: for each erroring category, try next-best candidate
    for error in errors:
        cat = error.category
        if cat not in ranked:
            continue
        current = selections.get(cat)
        for scored in ranked[cat]:
            if current and scored.product.id != current.id:
                selections[cat] = scored.product
                # Re-validate
                new_issues = validate_build(selections)
                new_errors = [i for i in new_issues if i.severity == "error"]
                if not any(e.category == cat for e in new_errors):
                    break
                else:
                    # Revert if it didn't help
                    selections[cat] = current

    return selections
