"""Tests for CatalogService — candidate component querying."""

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.db.models import AffiliateLink, Component
from app.models.builder import (
    BudgetRange,
    BuildRequest,
    ComponentCategory,
    CoolingPreference,
    CPUBrand,
    FormFactor,
    GPUBrand,
    UserGoal,
)
from app.services.catalog import CatalogService

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db():
    """In-memory SQLite DB with JSONB→JSON patching."""
    engine = create_async_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )

    jsonb_patches: list[tuple] = []
    from app.db import models as db_models

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

    for col, original_type in jsonb_patches:
        col.type = original_type


def _request(**overrides) -> BuildRequest:
    defaults = {
        "goal": UserGoal.mid_range_gaming,
        "budget_range": BudgetRange.range_1000_1500,
    }
    defaults.update(overrides)
    return BuildRequest(**defaults)


async def _seed_component(
    db, category, brand, model, specs, price=100.0, in_stock=True
):
    comp = Component(
        category=category, brand=brand, model=model, specs=specs, in_stock=in_stock
    )
    db.add(comp)
    await db.flush()
    db.add(
        AffiliateLink(
            component_id=comp.id,
            store="amazon",
            url="https://www.amazon.de/dp/TESTASIN?tag=thepccoach-21",
            price_eur=price,
        )
    )
    await db.commit()
    return comp


class TestCatalogServiceCandidates:
    async def test_returns_candidates_for_core_categories(self, db):
        await _seed_component(db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199)
        await _seed_component(db, "gpu", "NVIDIA", "RTX 4060", {"vram_gb": "8"}, 299)

        catalog = CatalogService()
        result = await catalog.get_candidates(db, _request())

        assert "cpu" in result
        assert "gpu" in result
        assert len(result["cpu"]) == 1
        assert result["cpu"][0].model == "Ryzen 5 7600"

    async def test_excludes_out_of_stock(self, db):
        await _seed_component(
            db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199, in_stock=True
        )
        await _seed_component(
            db, "cpu", "AMD", "Ryzen 7 7700X", {"socket": "AM5"}, 289, in_stock=False
        )

        catalog = CatalogService()
        result = await catalog.get_candidates(db, _request())

        assert len(result["cpu"]) == 1
        assert result["cpu"][0].model == "Ryzen 5 7600"

    async def test_filters_cpu_brand(self, db):
        await _seed_component(db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199)
        await _seed_component(
            db, "cpu", "Intel", "i5-14400F", {"socket": "LGA1700"}, 179
        )

        catalog = CatalogService()
        result = await catalog.get_candidates(db, _request(cpu_brand=CPUBrand.amd))

        assert len(result["cpu"]) == 1
        assert result["cpu"][0].brand == "AMD"

    async def test_filters_gpu_brand(self, db):
        await _seed_component(db, "gpu", "NVIDIA", "RTX 4060", {"vram_gb": "8"}, 299)
        await _seed_component(db, "gpu", "AMD", "RX 7600", {"vram_gb": "8"}, 259)

        catalog = CatalogService()
        result = await catalog.get_candidates(db, _request(gpu_brand=GPUBrand.nvidia))

        assert len(result["gpu"]) == 1
        assert result["gpu"][0].brand == "NVIDIA"

    async def test_excludes_existing_parts(self, db):
        await _seed_component(db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199)
        await _seed_component(db, "gpu", "NVIDIA", "RTX 4060", {"vram_gb": "8"}, 299)

        catalog = CatalogService()
        result = await catalog.get_candidates(
            db, _request(existing_parts=[ComponentCategory.cpu])
        )

        assert "cpu" not in result
        assert "gpu" in result

    async def test_peripherals_excluded_by_default(self, db):
        await _seed_component(
            db, "monitor", "LG", "27GP850", {"resolution": "2560x1440"}, 279
        )
        await _seed_component(db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199)

        catalog = CatalogService()
        result = await catalog.get_candidates(db, _request(include_peripherals=False))

        assert "monitor" not in result
        assert "cpu" in result

    async def test_peripherals_included_when_requested(self, db):
        await _seed_component(
            db, "monitor", "LG", "27GP850", {"resolution": "2560x1440"}, 279
        )

        catalog = CatalogService()
        result = await catalog.get_candidates(db, _request(include_peripherals=True))

        assert "monitor" in result

    async def test_cooling_preference_filter(self, db):
        await _seed_component(
            db, "cooling", "Noctua", "NH-D15", {"type": "air", "height_mm": "165"}, 99
        )
        await _seed_component(
            db,
            "cooling",
            "Arctic",
            "LF II 360",
            {"type": "liquid", "radiator_size_mm": "360"},
            89,
        )

        catalog = CatalogService()
        result = await catalog.get_candidates(
            db, _request(cooling_preference=CoolingPreference.air)
        )

        assert len(result["cooling"]) == 1
        assert result["cooling"][0].specs["type"] == "air"

    async def test_candidates_sorted_by_cheapest_price(self, db):
        await _seed_component(db, "cpu", "AMD", "Ryzen 9 7950X", {"socket": "AM5"}, 549)
        await _seed_component(db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199)

        catalog = CatalogService()
        result = await catalog.get_candidates(db, _request())

        assert result["cpu"][0].cheapest_price < result["cpu"][1].cheapest_price

    async def test_empty_result_when_no_matching_components(self, db):
        catalog = CatalogService()
        result = await catalog.get_candidates(db, _request())

        # No components seeded — all categories should be empty
        assert len(result) == 0

    async def test_case_form_factor_filter_atx(self, db):
        await _seed_component(db, "case", "NZXT", "H5 Flow", {"form_factor": "ATX"}, 89)
        await _seed_component(
            db, "case", "CM", "Q300L", {"form_factor": "micro_atx"}, 49
        )

        catalog = CatalogService()
        result = await catalog.get_candidates(db, _request(form_factor=FormFactor.atx))

        # ATX form factor request should only return ATX cases
        assert len(result["case"]) == 1
        assert result["case"][0].specs["form_factor"] == "ATX"

    async def test_motherboard_form_factor_filter_matx(self, db):
        await _seed_component(
            db,
            "motherboard",
            "Gigabyte",
            "B650 ATX",
            {"socket": "AM5", "form_factor": "ATX", "ddr_type": "DDR5"},
            169,
        )
        await _seed_component(
            db,
            "motherboard",
            "Gigabyte",
            "B650M",
            {"socket": "AM5", "form_factor": "micro_atx", "ddr_type": "DDR5"},
            119,
        )

        catalog = CatalogService()
        result = await catalog.get_candidates(
            db, _request(form_factor=FormFactor.micro_atx)
        )

        # mATX request should return micro_atx and mini_itx boards, not ATX
        models = [c.model for c in result["motherboard"]]
        assert "B650M" in models
        assert "B650 ATX" not in models
