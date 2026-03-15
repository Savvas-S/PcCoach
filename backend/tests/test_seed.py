"""Tests for seed data integrity."""

from app.db.seed import _amazon_url, _load_catalog
from app.models.builder import _ALLOWED_AFFILIATE_HOSTS, ComponentCategory

# Load full catalog (scraped + peripherals)
SEED_COMPONENTS = _load_catalog()

# All valid category values
VALID_CATEGORIES = {c.value for c in ComponentCategory}

# Required spec keys per category for compatibility checks
REQUIRED_SPECS: dict[str, set[str]] = {
    "cpu": {"socket", "tdp"},
    "gpu": {"vram_gb", "tdp"},
    "motherboard": {"socket", "ddr_type", "form_factor"},
    "ram": {"ddr_type", "capacity_gb"},
    "psu": {"wattage"},
    "case": {"form_factor"},
    "cooling": {"type"},
    "storage": {"capacity_gb"},
}


def _label(item: dict) -> str:
    return f"{item['brand']} {item['model']}"


class TestSeedDataIntegrity:
    def test_all_categories_are_valid(self):
        for item in SEED_COMPONENTS:
            assert item["category"] in VALID_CATEGORIES, (
                f"Invalid category for {_label(item)}"
            )

    def test_all_prices_are_positive(self):
        for item in SEED_COMPONENTS:
            for link in item["links"]:
                assert link["price_eur"] > 0, f"Non-positive price for {_label(item)}"

    def test_all_affiliate_urls_pass_allowlist(self):
        from urllib.parse import urlparse

        for item in SEED_COMPONENTS:
            for link in item["links"]:
                url = _amazon_url(link["asin"])
                host = urlparse(url).hostname
                assert host in _ALLOWED_AFFILIATE_HOSTS, (
                    f"Bad host '{host}' for {_label(item)}"
                )

    def test_required_specs_per_category(self):
        for item in SEED_COMPONENTS:
            category = item["category"]
            required = REQUIRED_SPECS.get(category, set())
            specs = set(item["specs"].keys())
            missing = required - specs
            assert not missing, f"{_label(item)} ({category}) missing: {missing}"

    def test_every_component_has_at_least_one_link(self):
        for item in SEED_COMPONENTS:
            assert len(item["links"]) > 0, f"{_label(item)} has no affiliate links"

    def test_minimum_catalog_coverage(self):
        """Ensure the seed covers all core categories."""
        categories = {item["category"] for item in SEED_COMPONENTS}
        core = {
            "cpu",
            "gpu",
            "motherboard",
            "ram",
            "storage",
            "psu",
            "case",
            "cooling",
        }
        missing = core - categories
        assert not missing, f"Missing categories: {missing}"

    def test_each_category_has_multiple_options(self):
        """Each core category needs >= 3 options."""
        from collections import Counter

        counts = Counter(item["category"] for item in SEED_COMPONENTS)
        for cat in [
            "cpu",
            "gpu",
            "motherboard",
            "ram",
            "storage",
            "psu",
            "case",
            "cooling",
        ]:
            assert counts[cat] >= 3, f"'{cat}' has {counts[cat]} (need >= 3)"

    def test_all_stores_are_amazon(self):
        """MVP: only Amazon.de affiliate links."""
        for item in SEED_COMPONENTS:
            for link in item["links"]:
                assert link["store"] == "amazon", f"Non-Amazon store for {_label(item)}"

    def test_amazon_urls_contain_affiliate_tag(self):
        for item in SEED_COMPONENTS:
            for link in item["links"]:
                url = _amazon_url(link["asin"])
                assert "tag=thepccoach-21" in url, f"Missing tag for {_label(item)}"

    def test_no_duplicate_products(self):
        """No exact duplicates (same brand + model + category)."""
        seen = set()
        for item in SEED_COMPONENTS:
            key = (item["category"], item["brand"], item["model"])
            assert key not in seen, (
                f"Duplicate: {_label(item)} ({item['category']})"
            )
            seen.add(key)
