"""SQLAlchemy implementation of the engine's CatalogPort.

Maps ORM Component + AffiliateLink rows to engine ProductRecord dataclasses.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AffiliateLink, Component
from engine.models.types import ListingRecord, ProductRecord


class SqlAlchemyCatalogAdapter:
    """Implements engine.ports.CatalogPort using SQLAlchemy."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_all_products(
        self, category: str | None = None
    ) -> list[ProductRecord]:
        """Fetch all in-stock products with their affiliate links."""
        stmt = (
            select(Component)
            .where(Component.in_stock.is_(True))
            .options(selectinload(Component.affiliate_links))
        )
        if category:
            stmt = stmt.where(Component.category == category)

        result = await self._db.execute(stmt)
        components = result.scalars().all()

        products: list[ProductRecord] = []
        for comp in components:
            listings = [
                ListingRecord(
                    component_id=link.component_id,
                    store=link.store,
                    price_eur=link.price_eur,
                    affiliate_url=link.url,
                )
                for link in comp.affiliate_links
                if link.price_eur and link.price_eur > 0
            ]
            # Skip products with no valid listings
            if not listings:
                continue

            products.append(
                ProductRecord(
                    id=comp.id,
                    category=comp.category,
                    brand=comp.brand,
                    model=comp.model,
                    normalized_model=comp.normalized_model or comp.model,
                    specs=comp.specs or {},
                    listings=listings,
                )
            )

        return products
