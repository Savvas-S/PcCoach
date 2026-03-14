"""Catalog query service — fetches candidate components from the DB for Claude."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, select
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
        return self.stores[0].price_eur if self.stores else 0.0


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

# Map form factor enum values to the DB spec values
_FORM_FACTOR_MAP: dict[FormFactor, list[str]] = {
    FormFactor.atx: ["ATX"],
    FormFactor.micro_atx: ["micro_atx", "ATX"],  # mATX boards fit ATX cases too
    FormFactor.mini_itx: ["mini_itx", "micro_atx", "ATX"],
}


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

        # Brand filters
        if category == "cpu" and request.cpu_brand not in (CPUBrand.no_preference,):
            brand_map = {"intel": "Intel", "amd": "AMD"}
            stmt = stmt.where(Component.brand == brand_map[request.cpu_brand.value])

        if category == "gpu" and request.gpu_brand not in (GPUBrand.no_preference,):
            brand_map = {"nvidia": "NVIDIA", "amd": "AMD"}
            stmt = stmt.where(Component.brand == brand_map[request.gpu_brand.value])

        # Cooling preference filter
        if (
            category == "cooling"
            and request.cooling_preference != CoolingPreference.no_preference
        ):
            cooling_type = request.cooling_preference.value  # "air" or "liquid"
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
