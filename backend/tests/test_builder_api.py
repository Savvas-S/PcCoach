"""Integration tests for POST /api/v1/build and GET /api/v1/build/{id}.

These tests use an in-memory SQLite database (via aiosqlite) so they run
without a real PostgreSQL instance. JSONB is not available in SQLite; we
use JSON instead via the render_as_batch / JSON fallback provided by
SQLAlchemy's type system.

POST /api/v1/build returns an SSE stream (text/event-stream). Helper
``_parse_sse`` extracts typed events from the raw response text.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base, get_db
from app.main import app
from app.models.builder import (
    BudgetRange,
    BuildResult,
    BuildStatus,
    ComponentCategory,
    ComponentRecommendation,
    UserGoal,
)
from app.services.build_validator import BuildValidationError, ValidationError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """Create a fresh in-memory SQLite DB for each test."""
    engine = create_async_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )

    # SQLite doesn't support JSONB — temporarily patch JSONB column types to
    # plain JSON at the ORM level, then restore after the test.
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import JSONB

    from app.db import models as db_models

    jsonb_patches: list[tuple] = []
    for model in (db_models.Build, db_models.Component):
        for attr_name in dir(model):
            attr = getattr(model, attr_name, None)
            if hasattr(attr, "property") and hasattr(attr.property, "columns"):
                col = attr.property.columns[0]
                if isinstance(col.type, JSONB):
                    jsonb_patches.append((col, col.type))
                    col.type = sa.JSON()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

    # Restore original types
    for col, original_type in jsonb_patches:
        col.type = original_type


@pytest.fixture
def client(db_session: AsyncSession):
    """TestClient with get_db overridden to use the test session.

    init_db is patched out because the lifespan calls it, which requires
    a real DATABASE_URL. Tests use their own in-memory SQLite engine.
    Rate limiter is disabled so tests don't interfere with each other.

    We yield the *same* session object for every get_db call so that
    data committed by POST is visible to a subsequent GET within the
    same in-memory SQLite database.
    """
    from app.limiter import limiter

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    was_enabled = limiter.enabled
    limiter.enabled = False
    with patch("app.main.init_db"):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    limiter.enabled = was_enabled
    app.dependency_overrides.clear()


def _make_build_result(build_id: str = "testid12") -> BuildResult:
    return BuildResult(
        id=build_id,
        components=[
            ComponentRecommendation(
                category=ComponentCategory.cpu,
                name="AMD Ryzen 5 7600X",
                brand="AMD",
                price_eur=250.0,
                specs={"cores": "6"},
            )
        ],
        summary="A solid mid-range build.",
        status=BuildStatus.completed,
    )


_VALID_PAYLOAD = {
    "goal": UserGoal.mid_range_gaming,
    "budget_range": BudgetRange.range_1000_1500,
    "form_factor": "atx",
    "cpu_brand": "no_preference",
    "gpu_brand": "no_preference",
    "cooling_preference": "no_preference",
    "include_peripherals": False,
    "existing_parts": [],
    "notes": "gaming pc",
}


# ---------------------------------------------------------------------------
# SSE parsing helper
# ---------------------------------------------------------------------------


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    """Parse SSE text into a list of (event_type, data_dict) tuples.

    Handles multi-line ``data:`` fields per the SSE spec (multiple
    ``data:`` lines are concatenated with ``\\n``).
    """
    events = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_type = ""
        data_lines: list[str] = []
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data_lines.append(line[6:])
        data = "\n".join(data_lines)
        if event_type and data:
            events.append((event_type, json.loads(data)))
    return events


def _sse_result(resp) -> dict:
    """Extract the 'result' event data from an SSE response."""
    events = _parse_sse(resp.text)
    for event_type, data in events:
        if event_type == "result":
            return data
    raise AssertionError(f"No 'result' event found in SSE response: {events}")


def _sse_error(resp) -> dict:
    """Extract the 'error' event data from an SSE response."""
    events = _parse_sse(resp.text)
    for event_type, data in events:
        if event_type == "error":
            return data
    raise AssertionError(f"No 'error' event found in SSE response: {events}")


# ---------------------------------------------------------------------------
# Async generator mock helper
# ---------------------------------------------------------------------------


async def _mock_build_stream(build: BuildResult):
    """Create an async generator that mimics generate_build_stream."""
    yield {
        "type": "progress",
        "phase": "scouting",
        "turn": 1,
        "elapsed_s": 1.0,
        "categories_scouted": ["cpu"],
        "categories_queried": [],
        "tool": "scout_catalog",
    }
    yield {"type": "result", "data": build}


# ---------------------------------------------------------------------------
# POST /api/v1/build — cache miss (calls Claude)
# ---------------------------------------------------------------------------


class TestCreateBuildCacheMiss:
    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_new_build_saved_and_returned(
        self, mock_guardrail, mock_get_service, client
    ):
        build = _make_build_result()
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()
        mock_service.generate_build_stream = MagicMock(
            return_value=_mock_build_stream(build)
        )
        mock_get_service.return_value = mock_service

        resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)

        assert resp.status_code == 200
        data = _sse_result(resp)
        assert data["id"] == build.id
        assert len(data["components"]) == 1
        mock_service.generate_build_stream.assert_called_once()

    @patch("app.api.v1.builder.secrets.token_urlsafe", return_value="persist01")
    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_build_persisted_retrievable_by_id(
        self,
        mock_guardrail,
        mock_get_service,
        mock_token,
        client,
    ):
        build = _make_build_result("persist01")
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()
        mock_service.generate_build_stream = MagicMock(
            return_value=_mock_build_stream(build)
        )
        mock_get_service.return_value = mock_service

        post_resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert post_resp.status_code == 200

        resp = client.get("/api/v1/build/persist01")
        assert resp.status_code == 200
        assert resp.json()["id"] == "persist01"


# ---------------------------------------------------------------------------
# POST /api/v1/build — cache hit (skips Claude)
# ---------------------------------------------------------------------------


class TestCreateBuildCacheHit:
    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_identical_request_returns_cached_result(
        self, mock_guardrail, mock_get_service, client
    ):
        build = _make_build_result()
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()
        mock_service.generate_build_stream = MagicMock(
            return_value=_mock_build_stream(build)
        )
        mock_get_service.return_value = mock_service

        # First request — calls Claude
        resp1 = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp1.status_code == 200

        # Second identical request — must NOT call Claude again
        resp2 = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp2.status_code == 200
        result1 = _sse_result(resp1)
        result2 = _sse_result(resp2)
        assert result2["id"] == result1["id"]
        mock_service.generate_build_stream.assert_called_once()  # still only one call


# ---------------------------------------------------------------------------
# GET /api/v1/build/{id}
# ---------------------------------------------------------------------------


class TestGetBuild:
    @patch("app.api.v1.builder.secrets.token_urlsafe", return_value="gettest1")
    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_existing_build_returned(
        self,
        mock_guardrail,
        mock_get_service,
        mock_token,
        client,
    ):
        build = _make_build_result("gettest1")
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()
        mock_service.generate_build_stream = MagicMock(
            return_value=_mock_build_stream(build)
        )
        mock_get_service.return_value = mock_service

        post_resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert post_resp.status_code == 200

        resp = client.get("/api/v1/build/gettest1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "gettest1"

    def test_missing_build_returns_404(self, client):
        resp = client.get("/api/v1/build/doesnotexist")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Build not found"


# ---------------------------------------------------------------------------
# Input guardrail blocking
# ---------------------------------------------------------------------------


class TestGuardrailBlocking:
    @patch("app.api.v1.builder.input_guardrail")
    def test_blocked_request_returns_400(self, mock_guardrail, client):
        mock_guardrail.check.return_value = MagicMock(
            allowed=False, reason="Off-topic request"
        )
        resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp.status_code == 400
        assert "Off-topic" in resp.json()["detail"]

    @patch("app.api.v1.builder.input_guardrail")
    def test_duplicate_request_returns_429(self, mock_guardrail, client):
        mock_guardrail.check.return_value = MagicMock(
            allowed=False,
            reason="Duplicate request detected. Please wait before resubmitting.",
        )
        resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp.status_code == 429


# ---------------------------------------------------------------------------
# Error handling (errors during streaming are SSE error events, not HTTP codes)
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_validation_failure_returns_error_event(
        self, mock_guardrail, mock_get_service, client
    ):
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()

        async def _failing_stream(*args, **kwargs):
            if False:
                yield  # async generator syntax
            raise BuildValidationError(
                [ValidationError("motherboard", "socket_mismatch", "AM5 != LGA1700")]
            )

        mock_service.generate_build_stream = MagicMock(return_value=_failing_stream())
        mock_get_service.return_value = mock_service

        resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp.status_code == 200  # SSE always 200
        err = _sse_error(resp)
        assert err["status"] == 400
        assert "compatibility" in err["detail"].lower()

    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_timeout_returns_error_event(
        self, mock_guardrail, mock_get_service, client
    ):
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()

        async def _timeout_stream(*args, **kwargs):
            if False:
                yield  # async generator syntax
            raise TimeoutError("Tool loop exceeded timeout")

        mock_service.generate_build_stream = MagicMock(return_value=_timeout_stream())
        mock_get_service.return_value = mock_service

        resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp.status_code == 200  # SSE always 200
        err = _sse_error(resp)
        assert err["status"] == 504


# ---------------------------------------------------------------------------
# Parametrized _map_error coverage
# ---------------------------------------------------------------------------


_ERROR_CASES = [
    (anthropic.APIConnectionError(request=None), 502, "could not reach"),
    (
        anthropic.RateLimitError(
            message="rate limited",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        ),
        503,
        "busy",
    ),
    (
        anthropic.AuthenticationError(
            message="auth",
            response=MagicMock(status_code=401, headers={}),
            body=None,
        ),
        503,
        "unavailable",
    ),
    (
        anthropic.InternalServerError(
            message="overloaded",
            response=MagicMock(status_code=529, headers={}),
            body=None,
        ),
        503,
        "overloaded",
    ),
    (ValueError("bad response"), 500, "could not generate"),
    (RuntimeError("unknown"), 500, "internal server error"),
]


class TestMapErrorCoverage:
    """Verify _map_error returns correct (status, detail) for each exception type."""

    @pytest.mark.parametrize(
        "exc,expected_status,detail_substr",
        _ERROR_CASES,
        ids=[type(e).__name__ for e, _, _ in _ERROR_CASES],
    )
    @patch("app.api.v1.builder.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_error_mapping(
        self,
        mock_guardrail,
        mock_get_service,
        mock_sleep,
        exc,
        expected_status,
        detail_substr,
        client,
    ):
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()

        async def _raise_stream(*args, **kwargs):
            if False:
                yield  # async generator syntax
            raise exc

        mock_service.generate_build_stream = MagicMock(return_value=_raise_stream())
        mock_get_service.return_value = mock_service

        resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp.status_code == 200  # SSE always 200
        err = _sse_error(resp)
        assert err["status"] == expected_status
        assert detail_substr in err["detail"].lower()


# ---------------------------------------------------------------------------
# Progress events in SSE output
# ---------------------------------------------------------------------------


class TestProgressEvents:
    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_progress_events_present_in_stream(
        self, mock_guardrail, mock_get_service, client
    ):
        build = _make_build_result()
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()
        mock_service.generate_build_stream = MagicMock(
            return_value=_mock_build_stream(build)
        )
        mock_get_service.return_value = mock_service

        resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp.status_code == 200

        events = _parse_sse(resp.text)
        event_types = [et for et, _ in events]

        # Must have at least one progress event before the result
        assert "progress" in event_types
        assert "result" in event_types
        assert event_types.index("progress") < event_types.index("result")

        # Verify progress event shape
        progress_data = [d for et, d in events if et == "progress"][0]
        assert "phase" in progress_data
        assert "turn" in progress_data
        assert "elapsed_s" in progress_data
        assert "categories_scouted" in progress_data
        assert "tool" in progress_data


# ---------------------------------------------------------------------------
# Internal cache-clear endpoint
# ---------------------------------------------------------------------------


class TestClearCache:
    @patch("app.main.ipaddress.ip_address")
    def test_clear_cache_from_localhost(self, mock_ip, client):
        mock_addr = MagicMock()
        mock_addr.is_loopback = True
        mock_addr.is_private = True
        mock_ip.return_value = mock_addr
        resp = client.post("/internal/clear-cache")
        assert resp.status_code == 200
        assert "cleared" in resp.json()

    @patch("app.main.ipaddress.ip_address")
    def test_clear_cache_returns_evicted_count(self, mock_ip, client):
        mock_addr = MagicMock()
        mock_addr.is_loopback = True
        mock_addr.is_private = True
        mock_ip.return_value = mock_addr

        from app.api.v1.search import _search_cache

        _search_cache["key1"] = {"dummy": True}
        _search_cache["key2"] = {"dummy": True}
        resp = client.post("/internal/clear-cache")
        assert resp.status_code == 200
        assert resp.json()["cleared"] == 2
        assert len(_search_cache) == 0

    def test_clear_cache_rejected_from_public_ip(self, client):
        """TestClient sends 'testclient' as host which is not a valid IP —
        should be rejected with 403."""
        resp = client.post("/internal/clear-cache")
        assert resp.status_code == 403
