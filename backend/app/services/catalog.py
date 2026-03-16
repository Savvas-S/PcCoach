"""Catalog query service — fetches candidate components from the DB for Claude."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AffiliateLink, Component
from app.models.builder import (
    BuildRequest,
    ComponentCategory,
    CoolingPreference,
    CPUBrand,
    FormFactor,
    GPUBrand,
)
from app.services.build_validator import ResolvedComponent


@dataclass(frozen=True)
class StoreOption:
    store: str
    url: str
    price_eur: float


@dataclass(frozen=True)
class CandidateComponent:
    id: int
    category: str
    brand: str
    model: str
    specs: dict[str, str]
    stores: list[StoreOption]  # sorted cheapest-first

    @property
    def cheapest_price(self) -> float:
        """Cheapest store price (stores is always non-empty)."""
        return self.stores[0].price_eur


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


# Categories that Claude must always fill (unless excluded by existing_parts)
_CORE_CATEGORIES = [
    ComponentCategory.cpu,
    ComponentCategory.gpu,
    ComponentCategory.motherboard,
    ComponentCategory.ram,
    ComponentCategory.storage,
    ComponentCategory.psu,
    ComponentCategory.case,
    ComponentCategory.cooling,
]

_PERIPHERAL_CATEGORIES = [
    ComponentCategory.monitor,
    ComponentCategory.keyboard,
    ComponentCategory.mouse,
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

    # ------------------------------------------------------------------
    # Legacy methods (kept temporarily for transition)
    # ------------------------------------------------------------------

    async def get_candidates(
        self,
        db: AsyncSession,
        request: BuildRequest,
    ) -> dict[str, list[CandidateComponent]]:
        """Return candidates per category, pre-filtered by request."""
        categories = self._categories_needed(request)
        result: dict[str, list[CandidateComponent]] = {}

        for cat in categories:
            candidates = await self._query_category(db, cat.value, request)
            if candidates:
                result[cat.value] = candidates

        return result

    def _categories_needed(self, request: BuildRequest) -> list[ComponentCategory]:
        """Determine which categories to query based on request."""
        excluded = set(request.existing_parts)
        cats = [c for c in _CORE_CATEGORIES if c not in excluded]
        if request.include_peripherals:
            cats.extend(c for c in _PERIPHERAL_CATEGORIES if c not in excluded)
        return cats

    def _required_sockets(self, request: BuildRequest) -> list[str] | None:
        """Determine which CPU sockets to include based on brand preference."""
        if request.cpu_brand == CPUBrand.amd:
            return _AMD_SOCKETS
        if request.cpu_brand == CPUBrand.intel:
            return _INTEL_SOCKETS
        return None  # no preference → all sockets

    async def _query_category(
        self,
        db: AsyncSession,
        category: str,
        request: BuildRequest,
    ) -> list[CandidateComponent]:
        """Query a single category with appropriate filters."""
        stmt = (
            select(Component)
            .options(selectinload(Component.affiliate_links))
            .where(
                and_(
                    Component.category == category,
                    Component.in_stock.is_(True),
                )
            )
        )

        # Brand filters (case-insensitive)
        if category == "cpu" and request.cpu_brand != CPUBrand.no_preference:
            stmt = stmt.where(
                func.lower(Component.brand) == request.cpu_brand.value.lower()
            )

        if category == "gpu" and request.gpu_brand != GPUBrand.no_preference:
            stmt = stmt.where(
                func.lower(Component.brand) == request.gpu_brand.value.lower()
            )

        # Socket compatibility: motherboards must match CPU socket
        sockets = self._required_sockets(request)
        if sockets and category == "motherboard":
            stmt = stmt.where(Component.specs["socket"].astext.in_(sockets))

        # Cooling preference filter
        if (
            category == "cooling"
            and request.cooling_preference != CoolingPreference.no_preference
        ):
            cooling_type = request.cooling_preference.value
            stmt = stmt.where(Component.specs["type"].astext == cooling_type)

        # Form factor filter for cases
        if category == "case":
            allowed_ff = self._allowed_case_form_factors(request.form_factor)
            stmt = stmt.where(Component.specs["form_factor"].astext.in_(allowed_ff))

        # Form factor filter for motherboards
        if category == "motherboard":
            allowed_ff = self._allowed_mobo_form_factors(request.form_factor)
            stmt = stmt.where(Component.specs["form_factor"].astext.in_(allowed_ff))

        rows = (await db.execute(stmt)).scalars().all()
        return self._to_candidates(rows)

    def _allowed_case_form_factors(self, ff: FormFactor) -> list[str]:
        """Cases: ATX case fits all boards, mATX fits mATX+mITX boards, etc."""
        if ff == FormFactor.atx:
            return ["ATX"]
        if ff == FormFactor.micro_atx:
            return ["micro_atx", "ATX"]
        # mini_itx — can use mini_itx, micro_atx, or ATX cases
        return ["mini_itx", "micro_atx", "ATX"]

    def _allowed_mobo_form_factors(self, ff: FormFactor) -> list[str]:
        """Motherboards: must fit the chosen form factor (same or smaller)."""
        if ff == FormFactor.atx:
            return ["ATX", "micro_atx", "mini_itx"]
        if ff == FormFactor.micro_atx:
            return ["micro_atx", "mini_itx"]
        return ["mini_itx"]

    def _to_candidates(self, components: list[Component]) -> list[CandidateComponent]:
        """Convert ORM rows to CandidateComponent dataclasses."""
        candidates = []
        for comp in components:
            links = sorted(comp.affiliate_links, key=lambda al: al.price_eur)
            if not links:
                continue  # skip components with no affiliate links
            stores = [
                StoreOption(store=al.store, url=al.url, price_eur=al.price_eur)
                for al in links
            ]
            candidates.append(
                CandidateComponent(
                    id=comp.id,
                    category=comp.category,
                    brand=comp.brand,
                    model=comp.model,
                    specs=comp.specs,
                    stores=stores,
                )
            )
        # Sort by cheapest price
        candidates.sort(key=lambda c: c.cheapest_price)
        return candidates

    async def get_search_candidates(
        self,
        db: AsyncSession,
        category: str,
    ) -> list[CandidateComponent]:
        """Return all in-stock candidates for a single category (search endpoint)."""
        stmt = (
            select(Component)
            .options(selectinload(Component.affiliate_links))
            .where(
                and_(
                    Component.category == category,
                    Component.in_stock.is_(True),
                )
            )
        )
        rows = (await db.execute(stmt)).scalars().all()
        return self._to_candidates(rows)


@lru_cache(maxsize=1)
def get_catalog_service() -> CatalogService:
    return CatalogService()
