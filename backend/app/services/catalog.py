"""Catalog query service — fetches candidate components from the DB for Claude."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Component
from app.models.builder import (
    BuildRequest,
    ComponentCategory,
    CoolingPreference,
    CPUBrand,
    FormFactor,
    GPUBrand,
)


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
