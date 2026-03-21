"""Abstract interface for catalog data access.

The engine needs product data but must not depend on any specific database
or ORM. The backend provides a concrete implementation using SQLAlchemy;
tests use a simple in-memory mock.
"""

from __future__ import annotations

from typing import Protocol

from engine.models.types import ProductRecord


class CatalogPort(Protocol):
    """Abstract interface for catalog data access."""

    async def get_all_products(
        self, category: str | None = None
    ) -> list[ProductRecord]:
        """Fetch all in-stock products, optionally filtered by category.

        Each ProductRecord must include all listings (affiliate links)
        merged from all stores. Products with zero listings should be
        excluded.
        """
        ...
