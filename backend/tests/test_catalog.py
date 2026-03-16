"""Tests for CatalogService — agentic tool-loop catalog methods."""

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.db.models import AffiliateLink, Component
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


# ---------------------------------------------------------------------------
# scout_all()
# ---------------------------------------------------------------------------


class TestScoutAll:
    async def test_returns_correct_categories(self, db):
        await _seed_component(db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199)
        await _seed_component(db, "gpu", "NVIDIA", "RTX 4060", {"vram_gb": "8"}, 299)

        catalog = CatalogService()
        result = await catalog.scout_all(db, ["cpu", "gpu"])

        assert "cpu" in result
        assert "gpu" in result
        assert len(result["cpu"]) == 1
        assert len(result["gpu"]) == 1

    async def test_respects_limit_per_category(self, db):
        for i in range(5):
            await _seed_component(
                db, "cpu", "AMD", f"Ryzen {i}", {"socket": "AM5"}, 100 + i * 50
            )

        catalog = CatalogService()
        result = await catalog.scout_all(db, ["cpu"], limit_per_category=3)

        assert len(result["cpu"]) == 3

    async def test_empty_categories_handled(self, db):
        catalog = CatalogService()
        result = await catalog.scout_all(db, ["cpu", "gpu"])

        assert result["cpu"] == []
        assert result["gpu"] == []

    async def test_multi_shop_dedup(self, db):
        """Multiple affiliate links for same component = one result with MIN price."""
        comp = Component(
            category="cpu", brand="AMD", model="Ryzen 5 7600",
            specs={"socket": "AM5"}, in_stock=True,
        )
        db.add(comp)
        await db.flush()
        db.add(AffiliateLink(
            component_id=comp.id, store="amazon",
            url="https://www.amazon.de/dp/A?tag=thepccoach-21", price_eur=219,
        ))
        db.add(AffiliateLink(
            component_id=comp.id, store="caseking",
            url="https://www.caseking.de/test", price_eur=199,
        ))
        await db.commit()

        catalog = CatalogService()
        result = await catalog.scout_all(db, ["cpu"])

        assert len(result["cpu"]) == 1
        assert result["cpu"][0].price_eur == 199.0


# ---------------------------------------------------------------------------
# query_for_tool()
# ---------------------------------------------------------------------------


class TestQueryForTool:
    async def test_basic_query(self, db):
        await _seed_component(db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199)

        catalog = CatalogService()
        result = await catalog.query_for_tool(db, "cpu")

        assert len(result) == 1
        assert result[0].brand == "AMD"
        assert result[0].model == "Ryzen 5 7600"

    async def test_spec_filtering(self, db):
        """Only CATEGORY_SPEC_KEYS specs should appear."""
        await _seed_component(
            db, "cpu", "AMD", "Ryzen 5 7600",
            {"socket": "AM5", "cores": "6", "internal_code": "secret"}, 199,
        )

        catalog = CatalogService()
        result = await catalog.query_for_tool(db, "cpu")

        assert "socket" in result[0].specs
        assert "cores" in result[0].specs
        assert "internal_code" not in result[0].specs

    async def test_brand_filter(self, db):
        await _seed_component(db, "cpu", "AMD", "Ryzen 5", {"socket": "AM5"}, 199)
        await _seed_component(db, "cpu", "Intel", "i5-14400F", {"socket": "LGA1700"}, 179)

        catalog = CatalogService()
        result = await catalog.query_for_tool(db, "cpu", brand="AMD")

        assert len(result) == 1
        assert result[0].brand == "AMD"

    async def test_socket_filter(self, db):
        await _seed_component(
            db, "motherboard", "Gigabyte", "B650",
            {"socket": "AM5", "form_factor": "ATX", "ddr_type": "DDR5"}, 169,
        )
        await _seed_component(
            db, "motherboard", "Gigabyte", "B760",
            {"socket": "LGA1700", "form_factor": "ATX", "ddr_type": "DDR5"}, 159,
        )

        catalog = CatalogService()
        result = await catalog.query_for_tool(db, "motherboard", socket="AM5")

        assert len(result) == 1
        assert result[0].model == "B650"

    async def test_limit(self, db):
        for i in range(10):
            await _seed_component(
                db, "cpu", "AMD", f"Ryzen {i}", {"socket": "AM5"}, 100 + i * 50
            )

        catalog = CatalogService()
        result = await catalog.query_for_tool(db, "cpu", limit=5)

        assert len(result) == 5

    async def test_price_sorting(self, db):
        await _seed_component(db, "cpu", "AMD", "Ryzen 9 7950X", {"socket": "AM5"}, 549)
        await _seed_component(db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199)

        catalog = CatalogService()
        result = await catalog.query_for_tool(db, "cpu")

        assert result[0].price_eur < result[1].price_eur

    async def test_no_urls_in_results(self, db):
        await _seed_component(db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199)

        catalog = CatalogService()
        result = await catalog.query_for_tool(db, "cpu")

        assert not hasattr(result[0], "affiliate_url")
        assert not hasattr(result[0], "stores")

    async def test_empty_results(self, db):
        catalog = CatalogService()
        result = await catalog.query_for_tool(db, "cpu", brand="NonExistent")

        assert result == []

    async def test_multi_shop_dedup(self, db):
        comp = Component(
            category="gpu", brand="NVIDIA", model="RTX 4060",
            specs={"vram_gb": "8"}, in_stock=True,
        )
        db.add(comp)
        await db.flush()
        db.add(AffiliateLink(
            component_id=comp.id, store="amazon",
            url="https://www.amazon.de/dp/B?tag=thepccoach-21", price_eur=319,
        ))
        db.add(AffiliateLink(
            component_id=comp.id, store="caseking",
            url="https://www.caseking.de/test", price_eur=299,
        ))
        await db.commit()

        catalog = CatalogService()
        result = await catalog.query_for_tool(db, "gpu")

        assert len(result) == 1
        assert result[0].price_eur == 299.0


# ---------------------------------------------------------------------------
# resolve_components()
# ---------------------------------------------------------------------------


class TestResolveComponents:
    async def test_valid_ids(self, db):
        comp = await _seed_component(
            db, "cpu", "AMD", "Ryzen 5 7600", {"socket": "AM5"}, 199
        )

        catalog = CatalogService()
        result = await catalog.resolve_components(db, [comp.id])

        assert comp.id in result
        rc = result[comp.id]
        assert rc.brand == "AMD"
        assert rc.price_eur == 199.0
        assert "amazon" in rc.affiliate_url

    async def test_unknown_id_error(self, db):
        catalog = CatalogService()
        with pytest.raises(ValueError, match="not found"):
            await catalog.resolve_components(db, [99999])

    async def test_picks_cheapest_link(self, db):
        comp = Component(
            category="cpu", brand="AMD", model="Ryzen 5 7600",
            specs={"socket": "AM5"}, in_stock=True,
        )
        db.add(comp)
        await db.flush()
        db.add(AffiliateLink(
            component_id=comp.id, store="amazon",
            url="https://www.amazon.de/dp/C?tag=thepccoach-21", price_eur=219,
        ))
        db.add(AffiliateLink(
            component_id=comp.id, store="caseking",
            url="https://www.caseking.de/test", price_eur=189,
        ))
        await db.commit()

        catalog = CatalogService()
        result = await catalog.resolve_components(db, [comp.id])

        rc = result[comp.id]
        assert rc.price_eur == 189.0
        assert rc.affiliate_source == "caseking"
