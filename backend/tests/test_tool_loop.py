"""Tests for the agentic tool loop mechanics (mocked Claude API)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.build_validator import BuildValidationError, ResolvedComponent
from app.services.catalog import ToolCatalogResult
from app.services.claude import ClaudeService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tool_use_block(tool_id, name, inp):
    """Simulate an anthropic ToolUseBlock."""
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=inp)


def _text_block(text):
    return SimpleNamespace(type="text", text=text)


def _response(content, stop_reason="tool_use"):
    return SimpleNamespace(content=content, stop_reason=stop_reason)


def _scout_result(cat, n=3):
    """Create N ToolCatalogResult items for a category."""
    return [
        ToolCatalogResult(
            id=i + 1, brand="Brand", model=f"Model {i+1}",
            specs={"socket": "AM5"}, price_eur=100.0 + i * 50,
        )
        for i in range(n)
    ]


def _resolved(comp_id, category, brand="Brand", model="Model"):
    return ResolvedComponent(
        id=comp_id, category=category, brand=brand, model=model,
        specs={"socket": "AM5"}, price_eur=200.0,
        affiliate_url="https://www.amazon.de/dp/TEST?tag=thepccoach-21",
        affiliate_source="amazon",
    )


def _build_components():
    """Minimal component list for a valid build."""
    return [
        {"component_id": 1, "category": "cpu"},
        {"component_id": 2, "category": "gpu"},
        {"component_id": 3, "category": "motherboard"},
        {"component_id": 4, "category": "ram"},
        {"component_id": 5, "category": "storage"},
        {"component_id": 6, "category": "psu"},
        {"component_id": 7, "category": "case"},
        {"component_id": 8, "category": "cooling"},
    ]


def _resolved_map():
    """Resolved components matching _build_components."""
    cats = ["cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooling"]
    return {
        i + 1: _resolved(i + 1, cat) for i, cat in enumerate(cats)
    }


@pytest.fixture
def service():
    """ClaudeService with mocked dependencies."""
    with patch("app.services.claude.settings") as mock_settings, \
         patch("app.services.claude.get_catalog_service") as mock_get_catalog:
        mock_settings.anthropic_api_key = MagicMock()
        mock_settings.anthropic_api_key.get_secret_value.return_value = "test-key"
        mock_settings.claude_model = "claude-sonnet-4-6"
        mock_settings.max_tool_turns = 20
        mock_settings.agentic_loop_timeout = 120.0

        svc = ClaudeService()
        svc.client = MagicMock()
        svc._catalog = MagicMock()
        yield svc


_REQUIRED_CATS = {"cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooling"}


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


class TestHappyPaths:
    async def test_scout_then_submit_succeeds(self, service):
        """Happy path: scout all categories, then submit build."""
        scout_results = {cat: _scout_result(cat, 3) for cat in _REQUIRED_CATS}
        service._catalog.scout_all = AsyncMock(return_value=scout_results)
        service._catalog.resolve_components = AsyncMock(return_value=_resolved_map())

        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(side_effect=[
            # Turn 1: scout
            _response([_tool_use_block("t1", "scout_catalog", {
                "categories": list(_REQUIRED_CATS),
            })]),
            # Turn 2: submit
            _response([_tool_use_block("t2", "submit_build", {
                "summary": "Great build",
                "components": _build_components(),
            })]),
        ])

        result = await service._run_tool_loop(
            db=MagicMock(),
            system_prompt="test",
            user_message="test",
            tools=[],
            terminal_tool_name="submit_build",
            required_categories=_REQUIRED_CATS,
        )

        assert result["summary"] == "Great build"
        assert "_resolved" in result

    async def test_scout_then_query_then_submit_succeeds(self, service):
        """Scout + targeted query + submit."""
        scout_results = {cat: _scout_result(cat, 3) for cat in _REQUIRED_CATS}
        service._catalog.scout_all = AsyncMock(return_value=scout_results)
        service._catalog.query_for_tool = AsyncMock(
            return_value=_scout_result("motherboard", 5)
        )
        service._catalog.resolve_components = AsyncMock(return_value=_resolved_map())

        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(side_effect=[
            # Turn 1: scout
            _response([_tool_use_block("t1", "scout_catalog", {
                "categories": list(_REQUIRED_CATS),
            })]),
            # Turn 2: targeted query
            _response([_tool_use_block("t2", "query_catalog", {
                "category": "motherboard", "socket": "AM5",
            })]),
            # Turn 3: submit
            _response([_tool_use_block("t3", "submit_build", {
                "summary": "Great build",
                "components": _build_components(),
            })]),
        ])

        result = await service._run_tool_loop(
            db=MagicMock(),
            system_prompt="test",
            user_message="test",
            tools=[],
            terminal_tool_name="submit_build",
            required_categories=_REQUIRED_CATS,
        )

        assert result["summary"] == "Great build"

    async def test_search_scout_then_recommend_succeeds(self, service):
        """Search flow: scout + recommend_component."""
        service._catalog.scout_all = AsyncMock(
            return_value={"cpu": _scout_result("cpu", 5)}
        )

        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(side_effect=[
            _response([_tool_use_block("t1", "scout_catalog", {
                "categories": ["cpu"],
            })]),
            _response([_tool_use_block("t2", "recommend_component", {
                "component_id": 1,
                "reason": "Best value for the price",
            })]),
        ])

        result = await service._run_tool_loop(
            db=MagicMock(),
            system_prompt="test",
            user_message="test",
            tools=[],
            terminal_tool_name="recommend_component",
            required_categories=None,
        )

        assert result["component_id"] == 1
        assert "reason" in result


# ---------------------------------------------------------------------------
# Guard rails and error cases
# ---------------------------------------------------------------------------


class TestGuardRails:
    async def test_repeated_identical_query_flagged(self, service):
        """Duplicate query detection returns warning instead of re-querying."""
        scout_results = {cat: _scout_result(cat, 3) for cat in _REQUIRED_CATS}
        service._catalog.scout_all = AsyncMock(return_value=scout_results)
        service._catalog.query_for_tool = AsyncMock(
            return_value=_scout_result("motherboard", 5)
        )
        service._catalog.resolve_components = AsyncMock(return_value=_resolved_map())

        query_input = {"category": "motherboard", "socket": "AM5"}

        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(side_effect=[
            _response([_tool_use_block("t1", "scout_catalog", {
                "categories": list(_REQUIRED_CATS),
            })]),
            _response([_tool_use_block("t2", "query_catalog", query_input)]),
            # Duplicate query
            _response([_tool_use_block("t3", "query_catalog", query_input)]),
            _response([_tool_use_block("t4", "submit_build", {
                "summary": "Build",
                "components": _build_components(),
            })]),
        ])

        result = await service._run_tool_loop(
            db=MagicMock(),
            system_prompt="test",
            user_message="test",
            tools=[],
            terminal_tool_name="submit_build",
            required_categories=_REQUIRED_CATS,
        )

        # query_for_tool should only be called once (second was duplicate)
        assert service._catalog.query_for_tool.await_count == 1

    async def test_premature_submit_rejected(self, service):
        """Missing required categories should be rejected."""
        scout_results = {"cpu": _scout_result("cpu", 3)}
        service._catalog.scout_all = AsyncMock(return_value=scout_results)
        service._catalog.resolve_components = AsyncMock(return_value=_resolved_map())

        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(side_effect=[
            _response([_tool_use_block("t1", "scout_catalog", {
                "categories": ["cpu"],
            })]),
            # Submit with only CPU - missing many required categories
            _response([_tool_use_block("t2", "submit_build", {
                "summary": "Build",
                "components": [{"component_id": 1, "category": "cpu"}],
            })]),
            # Then submit properly
            _response([_tool_use_block("t3", "scout_catalog", {
                "categories": list(_REQUIRED_CATS - {"cpu"}),
            })]),
            _response([_tool_use_block("t4", "submit_build", {
                "summary": "Build",
                "components": _build_components(),
            })]),
        ])

        # Need to update scout_all for second call
        service._catalog.scout_all = AsyncMock(side_effect=[
            {"cpu": _scout_result("cpu", 3)},
            {cat: _scout_result(cat, 3) for cat in _REQUIRED_CATS - {"cpu"}},
        ])

        result = await service._run_tool_loop(
            db=MagicMock(),
            system_prompt="test",
            user_message="test",
            tools=[],
            terminal_tool_name="submit_build",
            required_categories=_REQUIRED_CATS,
        )

        assert result["summary"] == "Build"

    async def test_unqueried_category_rejected(self, service):
        """Submitted category never seen in scout or query."""
        service._catalog.scout_all = AsyncMock(
            return_value={"cpu": _scout_result("cpu", 3)}
        )
        service._catalog.resolve_components = AsyncMock(return_value=_resolved_map())

        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(side_effect=[
            # Scout only cpu
            _response([_tool_use_block("t1", "scout_catalog", {
                "categories": ["cpu"],
            })]),
            # Submit gpu (never scouted)
            _response([_tool_use_block("t2", "submit_build", {
                "summary": "Build",
                "components": [
                    {"component_id": 1, "category": "cpu"},
                    {"component_id": 2, "category": "gpu"},
                ],
            })]),
            # Scout remaining and resubmit
            _response([_tool_use_block("t3", "scout_catalog", {
                "categories": list(_REQUIRED_CATS - {"cpu"}),
            })]),
            _response([_tool_use_block("t4", "submit_build", {
                "summary": "Build",
                "components": _build_components(),
            })]),
        ])

        service._catalog.scout_all = AsyncMock(side_effect=[
            {"cpu": _scout_result("cpu", 3)},
            {cat: _scout_result(cat, 3) for cat in _REQUIRED_CATS - {"cpu"}},
        ])

        result = await service._run_tool_loop(
            db=MagicMock(),
            system_prompt="test",
            user_message="test",
            tools=[],
            terminal_tool_name="submit_build",
            required_categories=_REQUIRED_CATS,
        )

        assert result["summary"] == "Build"

    async def test_max_turns_exceeded_raises(self, service):
        """Should raise TimeoutError when max turns is exceeded."""
        service._catalog.scout_all = AsyncMock(
            return_value={"cpu": _scout_result("cpu", 3)}
        )

        with patch("app.services.claude.settings") as mock_settings:
            mock_settings.max_tool_turns = 2
            mock_settings.agentic_loop_timeout = 120.0

            service.client.messages = MagicMock()
            service.client.messages.create = AsyncMock(side_effect=[
                _response([_tool_use_block("t1", "scout_catalog", {
                    "categories": ["cpu"],
                })]),
                _response([_tool_use_block("t2", "query_catalog", {
                    "category": "cpu",
                })]),
                _response([_tool_use_block("t3", "query_catalog", {
                    "category": "gpu",
                })]),
            ])

            service._catalog.query_for_tool = AsyncMock(
                return_value=_scout_result("cpu", 3)
            )

            with pytest.raises(TimeoutError, match="max turns"):
                await service._run_tool_loop(
                    db=MagicMock(),
                    system_prompt="test",
                    user_message="test",
                    tools=[],
                    terminal_tool_name="submit_build",
                    required_categories=_REQUIRED_CATS,
                )

    async def test_timeout_exceeded_raises(self, service):
        """Should raise TimeoutError when wall-clock timeout is exceeded."""
        with patch("app.services.claude.settings") as mock_settings, \
             patch("app.services.claude.time") as mock_time:
            mock_settings.max_tool_turns = 20
            mock_settings.agentic_loop_timeout = 10.0
            # First call returns start time, second call returns way past timeout
            mock_time.monotonic.side_effect = [0.0, 15.0]

            service.client.messages = MagicMock()
            service.client.messages.create = AsyncMock()

            with pytest.raises(TimeoutError, match="timeout"):
                await service._run_tool_loop(
                    db=MagicMock(),
                    system_prompt="test",
                    user_message="test",
                    tools=[],
                    terminal_tool_name="submit_build",
                    required_categories=_REQUIRED_CATS,
                )

    async def test_unknown_tool_returns_error(self, service):
        """Unknown tool name should return is_error tool_result."""
        service._catalog.scout_all = AsyncMock(
            return_value={cat: _scout_result(cat, 3) for cat in _REQUIRED_CATS}
        )
        service._catalog.resolve_components = AsyncMock(return_value=_resolved_map())

        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(side_effect=[
            _response([_tool_use_block("t1", "scout_catalog", {
                "categories": list(_REQUIRED_CATS),
            })]),
            _response([_tool_use_block("t2", "nonexistent_tool", {})]),
            _response([_tool_use_block("t3", "submit_build", {
                "summary": "Build",
                "components": _build_components(),
            })]),
        ])

        result = await service._run_tool_loop(
            db=MagicMock(),
            system_prompt="test",
            user_message="test",
            tools=[],
            terminal_tool_name="submit_build",
            required_categories=_REQUIRED_CATS,
        )

        assert result["summary"] == "Build"

    async def test_end_turn_without_terminal_raises(self, service):
        """end_turn stop reason without terminal tool should raise ValueError."""
        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(return_value=_response(
            [_text_block("I can't do this")], stop_reason="end_turn"
        ))

        with pytest.raises(ValueError, match="ended without calling"):
            await service._run_tool_loop(
                db=MagicMock(),
                system_prompt="test",
                user_message="test",
                tools=[],
                terminal_tool_name="submit_build",
                required_categories=_REQUIRED_CATS,
            )


# ---------------------------------------------------------------------------
# Validation + repair
# ---------------------------------------------------------------------------


class TestValidationRepair:
    async def test_validation_failure_triggers_repair_within_loop(self, service):
        """First validation failure triggers repair; second attempt succeeds."""
        from app.services.build_validator import (
            ValidationResult,
            ValidationError as VError,
        )

        scout_results = {cat: _scout_result(cat, 3) for cat in _REQUIRED_CATS}
        service._catalog.scout_all = AsyncMock(return_value=scout_results)
        service._catalog.resolve_components = AsyncMock(return_value=_resolved_map())

        # First validation fails, second passes
        bad_result = ValidationResult(
            valid=False,
            errors=[VError("motherboard", "socket_mismatch", "AM5 != LGA1700")],
        )
        good_result = ValidationResult(valid=True, errors=[], warnings=[])
        service._validator.validate = MagicMock(side_effect=[bad_result, good_result])

        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(side_effect=[
            _response([_tool_use_block("t1", "scout_catalog", {
                "categories": list(_REQUIRED_CATS),
            })]),
            # First submit — will fail validation
            _response([_tool_use_block("t2", "submit_build", {
                "summary": "Build v1",
                "components": _build_components(),
            })]),
            # Repair query
            _response([_tool_use_block("t3", "query_catalog", {
                "category": "motherboard", "socket": "AM5",
            })]),
            # Second submit — validation passes
            _response([_tool_use_block("t4", "submit_build", {
                "summary": "Build v2",
                "components": _build_components(),
            })]),
        ])

        service._catalog.query_for_tool = AsyncMock(
            return_value=_scout_result("motherboard", 5)
        )

        result = await service._run_tool_loop(
            db=MagicMock(),
            system_prompt="test",
            user_message="test",
            tools=[],
            terminal_tool_name="submit_build",
            required_categories=_REQUIRED_CATS,
        )

        assert result["summary"] == "Build v2"
        assert service._validator.validate.call_count == 2

    async def test_repair_success_returns_result(self, service):
        """After a failed first attempt, successful repair returns the build."""
        from app.services.build_validator import (
            ValidationResult,
            ValidationError as VError,
        )

        scout_results = {cat: _scout_result(cat, 3) for cat in _REQUIRED_CATS}
        service._catalog.scout_all = AsyncMock(return_value=scout_results)
        service._catalog.resolve_components = AsyncMock(return_value=_resolved_map())

        bad_result = ValidationResult(
            valid=False,
            errors=[VError("ram", "ddr_mismatch", "DDR5 != DDR4")],
        )
        good_result = ValidationResult(valid=True, errors=[], warnings=[])
        service._validator.validate = MagicMock(side_effect=[bad_result, good_result])

        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(side_effect=[
            _response([_tool_use_block("t1", "scout_catalog", {
                "categories": list(_REQUIRED_CATS),
            })]),
            _response([_tool_use_block("t2", "submit_build", {
                "summary": "Build bad",
                "components": _build_components(),
            })]),
            _response([_tool_use_block("t3", "submit_build", {
                "summary": "Build fixed",
                "components": _build_components(),
            })]),
        ])

        result = await service._run_tool_loop(
            db=MagicMock(),
            system_prompt="test",
            user_message="test",
            tools=[],
            terminal_tool_name="submit_build",
            required_categories=_REQUIRED_CATS,
        )

        assert result["summary"] == "Build fixed"

    async def test_second_repair_failure_raises_build_validation_error(self, service):
        """After two failed validations, should raise BuildValidationError."""
        from app.services.build_validator import (
            ValidationResult,
            ValidationError as VError,
        )

        scout_results = {cat: _scout_result(cat, 3) for cat in _REQUIRED_CATS}
        service._catalog.scout_all = AsyncMock(return_value=scout_results)
        service._catalog.resolve_components = AsyncMock(return_value=_resolved_map())

        bad_result = ValidationResult(
            valid=False,
            errors=[VError("motherboard", "socket_mismatch", "AM5 != LGA1700")],
        )
        service._validator.validate = MagicMock(return_value=bad_result)

        service.client.messages = MagicMock()
        service.client.messages.create = AsyncMock(side_effect=[
            _response([_tool_use_block("t1", "scout_catalog", {
                "categories": list(_REQUIRED_CATS),
            })]),
            _response([_tool_use_block("t2", "submit_build", {
                "summary": "Build v1",
                "components": _build_components(),
            })]),
            # After repair error, Claude tries again
            _response([_tool_use_block("t3", "submit_build", {
                "summary": "Build v2",
                "components": _build_components(),
            })]),
        ])

        with pytest.raises(BuildValidationError):
            await service._run_tool_loop(
                db=MagicMock(),
                system_prompt="test",
                user_message="test",
                tools=[],
                terminal_tool_name="submit_build",
                required_categories=_REQUIRED_CATS,
            )
