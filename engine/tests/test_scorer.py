"""Tests for product scoring logic."""

from engine.config.loader import load_profile, load_tiers
from engine.core.scorer import score_products
from engine.tests.conftest import SAMPLE_PRODUCTS, make_product


def _get_gpus():
    return [p for p in SAMPLE_PRODUCTS if p.category == "gpu"]


def _get_cpus():
    return [p for p in SAMPLE_PRODUCTS if p.category == "cpu"]


def test_score_products_returns_sorted():
    """Scored products should be sorted by total_score descending."""
    profile = load_profile("high_end_gaming")
    gpus = _get_gpus()
    scored = score_products(
        gpus, "gpu", 800, profile, "2000_3000", "high_end_gaming"
    )
    assert len(scored) > 0
    for i in range(len(scored) - 1):
        assert scored[i].total_score >= scored[i + 1].total_score


def test_higher_tier_gpu_scores_better_for_high_budget():
    """For high-end gaming with big budget, top-tier GPU should score highest."""
    profile = load_profile("high_end_gaming")
    gpus = _get_gpus()
    scored = score_products(
        gpus, "gpu", 1200, profile, "over_3000", "high_end_gaming"
    )
    # RTX 5080 should score higher than RTX 4060 at this budget
    top = scored[0].product
    assert "5080" in top.model or "5070" in top.model or "5090" in top.model


def test_budget_gpu_preferred_for_low_budget():
    """For low budget, cheaper GPU should rank high due to price score."""
    profile = load_profile("low_end_gaming")
    gpus = _get_gpus()
    scored = score_products(
        gpus, "gpu", 260, profile, "0_1000", "low_end_gaming"
    )
    # RTX 4060 or RX 7600 should be near the top (price-appropriate)
    top_3_models = [s.product.model for s in scored[:3]]
    assert any("4060" in m or "7600" in m for m in top_3_models)


def test_cpu_gaming_rank_matters():
    """Gaming CPUs should be ranked by gaming tier."""
    profile = load_profile("high_end_gaming")
    cpus = _get_cpus()
    scored = score_products(
        cpus, "cpu", 350, profile, "2000_3000", "high_end_gaming"
    )
    # 7800X3D is the best gaming CPU in our sample
    assert "7800X3D" in scored[0].product.model


def test_all_scores_in_range():
    """All score components should be in [0, 1] range."""
    profile = load_profile("mid_range_gaming")
    for category in ["gpu", "cpu", "ram", "storage", "psu"]:
        pool = [p for p in SAMPLE_PRODUCTS if p.category == category]
        if not pool:
            continue
        scored = score_products(
            pool, category, 200, profile, "1000_1500", "mid_range_gaming"
        )
        for s in scored:
            assert 0.0 <= s.spec_score <= 1.0, f"{category}: spec_score={s.spec_score}"
            assert 0.0 <= s.price_score <= 1.0, f"{category}: price_score={s.price_score}"
            assert 0.0 <= s.tier_score <= 1.0, f"{category}: tier_score={s.tier_score}"


def test_notes_bonus_applied():
    """Products matching user notes should get a bonus."""
    from engine.models.types import NotesPreferences

    profile = load_profile("mid_range_gaming")
    gpus = _get_gpus()

    # Without notes
    scored_no_notes = score_products(
        gpus, "gpu", 300, profile, "1000_1500", "mid_range_gaming"
    )

    # With notes preferring NVIDIA
    prefs = NotesPreferences(brands=["NVIDIA"])
    scored_with_notes = score_products(
        gpus, "gpu", 300, profile, "1000_1500", "mid_range_gaming",
        notes_prefs=prefs,
    )

    # NVIDIA products should score higher with notes
    nvidia_no = next(
        s for s in scored_no_notes if s.product.brand == "NVIDIA"
    )
    nvidia_with = next(
        s for s in scored_with_notes
        if s.product.id == nvidia_no.product.id
    )
    assert nvidia_with.total_score >= nvidia_no.total_score
