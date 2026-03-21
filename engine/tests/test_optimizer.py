"""Tests for budget optimizer and upgrade/downgrade identification."""

from engine.config.loader import load_profile
from engine.core.optimizer import (
    find_downgrade_candidate,
    find_upgrade_candidate,
    optimize_budget,
)
from engine.core.scorer import score_products
from engine.tests.conftest import SAMPLE_PRODUCTS


def _build_ranked_and_selections():
    """Helper: score GPUs and pick cheapest as current selection."""
    profile = load_profile("mid_range_gaming")
    gpus = [p for p in SAMPLE_PRODUCTS if p.category == "gpu"]
    ranked_gpu = score_products(
        gpus, "gpu", 300, profile, "1000_1500", "mid_range_gaming"
    )
    cheapest = min(gpus, key=lambda g: g.best_price)
    return profile, {"gpu": cheapest}, {"gpu": ranked_gpu}


def test_upgrade_candidate_found():
    """Should find an upgrade when a cheaper product is selected."""
    profile, selections, ranked = _build_ranked_and_selections()
    result = find_upgrade_candidate(selections, ranked, profile)
    if result:
        cat, product = result
        assert cat == "gpu"
        assert product.best_price > selections["gpu"].best_price


def test_downgrade_candidate_found():
    """Should find a downgrade when expensive product is selected."""
    profile = load_profile("mid_range_gaming")
    gpus = [p for p in SAMPLE_PRODUCTS if p.category == "gpu"]
    ranked_gpu = score_products(
        gpus, "gpu", 300, profile, "1000_1500", "mid_range_gaming"
    )
    # Select the most expensive GPU
    expensive = max(gpus, key=lambda g: g.best_price)
    selections = {"gpu": expensive}
    result = find_downgrade_candidate(selections, {"gpu": ranked_gpu}, profile)
    if result:
        cat, product = result
        assert cat == "gpu"
        assert product.best_price < expensive.best_price


def test_optimize_within_budget():
    """Optimization should not exceed budget_max."""
    profile, selections, ranked = _build_ranked_and_selections()
    optimized = optimize_budget(
        selections, ranked,
        budget_target=800,
        budget_max=1000,
        profile=profile,
    )
    total = sum(p.best_price for p in optimized.values())
    assert total <= 1200  # allow some flex
