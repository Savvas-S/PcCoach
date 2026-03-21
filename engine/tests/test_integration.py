"""End-to-end integration tests: request → engine → valid build.

Tests every valid (goal, budget_range) combination using mock catalog.
"""

import json
from pathlib import Path

import pytest

from engine import select_build
from engine.tests.conftest import MockCatalogAdapter, SAMPLE_PRODUCTS

# Load budget_goals.json to get all valid (goal, budget_range) combos
_BUDGET_GOALS_PATH = Path(__file__).parent.parent.parent / "shared" / "budget_goals.json"


def _load_valid_combos() -> list[tuple[str, str]]:
    """Load all valid (budget_range, goal) combos from budget_goals.json."""
    with open(_BUDGET_GOALS_PATH) as f:
        data = json.load(f)
    combos = []
    for budget_range, goals in data.items():
        for goal in goals:
            combos.append((budget_range, goal))
    return combos


VALID_COMBOS = _load_valid_combos()


@pytest.fixture
def catalog():
    return MockCatalogAdapter(SAMPLE_PRODUCTS)


@pytest.mark.parametrize("budget_range,goal", VALID_COMBOS)
async def test_valid_combo_produces_build(budget_range, goal, catalog):
    """Every valid (budget_range, goal) combination should produce a build."""
    result = await select_build(
        goal=goal,
        budget_range=budget_range,
        catalog=catalog,
    )
    # Must have at least some components
    assert len(result.components) >= 4, (
        f"{goal}/{budget_range}: only {len(result.components)} components"
    )
    # All components must have affiliate URLs
    for cat, comp in result.components.items():
        assert comp.affiliate_url, f"{goal}/{budget_range}/{cat}: no URL"
    # Total price must be positive
    assert result.total_price_eur > 0
    # Family must be set
    assert result.family_used


async def test_all_core_categories_present(catalog):
    """A standard build should have all 8 core categories."""
    result = await select_build(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
    )
    expected = {"cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooling"}
    assert set(result.components.keys()) == expected


async def test_component_ids_are_positive(catalog):
    """All component IDs should be positive integers."""
    result = await select_build(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
    )
    for comp in result.components.values():
        assert comp.component_id > 0


async def test_socket_ddr_match_in_result(catalog):
    """CPU socket must match motherboard, RAM DDR must match motherboard."""
    result = await select_build(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
    )
    cpu = result.components["cpu"]
    mobo = result.components["motherboard"]
    ram = result.components["ram"]
    assert cpu.specs.get("socket") == mobo.specs.get("socket")
    assert ram.specs.get("ddr_type") == mobo.specs.get("ddr_type")


async def test_family_name_matches_components(catalog):
    """family_used should match the actual socket/DDR of selected components."""
    result = await select_build(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
    )
    socket = result.components["cpu"].specs.get("socket", "")
    ddr = result.components["ram"].specs.get("ddr_type", "")
    assert result.family_used == f"{socket}_{ddr}"


async def test_existing_parts_reduce_component_count(catalog):
    """Excluding parts should reduce the number of components."""
    full = await select_build(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        catalog=catalog,
    )
    partial = await select_build(
        goal="mid_range_gaming",
        budget_range="1000_1500",
        existing_parts=["gpu", "case"],
        catalog=catalog,
    )
    assert len(partial.components) < len(full.components)
    assert "gpu" not in partial.components
    assert "case" not in partial.components
