"""Post-selection budget optimization.

After greedy selection, this module checks if there's headroom to upgrade
high-priority components or if the build is over budget and needs downgrades.
Also identifies upgrade/downgrade candidates for user suggestions.
"""

from __future__ import annotations

from engine.config.loader import Profile
from engine.models.types import ProductRecord, ScoredProduct


def optimize_budget(
    selections: dict[str, ProductRecord],
    ranked: dict[str, list[ScoredProduct]],
    budget_target: float,
    budget_max: float,
    profile: Profile,
) -> dict[str, ProductRecord]:
    """Optimize the build to better use the available budget.

    If there's headroom (>5% unused), try upgrading high-priority categories.
    If over budget_max, downgrade lowest-priority categories.

    Args:
        selections: Current selections (category → product).
        ranked: All scored candidates per category.
        budget_target: Target budget (typically budget_max × 0.85).
        budget_max: Hard budget ceiling.
        profile: Active build profile.

    Returns:
        Updated selections dict (may be the same object if no changes).
    """
    total = sum(p.best_price for p in selections.values())

    # Phase 1: Upgrade if headroom
    remaining = budget_max - total
    if remaining > budget_target * 0.05:
        selections = _try_upgrades(
            selections, ranked, remaining, profile
        )

    # Phase 2: Downgrade if over budget
    total = sum(p.best_price for p in selections.values())
    if total > budget_max:
        selections = _try_downgrades(
            selections, ranked, total - budget_max, profile
        )

    return selections


def find_upgrade_candidate(
    selections: dict[str, ProductRecord],
    ranked: dict[str, list[ScoredProduct]],
    profile: Profile,
) -> tuple[str, ProductRecord] | None:
    """Find the best upgrade candidate (next tier up in highest-priority category).

    Returns (category, upgrade_product) or None if no viable upgrade exists.
    """
    for category in profile.selection_order:
        if category not in selections or category not in ranked:
            continue

        current = selections[category]
        candidates = ranked[category]

        # Find candidates that are strictly better (higher score, higher price)
        for scored in candidates:
            p = scored.product
            if (
                p.id != current.id
                and p.best_price > current.best_price
                and scored.total_score > 0
            ):
                # Must be meaningfully better — at least 10% more expensive
                if p.best_price >= current.best_price * 1.10:
                    return (category, p)

    return None


def find_downgrade_candidate(
    selections: dict[str, ProductRecord],
    ranked: dict[str, list[ScoredProduct]],
    profile: Profile,
) -> tuple[str, ProductRecord] | None:
    """Find the best downgrade candidate (cheaper but still adequate).

    Searches in reverse priority order (lowest priority first).
    Returns (category, downgrade_product) or None.
    """
    for category in reversed(profile.selection_order):
        if category not in selections or category not in ranked:
            continue

        current = selections[category]
        candidates = ranked[category]

        # Find candidates that are cheaper
        for scored in candidates:
            p = scored.product
            if (
                p.id != current.id
                and p.best_price < current.best_price
                and scored.total_score > 0
            ):
                # Must save meaningfully — at least 10% cheaper
                if p.best_price <= current.best_price * 0.90:
                    return (category, p)

    return None


def _try_upgrades(
    selections: dict[str, ProductRecord],
    ranked: dict[str, list[ScoredProduct]],
    headroom: float,
    profile: Profile,
) -> dict[str, ProductRecord]:
    """Try upgrading components in priority order."""
    for category in profile.selection_order:
        if category not in selections or category not in ranked:
            continue

        current = selections[category]
        candidates = ranked[category]

        # Look for a better product that fits in the headroom
        for scored in candidates:
            p = scored.product
            extra_cost = p.best_price - current.best_price
            if (
                p.id != current.id
                and extra_cost > 0
                and extra_cost <= headroom
                and scored.total_score > 0
            ):
                selections[category] = p
                headroom -= extra_cost
                break  # one upgrade per category per pass

        if headroom <= 0:
            break

    return selections


def _try_downgrades(
    selections: dict[str, ProductRecord],
    ranked: dict[str, list[ScoredProduct]],
    overage: float,
    profile: Profile,
) -> dict[str, ProductRecord]:
    """Downgrade lowest-priority components to get within budget."""
    for category in reversed(profile.selection_order):
        if category not in selections or category not in ranked:
            continue

        current = selections[category]
        candidates = ranked[category]

        # Find a cheaper alternative
        for scored in candidates:
            p = scored.product
            savings = current.best_price - p.best_price
            if p.id != current.id and savings > 0:
                selections[category] = p
                overage -= savings
                break

        if overage <= 0:
            break

    return selections
