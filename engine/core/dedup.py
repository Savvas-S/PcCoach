"""Product deduplication across multiple shop listings.

When the same physical product appears from multiple stores, each store
creates a separate DB record. This module merges them into a single
ProductRecord with all listings combined, so the selection algorithm
works on unique products and picks the cheapest listing post-selection.
"""

from __future__ import annotations

from engine.models.types import ProductRecord


def deduplicate(products: list[ProductRecord]) -> list[ProductRecord]:
    """Merge products that represent the same physical item.

    Groups by (category, brand, normalized_model) and combines listings
    from all matching records. Returns a new list of deduplicated
    ProductRecords, each with merged listings sorted by price.

    Products with zero listings after merge are excluded.
    """
    groups: dict[tuple[str, str, str], list[ProductRecord]] = {}

    for p in products:
        key = (p.category, p.brand.lower(), p.normalized_model.lower())
        groups.setdefault(key, []).append(p)

    result: list[ProductRecord] = []
    for group in groups.values():
        if not group:
            continue

        # Use the first record as the canonical product
        canonical = group[0]

        # Merge all listings, dedup by (component_id, store)
        seen: set[tuple[int, str]] = set()
        merged_listings = []
        for p in group:
            for listing in p.listings:
                lid = (listing.component_id, listing.store)
                if lid not in seen:
                    seen.add(lid)
                    merged_listings.append(listing)

        # Sort by price ascending
        merged_listings.sort(key=lambda l: l.price_eur)

        if not merged_listings:
            continue

        merged = ProductRecord(
            id=canonical.id,
            category=canonical.category,
            brand=canonical.brand,
            model=canonical.model,
            normalized_model=canonical.normalized_model,
            specs=canonical.specs,
            listings=merged_listings,
        )
        result.append(merged)

    return result
