"""Engine-internal data types — plain dataclasses, no ORM dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ListingRecord:
    """A single shop listing for a product (one product may have many)."""

    component_id: int
    store: str
    price_eur: float
    affiliate_url: str


@dataclass(frozen=True)
class ProductRecord:
    """A unique product with all its shop listings merged."""

    id: int
    category: str
    brand: str
    model: str
    normalized_model: str
    specs: dict[str, Any]
    listings: list[ListingRecord]

    @property
    def best_price(self) -> float:
        """Cheapest listing price. Raises if no listings."""
        if not self.listings:
            raise ValueError(f"No listings for {self.brand} {self.model}")
        return min(l.price_eur for l in self.listings)

    @property
    def best_listing(self) -> ListingRecord:
        """Cheapest listing. Raises if no listings."""
        if not self.listings:
            raise ValueError(f"No listings for {self.brand} {self.model}")
        return min(self.listings, key=lambda l: l.price_eur)


@dataclass(frozen=True)
class CompatibilityFamily:
    """A group of products guaranteed to be cross-compatible.

    Defined by (socket, ddr_type). All family-bound products share these.
    """

    socket: str
    ddr_type: str
    cpus: list[ProductRecord]
    motherboards: list[ProductRecord]
    ram: list[ProductRecord]
    coolers: list[ProductRecord]

    @property
    def name(self) -> str:
        return f"{self.socket}_{self.ddr_type}"

    def pool(self, category: str) -> list[ProductRecord]:
        """Get the product pool for a family-bound category."""
        return {
            "cpu": self.cpus,
            "motherboard": self.motherboards,
            "ram": self.ram,
            "cooling": self.coolers,
        }.get(category, [])


@dataclass(frozen=True)
class ScoredProduct:
    """A product with its computed scores."""

    product: ProductRecord
    spec_score: float
    price_score: float
    tier_score: float
    total_score: float


@dataclass(frozen=True)
class NotesPreferences:
    """Structured preferences extracted from user notes."""

    brands: list[str] = field(default_factory=list)
    resolution: str | None = None
    specific_models: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
