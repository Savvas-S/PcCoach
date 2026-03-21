"""Tests for the greedy selection algorithm."""

import pytest

from engine.core.selector import run_selection
from engine.tests.conftest import MockCatalogAdapter, SAMPLE_PRODUCTS


@pytest.fixture
def catalog():
    return MockCatalogAdapter(SAMPLE_PRODUCTS)


async def test_basic_build_produces_all_categories(catalog):
    """A basic build should have all 8 core categories."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
        existing_parts=[],
    )
    expected = {"cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooling"}
    assert set(result.components.keys()) == expected


async def test_total_price_positive(catalog):
    """Total price should be positive."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
        existing_parts=[],
    )
    assert result.total_price_eur > 0


async def test_budget_utilization_reasonable(catalog):
    """Budget utilization should be reasonable (>40%)."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
        existing_parts=[],
    )
    assert result.budget_utilization > 0.4


async def test_all_components_have_affiliate_links(catalog):
    """Every selected component must have a valid affiliate URL."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
        existing_parts=[],
    )
    for cat, comp in result.components.items():
        assert comp.affiliate_url, f"{cat}: missing affiliate_url"
        assert "amazon.de" in comp.affiliate_url, f"{cat}: bad URL"


async def test_existing_parts_excluded(catalog):
    """Excluded categories should not appear in the build."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
        existing_parts=["gpu", "case"],
    )
    assert "gpu" not in result.components
    assert "case" not in result.components
    assert "cpu" in result.components


async def test_cpu_brand_preference_amd(catalog):
    """AMD CPU preference should select AMD CPU."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        cpu_brand="amd",
        catalog=catalog,
        existing_parts=[],
    )
    cpu = result.components["cpu"]
    assert cpu.brand.lower() == "amd"


async def test_cpu_brand_preference_intel(catalog):
    """Intel CPU preference should select Intel CPU."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        cpu_brand="intel",
        catalog=catalog,
        existing_parts=[],
    )
    cpu = result.components["cpu"]
    assert cpu.brand.lower() == "intel"


async def test_family_used_set(catalog):
    """family_used should be set to a valid family name."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
        existing_parts=[],
    )
    assert result.family_used
    assert "_" in result.family_used  # e.g. "AM5_DDR5"


async def test_low_budget_prefers_cheaper(catalog):
    """Low budget build should use cheaper components."""
    result = await run_selection(
        goal="low_end_gaming",
        budget_range="0_1000",
        catalog=catalog,
        existing_parts=[],
    )
    assert result.total_price_eur <= 1200  # some flex allowed


async def test_high_budget_prefers_better(catalog):
    """High budget should select premium components when available."""
    low = await run_selection(
        goal="low_end_gaming",
        budget_range="0_1000",
        catalog=catalog,
        existing_parts=[],
    )
    high = await run_selection(
        goal="high_end_gaming",
        budget_range="2000_3000",
        catalog=catalog,
        existing_parts=[],
    )
    assert high.total_price_eur >= low.total_price_eur


async def test_cooling_preference_respected(catalog):
    """Cooling preference should be reflected in selection."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        cooling_preference="air",
        catalog=catalog,
        existing_parts=[],
    )
    cooling = result.components.get("cooling")
    if cooling:
        assert cooling.specs.get("type") == "air"


async def test_socket_compatibility(catalog):
    """CPU and motherboard should share the same socket."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
        existing_parts=[],
    )
    cpu = result.components["cpu"]
    mobo = result.components["motherboard"]
    assert cpu.specs.get("socket") == mobo.specs.get("socket")


async def test_ddr_compatibility(catalog):
    """RAM and motherboard should share the same DDR type."""
    result = await run_selection(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
        existing_parts=[],
    )
    ram = result.components["ram"]
    mobo = result.components["motherboard"]
    assert ram.specs.get("ddr_type") == mobo.specs.get("ddr_type")
