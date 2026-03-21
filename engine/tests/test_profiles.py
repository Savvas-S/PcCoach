"""Tests for config loading — profiles and hardware tiers."""

import pytest

from engine.config.loader import (
    budget_range_to_eur,
    get_all_profiles,
    get_chipset_rank,
    get_cpu_gaming_tier,
    get_cpu_workstation_tier,
    get_gpu_tier,
    load_profile,
    load_tiers,
)


# ---------------------------------------------------------------
# Profile tests
# ---------------------------------------------------------------


def test_all_goals_have_profiles():
    """Every valid goal must have a profile."""
    profiles = get_all_profiles()
    expected = {
        "high_end_gaming", "mid_range_gaming", "low_end_gaming",
        "light_work", "heavy_work", "designer", "architecture",
    }
    assert set(profiles.keys()) == expected


def test_budget_allocations_sum_to_100():
    """Each profile's budget allocation must sum to ~100."""
    for goal, profile in get_all_profiles().items():
        total = sum(profile.budget_allocation.values())
        assert abs(total - 100) <= 2, (
            f"{goal}: budget_allocation sums to {total}"
        )


def test_selection_order_covers_all_categories():
    """Selection order must include all 8 core categories."""
    required = {"cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooling"}
    for goal, profile in get_all_profiles().items():
        order_set = set(profile.selection_order)
        missing = required - order_set
        assert not missing, f"{goal}: missing from selection_order: {missing}"


def test_load_specific_profile():
    """Can load a specific profile by goal name."""
    p = load_profile("high_end_gaming")
    assert p.goal == "high_end_gaming"
    assert "gpu" in p.selection_order
    assert "gpu" in p.budget_allocation


def test_unknown_goal_raises():
    """Loading an unknown goal raises ValueError."""
    with pytest.raises(ValueError, match="Unknown goal"):
        load_profile("nonexistent_goal")


def test_family_preference_not_empty():
    """Every profile must have at least one family preference."""
    for goal, profile in get_all_profiles().items():
        assert len(profile.family_preference) > 0, (
            f"{goal}: empty family_preference"
        )


def test_gaming_profiles_gpu_first():
    """Gaming profiles should have GPU first in selection order."""
    for goal in ("high_end_gaming", "mid_range_gaming", "low_end_gaming"):
        p = load_profile(goal)
        assert p.selection_order[0] == "gpu", f"{goal}: GPU not first"


def test_work_profiles_cpu_first():
    """Work profiles should have CPU first in selection order."""
    for goal in ("heavy_work", "architecture"):
        p = load_profile(goal)
        assert p.selection_order[0] == "cpu", f"{goal}: CPU not first"


# ---------------------------------------------------------------
# Tier tests
# ---------------------------------------------------------------


def test_tier_config_loads():
    """Hardware tiers YAML loads successfully."""
    tiers = load_tiers()
    assert len(tiers.gpu_tiers) > 0
    assert len(tiers.cpu_gaming_tiers) > 0
    assert len(tiers.cpu_workstation_tiers) > 0
    assert len(tiers.chipset_rank) > 0


def test_gpu_tier_exact():
    """Exact GPU tier lookup."""
    assert get_gpu_tier("RTX 5090") == 1
    assert get_gpu_tier("RTX 4060") == 9
    assert get_gpu_tier("RX 7600") == 10


def test_gpu_tier_substring():
    """GPU tier lookup via substring match (product model contains tier key)."""
    assert get_gpu_tier("ASUS ROG Astral GeForce RTX 5090 32GB") == 1
    assert get_gpu_tier("ASUS Dual GeForce RTX 4060 EVO OC Edition 8GB") == 9


def test_gpu_tier_unknown():
    """Unknown GPU model returns None."""
    assert get_gpu_tier("Unknown GPU XYZ") is None


def test_cpu_gaming_tier():
    """CPU gaming tier lookup."""
    assert get_cpu_gaming_tier("Ryzen 7 7800X3D") == 2
    assert get_cpu_gaming_tier("Core i5-12400F") == 10


def test_cpu_workstation_tier():
    """CPU workstation tier lookup."""
    assert get_cpu_workstation_tier("Ryzen 9 9950X3D") == 1
    assert get_cpu_workstation_tier("Core i5-12400F") == 9


def test_chipset_rank_with_prefix():
    """Chipset rank strips vendor prefix."""
    assert get_chipset_rank("AMD B650") == 4
    assert get_chipset_rank("Intel B760") == 5
    assert get_chipset_rank("B550") == 6


def test_chipset_rank_unknown():
    """Unknown chipset returns None."""
    assert get_chipset_rank("Unknown Chipset") is None


# ---------------------------------------------------------------
# Budget range tests
# ---------------------------------------------------------------


def test_budget_range_to_eur():
    """Budget range conversion works."""
    assert budget_range_to_eur("0_1000") == (0.0, 1000.0)
    assert budget_range_to_eur("over_3000") == (3000.0, 5000.0)


def test_budget_range_unknown():
    """Unknown budget range raises."""
    with pytest.raises(ValueError):
        budget_range_to_eur("bad_range")
