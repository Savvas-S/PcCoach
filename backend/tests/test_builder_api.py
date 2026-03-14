"""Integration tests for POST /api/v1/build and GET /api/v1/build/{id}.

These tests use an in-memory SQLite database (via aiosqlite) so they run
without a real PostgreSQL instance. JSONB is not available in SQLite; we
use JSON instead via the render_as_batch / JSON fallback provided by
SQLAlchemy's type system.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """Create a fresh in-memory SQLite DB for each test."""
    engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    # SQLite doesn't support JSONB — temporarily patch the column type to plain
    # JSON at the ORM level, then restore it after the test to avoid leaking
    # into other tests in the same process.
    import sqlalchemy as sa
    from app.db import models as db_models
    original_type = db_models.Build.result.property.columns[0].type
    db_models.Build.result.property.columns[0].type = sa.JSON()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    db_models.Build.result.property.columns[0].type = original_type


@pytest.fixture
def client(db_session: AsyncSession):
    """TestClient with get_db overridden to use the test session."""
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
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
# POST /api/v1/build — cache miss (calls Claude)
# ---------------------------------------------------------------------------

class TestCreateBuildCacheMiss:
    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_new_build_saved_and_returned(self, mock_guardrail, mock_get_service, client):
        build = _make_build_result()
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()
        mock_service.generate_build = AsyncMock(return_value=build)
        mock_get_service.return_value = mock_service

        resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)

        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == build.id
        assert len(data["components"]) == 1
        mock_service.generate_build.assert_awaited_once()

    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_build_persisted_retrievable_by_id(self, mock_guardrail, mock_get_service, client):
        build = _make_build_result("persist01")
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()
        mock_service.generate_build = AsyncMock(return_value=build)
        mock_get_service.return_value = mock_service

        client.post("/api/v1/build", json=_VALID_PAYLOAD)
        resp = client.get(f"/api/v1/build/{build.id}")

        assert resp.status_code == 200
        assert resp.json()["id"] == build.id


# ---------------------------------------------------------------------------
# POST /api/v1/build — cache hit (skips Claude)
# ---------------------------------------------------------------------------

class TestCreateBuildCacheHit:
    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_identical_request_returns_cached_result(self, mock_guardrail, mock_get_service, client):
        build = _make_build_result()
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()
        mock_service.generate_build = AsyncMock(return_value=build)
        mock_get_service.return_value = mock_service

        # First request — calls Claude
        resp1 = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp1.status_code == 201

        # Second identical request — must NOT call Claude again
        resp2 = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp2.status_code == 201
        assert resp2.json()["id"] == resp1.json()["id"]
        mock_service.generate_build.assert_awaited_once()  # still only one call


# ---------------------------------------------------------------------------
# GET /api/v1/build/{id}
# ---------------------------------------------------------------------------

class TestGetBuild:
    @patch("app.api.v1.builder.get_claude_service")
    @patch("app.api.v1.builder.input_guardrail")
    def test_existing_build_returned(self, mock_guardrail, mock_get_service, client):
        build = _make_build_result("gettest1")
        mock_guardrail.check.return_value = MagicMock(allowed=True)
        mock_service = MagicMock()
        mock_service.generate_build = AsyncMock(return_value=build)
        mock_get_service.return_value = mock_service

        client.post("/api/v1/build", json=_VALID_PAYLOAD)
        resp = client.get(f"/api/v1/build/{build.id}")

        assert resp.status_code == 200
        assert resp.json()["id"] == build.id

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
            allowed=False, reason="Duplicate request detected. Please wait before resubmitting."
        )
        resp = client.post("/api/v1/build", json=_VALID_PAYLOAD)
        assert resp.status_code == 429
