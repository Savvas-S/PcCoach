"""Shared test fixtures for engine tests.

Provides a MockCatalogAdapter and sample product data that mirrors
the real catalog structure without any database dependency.
"""

from __future__ import annotations

import pytest

from engine.models.types import ListingRecord, ProductRecord


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def make_listing(
    component_id: int,
    store: str = "amazon",
    price_eur: float = 100.0,
    affiliate_url: str = "https://www.amazon.de/dp/TEST?tag=thepccoach-21",
) -> ListingRecord:
    return ListingRecord(
        component_id=component_id,
        store=store,
        price_eur=price_eur,
        affiliate_url=affiliate_url,
    )


def make_product(
    id: int,
    category: str,
    brand: str,
    model: str,
    specs: dict | None = None,
    price_eur: float = 100.0,
    normalized_model: str | None = None,
    listings: list[ListingRecord] | None = None,
) -> ProductRecord:
    if listings is None:
        listings = [make_listing(component_id=id, price_eur=price_eur)]
    return ProductRecord(
        id=id,
        category=category,
        brand=brand,
        model=model,
        normalized_model=normalized_model or model,
        specs=specs or {},
        listings=listings,
    )


# ---------------------------------------------------------------------------
# Mock CatalogPort
# ---------------------------------------------------------------------------


class MockCatalogAdapter:
    """In-memory CatalogPort implementation for tests."""

    def __init__(self, products: list[ProductRecord] | None = None):
        self._products = products or []

    async def get_all_products(
        self, category: str | None = None
    ) -> list[ProductRecord]:
        if category:
            return [p for p in self._products if p.category == category]
        return list(self._products)


# ---------------------------------------------------------------------------
# Sample product catalog fixture
# ---------------------------------------------------------------------------

# fmt: off
SAMPLE_PRODUCTS: list[ProductRecord] = [
    # CPUs
    make_product(1, "cpu", "AMD", "Ryzen 5 5600X", {"socket": "AM4", "cores": "6", "threads": "12", "tdp": "65", "boost_ghz": "4.6"}, 140),
    make_product(2, "cpu", "AMD", "Ryzen 7 7800X3D", {"socket": "AM5", "cores": "8", "threads": "16", "tdp": "120", "boost_ghz": "5.0"}, 350),
    make_product(3, "cpu", "Intel", "Core i5-12400F", {"socket": "LGA1700", "cores": "6", "threads": "12", "tdp": "65", "boost_ghz": "4.4"}, 130),
    # Motherboards
    make_product(10, "motherboard", "MSI", "B550-A PRO", {"socket": "AM4", "chipset": "AMD B550", "form_factor": "ATX", "ddr_type": "DDR4"}, 100),
    make_product(11, "motherboard", "ASUS", "TUF Gaming B650-PLUS WiFi", {"socket": "AM5", "chipset": "AMD B650", "form_factor": "ATX", "ddr_type": "DDR5"}, 155),
    make_product(12, "motherboard", "MSI", "B760 Gaming Plus WiFi", {"socket": "LGA1700", "chipset": "Intel B760", "form_factor": "ATX", "ddr_type": "DDR5"}, 115),
    # RAM
    make_product(20, "ram", "Corsair", "Vengeance LPX 16GB DDR4 3200MHz", {"ddr_type": "DDR4", "capacity_gb": "16", "speed_mhz": "3200", "modules": "2"}, 145),
    make_product(21, "ram", "Corsair", "Vengeance DDR5 32GB 6000MHz", {"ddr_type": "DDR5", "capacity_gb": "32", "speed_mhz": "6000", "modules": "2"}, 430),
    make_product(22, "ram", "Kingston", "FURY Beast DDR5 32GB 6000MHz", {"ddr_type": "DDR5", "capacity_gb": "32", "speed_mhz": "6000", "modules": "2"}, 425),
    # GPUs (family-independent)
    make_product(30, "gpu", "NVIDIA", "RTX 4060 8GB", {"vram_gb": "8", "tdp": "115", "length_mm": "240"}, 260),
    make_product(31, "gpu", "NVIDIA", "RTX 5070 12GB", {"vram_gb": "12", "tdp": "250", "length_mm": "305"}, 600),
    make_product(32, "gpu", "AMD", "RX 7600 8GB", {"vram_gb": "8", "tdp": "165", "length_mm": "267"}, 260),
    # Storage (family-independent)
    make_product(40, "storage", "Samsung", "990 EVO Plus 1TB", {"type": "NVMe", "capacity_gb": "1000", "interface": "PCIe 5.0 x2", "read_mbps": "7250"}, 150),
    make_product(41, "storage", "Crucial", "P310 2TB", {"type": "NVMe", "capacity_gb": "2000", "interface": "PCIe 4.0 x4", "read_mbps": "7100"}, 250),
    # PSUs (family-independent)
    make_product(50, "psu", "be quiet!", "Pure Power 12 650W", {"wattage": "650", "efficiency": "80 Plus Gold"}, 75),
    make_product(51, "psu", "Corsair", "RM750e 750W", {"wattage": "750", "efficiency": "80 Plus Gold"}, 85),
    make_product(52, "psu", "be quiet!", "Pure Power 12 850W", {"wattage": "850", "efficiency": "80 Plus Gold"}, 85),
    # Cases (family-independent)
    make_product(60, "case", "MSI", "MAG Forge 320R Airflow", {"form_factor": "ATX"}, 60),
    make_product(61, "case", "Corsair", "3000D Airflow", {"form_factor": "ATX"}, 70),
    # Cooling
    make_product(70, "cooling", "Thermalright", "Peerless Assassin 120 SE", {"type": "air"}, 35),
    make_product(71, "cooling", "Arctic", "Liquid Freezer III Pro 240mm", {"type": "liquid", "radiator_mm": "240"}, 70),
]
# fmt: on


@pytest.fixture
def sample_products() -> list[ProductRecord]:
    return list(SAMPLE_PRODUCTS)


@pytest.fixture
def mock_catalog() -> MockCatalogAdapter:
    return MockCatalogAdapter(SAMPLE_PRODUCTS)
