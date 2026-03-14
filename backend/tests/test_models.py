import pytest
from pydantic import ValidationError

from app.models.builder import (
    BudgetRange,
    BuildRequest,
    BuildResult,
    BuildStatus,
    ComponentCategory,
    ComponentRecommendation,
    StoreLink,
    UserGoal,
    _VALID_GOALS_FOR_BUDGET,
)


class TestBuildRequestGoalBudgetValidation:
    def test_valid_goal_for_budget(self):
        req = BuildRequest(
            goal=UserGoal.low_end_gaming, budget_range=BudgetRange.range_0_1000
        )
        assert req.goal == UserGoal.low_end_gaming

    def test_invalid_goal_for_budget_raises(self):
        with pytest.raises(ValidationError, match="not available for budget"):
            BuildRequest(
                goal=UserGoal.high_end_gaming, budget_range=BudgetRange.range_0_1000
            )

    def test_all_over_3000_goals_are_valid(self):
        for goal in [
            UserGoal.high_end_gaming,
            UserGoal.heavy_work,
            UserGoal.designer,
            UserGoal.architecture,
        ]:
            req = BuildRequest(goal=goal, budget_range=BudgetRange.over_3000)
            assert req.goal == goal

    def test_light_work_valid_across_lower_budgets(self):
        for budget in [
            BudgetRange.range_0_1000,
            BudgetRange.range_1000_1500,
            BudgetRange.range_1500_2000,
        ]:
            req = BuildRequest(goal=UserGoal.light_work, budget_range=budget)
            assert req.goal == UserGoal.light_work

    def test_light_work_invalid_for_high_budget(self):
        with pytest.raises(ValidationError, match="not available for budget"):
            BuildRequest(
                goal=UserGoal.light_work, budget_range=BudgetRange.range_2000_3000
            )


class TestBuildResultTotalPrice:
    def _make_component(
        self, category: ComponentCategory, price: float
    ) -> ComponentRecommendation:
        return ComponentRecommendation(
            category=category,
            name="Test Component",
            brand="TestBrand",
            price_eur=price,
            specs={},
        )

    def test_total_price_computed_from_components(self):
        result = BuildResult(
            id="abc123",
            components=[
                self._make_component(ComponentCategory.cpu, 200.0),
                self._make_component(ComponentCategory.gpu, 400.0),
                self._make_component(ComponentCategory.ram, 80.0),
            ],
            status=BuildStatus.completed,
        )
        assert result.total_price_eur == pytest.approx(680.0)

    def test_total_price_none_when_no_components(self):
        result = BuildResult(id="abc123", components=[], status=BuildStatus.completed)
        assert result.total_price_eur is None

    def test_default_status_is_completed(self):
        result = BuildResult(id="abc123")
        assert result.status == BuildStatus.completed


class TestDeduplicateExistingParts:
    def _base(self, parts: list) -> BuildRequest:
        return BuildRequest(
            goal=UserGoal.low_end_gaming,
            budget_range=BudgetRange.range_0_1000,
            existing_parts=parts,
        )

    def test_duplicates_removed_preserving_order(self):
        req = self._base(
            [ComponentCategory.cpu, ComponentCategory.gpu, ComponentCategory.cpu]
        )
        assert req.existing_parts == [ComponentCategory.cpu, ComponentCategory.gpu]

    def test_all_duplicates(self):
        req = self._base(
            [ComponentCategory.ram, ComponentCategory.ram, ComponentCategory.ram]
        )
        assert req.existing_parts == [ComponentCategory.ram]

    def test_no_duplicates_unchanged(self):
        req = self._base([ComponentCategory.cpu, ComponentCategory.gpu])
        assert req.existing_parts == [ComponentCategory.cpu, ComponentCategory.gpu]

    def test_empty_list_unchanged(self):
        req = self._base([])
        assert req.existing_parts == []


class TestBudgetGoalsJson:
    def test_every_budget_range_is_present(self):
        for budget in BudgetRange:
            assert budget in _VALID_GOALS_FOR_BUDGET, (
                f"BudgetRange.{budget.name} ({budget.value}) is missing from budget_goals.json"
            )

    def test_every_budget_has_at_least_one_goal(self):
        for budget, goals in _VALID_GOALS_FOR_BUDGET.items():
            assert len(goals) > 0, (
                f"Budget {budget.value} has no goals in budget_goals.json"
            )

    def test_all_goal_values_are_valid_enums(self):
        for budget, goals in _VALID_GOALS_FOR_BUDGET.items():
            for goal in goals:
                assert isinstance(goal, UserGoal), (
                    f"Unknown goal value under {budget.value} in budget_goals.json"
                )


class TestAffiliateUrlValidation:
    def _base_component(self) -> dict:
        return {
            "category": ComponentCategory.gpu,
            "name": "RTX 4070",
            "brand": "NVIDIA",
            "price_eur": 599.0,
            "specs": {},
        }

    def test_valid_amazon_url(self):
        comp = ComponentRecommendation(
            **self._base_component(),
            affiliate_url="https://www.amazon.de/dp/B123456",
            affiliate_source="amazon",
        )
        assert comp.affiliate_url is not None

    def test_valid_computeruniverse_url(self):
        comp = ComponentRecommendation(
            **self._base_component(),
            affiliate_url="https://www.computeruniverse.net/en/p/123",
            affiliate_source="computeruniverse",
        )
        assert comp.affiliate_url is not None

    def test_valid_caseking_url(self):
        comp = ComponentRecommendation(
            **self._base_component(),
            affiliate_url="https://www.caseking.de/en/product/123",
            affiliate_source="caseking",
        )
        assert comp.affiliate_url is not None

    def test_none_affiliate_url_allowed(self):
        comp = ComponentRecommendation(**self._base_component(), affiliate_url=None)
        assert comp.affiliate_url is None

    def test_disallowed_domain_raises(self):
        with pytest.raises(ValidationError, match="not an allowed store"):
            ComponentRecommendation(
                **self._base_component(),
                affiliate_url="https://www.ebay.de/itm/12345",
                affiliate_source="amazon",
            )


class TestStoreLinkValidation:
    def test_valid_store_link(self):
        link = StoreLink(
            store="amazon", url="https://www.amazon.de/s?k=RTX+4070&tag=thepccoach-21"
        )
        assert link.url is not None

    def test_valid_computeruniverse_link(self):
        link = StoreLink(
            store="computeruniverse",
            url="https://www.computeruniverse.net/en/search?query=RTX+4070",
        )
        assert link.url is not None

    def test_valid_caseking_link(self):
        link = StoreLink(
            store="caseking", url="https://www.caseking.de/en/search?q=RTX+4070"
        )
        assert link.url is not None

    def test_disallowed_domain_raises(self):
        with pytest.raises(ValidationError, match="not an allowed store"):
            StoreLink(store="amazon", url="https://www.ebay.de/s?k=RTX+4070")
