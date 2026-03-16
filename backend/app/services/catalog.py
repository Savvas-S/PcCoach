"""Catalog query service — fetches candidate components from the DB for Claude."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AffiliateLink, Component
from app.models.builder import ComponentCategory
from app.services.build_validator import (
    CORE_CATEGORIES,
    PERIPHERAL_CATEGORIES,
    ResolvedComponent,
)


@dataclass(frozen=True)
class ToolCatalogResult:
    """Slim result for the agentic tool loop — no URLs, minimal data."""

    id: int
    brand: str
    model: str
    specs: dict[str, str]  # filtered by CATEGORY_SPEC_KEYS
    price_eur: float  # MIN(price) across all stores


# Per-category spec keys to show in tool results
CATEGORY_SPEC_KEYS: dict[str, list[str]] = {
    "cpu": ["socket", "cores", "threads", "boost_ghz", "tdp", "integrated_graphics"],
    "gpu": ["vram_gb", "tdp", "length_mm"],
    "motherboard": ["socket", "chipset", "form_factor", "ddr_type"],
    "ram": ["ddr_type", "capacity_gb", "speed_mhz", "modules"],
    "storage": ["type", "capacity_gb", "interface", "read_mbps"],
    "psu": ["wattage", "efficiency"],
    "case": ["form_factor", "max_gpu_length"],
    "cooling": ["type", "radiator_mm", "socket_support"],
    "monitor": ["resolution", "size_inches", "panel", "refresh_hz"],
    "keyboard": ["type", "switch", "layout"],
    "mouse": ["sensor", "weight_g", "wireless"],
}


# Category lists derived from the single source of truth in build_validator
_CORE_CATEGORIES = [
    ComponentCategory(c) for c in CORE_CATEGORIES
]

_PERIPHERAL_CATEGORIES = [
    ComponentCategory(c) for c in PERIPHERAL_CATEGORIES
]

# Socket values used in the seed data
_AMD_SOCKETS = ["AM5", "AM4"]
_INTEL_SOCKETS = ["LGA1851", "LGA1700"]


class CatalogService:
    """Query the component catalog for candidates matching a BuildRequest."""

    # ------------------------------------------------------------------
    # New agentic tool-loop methods
    # ------------------------------------------------------------------

    async def scout_all(
        self,
        db: AsyncSession,
        categories: list[str],
        limit_per_category: int = 50,
    ) -> dict[str, list[ToolCatalogResult]]:
        """Scout all requested categories sequentially.

        Returns up to `limit_per_category` products per category,
        sorted by price ascending, deduped at Component level (MIN price
        across all shops).

        Note: uses a sequential loop (not asyncio.gather) because
        AsyncSession is not safe for concurrent use.
        """
        result: dict[str, list[ToolCatalogResult]] = {}
        for cat in categories:
            result[cat] = await self.query_for_tool(
                db, category=cat, limit=limit_per_category
            )
        return result

    async def query_for_tool(
        self,
        db: AsyncSession,
        category: str,
        brand: str | None = None,
        socket: str | None = None,
        form_factor: str | None = None,
        ddr_type: str | None = None,
        cooling_type: str | None = None,
        limit: int = 15,
    ) -> list[ToolCatalogResult]:
        """Query catalog for a single category with optional filters.

        Returns slim results (no URLs) sorted by cheapest price, deduped
        across shops (Component-level, MIN price).
        """
        stmt = (
            select(
                Component,
                func.min(AffiliateLink.price_eur).label("min_price"),
            )
            .join(AffiliateLink, AffiliateLink.component_id == Component.id)
            .where(
                and_(
                    Component.category == category,
                    Component.in_stock.is_(True),
                )
            )
            .group_by(Component.id)
            .order_by(func.min(AffiliateLink.price_eur).asc())
            .limit(limit)
        )

        # Optional filters (all case-insensitive to handle LLM casing variance)
        if brand:
            stmt = stmt.where(func.lower(Component.brand) == brand.lower())
        if socket:
            stmt = stmt.where(
                func.lower(Component.specs["socket"].astext) == socket.lower()
            )
        if form_factor:
            stmt = stmt.where(
                func.lower(Component.specs["form_factor"].astext)
                == form_factor.lower()
            )
        if ddr_type:
            stmt = stmt.where(
                func.lower(Component.specs["ddr_type"].astext) == ddr_type.lower()
            )
        if cooling_type:
            stmt = stmt.where(
                func.lower(Component.specs["type"].astext) == cooling_type.lower()
            )

        rows = (await db.execute(stmt)).all()

        spec_keys = CATEGORY_SPEC_KEYS.get(category, [])
        results = []
        for row in rows:
            comp = row[0]
            min_price = row[1]
            filtered_specs = {
                k: str(v) for k, v in comp.specs.items() if k in spec_keys
            }
            results.append(
                ToolCatalogResult(
                    id=comp.id,
                    brand=comp.brand,
                    model=comp.model,
                    specs=filtered_specs,
                    price_eur=float(min_price),
                )
            )
        return results

    async def resolve_components(
        self,
        db: AsyncSession,
        component_ids: list[int],
    ) -> dict[int, ResolvedComponent]:
        """Load components by ID and resolve cheapest affiliate link.

        Raises ValueError if any ID not found or has no affiliate links.
        """
        stmt = (
            select(Component)
            .options(selectinload(Component.affiliate_links))
            .where(Component.id.in_(component_ids))
        )
        rows = (await db.execute(stmt)).scalars().all()

        found = {comp.id: comp for comp in rows}
        missing = set(component_ids) - set(found.keys())
        if missing:
            raise ValueError(f"Component IDs not found: {sorted(missing)}")

        result: dict[int, ResolvedComponent] = {}
        for comp_id, comp in found.items():
            links = sorted(comp.affiliate_links, key=lambda al: al.price_eur)
            if not links:
                raise ValueError(
                    f"Component {comp_id} ({comp.brand} {comp.model}) "
                    f"has no affiliate links"
                )
            cheapest = links[0]
            spec_keys = CATEGORY_SPEC_KEYS.get(comp.category, [])
            filtered_specs = {
                k: str(v) for k, v in comp.specs.items() if k in spec_keys
            }
            result[comp_id] = ResolvedComponent(
                id=comp.id,
                category=comp.category,
                brand=comp.brand,
                model=comp.model,
                specs=filtered_specs,
                price_eur=cheapest.price_eur,
                affiliate_url=cheapest.url,
                affiliate_source=cheapest.store,
            )
        return result



@lru_cache(maxsize=1)
def get_catalog_service() -> CatalogService:
    return CatalogService()
