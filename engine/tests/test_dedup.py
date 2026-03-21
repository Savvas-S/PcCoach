"""Tests for product deduplication logic."""

from engine.core.dedup import deduplicate
from engine.models.types import ListingRecord, ProductRecord
from engine.tests.conftest import make_listing, make_product


def test_no_duplicates_unchanged():
    """Products with no duplicates pass through unchanged."""
    products = [
        make_product(1, "cpu", "AMD", "Ryzen 5 5600X", price_eur=140),
        make_product(2, "gpu", "NVIDIA", "RTX 4060", price_eur=260),
    ]
    result = deduplicate(products)
    assert len(result) == 2


def test_same_product_two_stores_merged():
    """Same product from two stores merges into one with both listings."""
    p1 = ProductRecord(
        id=1,
        category="gpu",
        brand="NVIDIA",
        model="RTX 5070 12GB",
        normalized_model="RTX 5070",
        specs={"vram_gb": "12"},
        listings=[make_listing(1, "amazon", 600)],
    )
    p2 = ProductRecord(
        id=2,
        category="gpu",
        brand="NVIDIA",
        model="RTX 5070 12GB OC",
        normalized_model="RTX 5070",
        specs={"vram_gb": "12"},
        listings=[make_listing(2, "caseking", 580)],
    )
    result = deduplicate([p1, p2])
    assert len(result) == 1
    assert len(result[0].listings) == 2
    # Cheapest listing is from caseking
    assert result[0].best_price == 580


def test_different_products_not_merged():
    """Different models from same brand are NOT merged."""
    p1 = make_product(1, "gpu", "NVIDIA", "RTX 4060", normalized_model="RTX 4060", price_eur=260)
    p2 = make_product(2, "gpu", "NVIDIA", "RTX 5070", normalized_model="RTX 5070", price_eur=600)
    result = deduplicate([p1, p2])
    assert len(result) == 2


def test_case_insensitive_matching():
    """Dedup is case-insensitive on brand and normalized_model."""
    p1 = make_product(1, "cpu", "AMD", "Ryzen 5 5600X", normalized_model="Ryzen 5 5600X", price_eur=140)
    p2 = make_product(2, "cpu", "amd", "Ryzen 5 5600X", normalized_model="ryzen 5 5600x", price_eur=135)
    result = deduplicate([p1, p2])
    assert len(result) == 1
    assert len(result[0].listings) == 2


def test_different_categories_not_merged():
    """Same model name in different categories stays separate."""
    p1 = make_product(1, "cpu", "Test", "Model A", normalized_model="model a", price_eur=100)
    p2 = make_product(2, "gpu", "Test", "Model A", normalized_model="model a", price_eur=200)
    result = deduplicate([p1, p2])
    assert len(result) == 2


def test_products_without_listings_excluded():
    """Products with zero listings are filtered out."""
    p1 = ProductRecord(
        id=1,
        category="gpu",
        brand="NVIDIA",
        model="RTX 5090",
        normalized_model="RTX 5090",
        specs={},
        listings=[],
    )
    p2 = make_product(2, "gpu", "NVIDIA", "RTX 5070", price_eur=600)
    result = deduplicate([p1, p2])
    assert len(result) == 1
    assert result[0].model == "RTX 5070"


def test_listings_sorted_by_price():
    """Merged listings are sorted cheapest first."""
    p1 = ProductRecord(
        id=1,
        category="gpu",
        brand="NVIDIA",
        model="RTX 5070",
        normalized_model="RTX 5070",
        specs={},
        listings=[make_listing(1, "amazon", 620)],
    )
    p2 = ProductRecord(
        id=2,
        category="gpu",
        brand="NVIDIA",
        model="RTX 5070",
        normalized_model="RTX 5070",
        specs={},
        listings=[make_listing(2, "caseking", 580)],
    )
    result = deduplicate([p1, p2])
    assert result[0].listings[0].price_eur == 580
    assert result[0].listings[1].price_eur == 620


def test_duplicate_listing_ids_deduped():
    """Same (component_id, store) pair is not duplicated."""
    listing = make_listing(1, "amazon", 100)
    p1 = ProductRecord(
        id=1, category="cpu", brand="AMD", model="R5",
        normalized_model="R5", specs={}, listings=[listing],
    )
    p2 = ProductRecord(
        id=1, category="cpu", brand="AMD", model="R5",
        normalized_model="R5", specs={}, listings=[listing],
    )
    result = deduplicate([p1, p2])
    assert len(result) == 1
    assert len(result[0].listings) == 1


def test_empty_input():
    """Empty product list returns empty result."""
    assert deduplicate([]) == []


def test_three_stores_merged():
    """Product from three different stores merges into one."""
    base = {"category": "gpu", "brand": "NVIDIA", "model": "RTX 5070",
            "normalized_model": "RTX 5070", "specs": {}}
    p1 = ProductRecord(id=1, **base, listings=[make_listing(1, "amazon", 600)])
    p2 = ProductRecord(id=2, **base, listings=[make_listing(2, "caseking", 590)])
    p3 = ProductRecord(id=3, **base, listings=[make_listing(3, "computeruniverse", 595)])
    result = deduplicate([p1, p2, p3])
    assert len(result) == 1
    assert len(result[0].listings) == 3
    assert result[0].best_price == 590
