"""Seed the component catalog with real products and Amazon.de affiliate links.

Run via:  uv run python -m app.db.seed
Or:       make seed
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import init_db
from app.db.models import AffiliateLink, Component

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Amazon.de affiliate tag — appended to all URLs
# ---------------------------------------------------------------------------
_AMAZON_TAG = "thepccoach-21"

# Path to scraped product catalog (all core categories combined)
_CATALOG_JSON = Path(__file__).parent / "all_products.json"


def _amazon_url(asin: str) -> str:
    """Build an Amazon.de affiliate product URL from an ASIN."""
    return f"https://www.amazon.de/dp/{asin}?tag={_AMAZON_TAG}"


def _load_catalog() -> list[dict]:
    """Load scraped products from JSON and append peripheral seed data."""
    with open(_CATALOG_JSON) as f:
        data = json.load(f)
    products = data["products"]
    products.extend(_PERIPHERAL_COMPONENTS)
    return products


# ---------------------------------------------------------------------------
# Peripheral seed data — monitors, keyboards, mice
# Not yet scraped; manually curated with real ASINs and prices.
# ---------------------------------------------------------------------------

_PERIPHERAL_COMPONENTS: list[dict] = [
    # ===== Monitors =====
    {
        "category": "monitor",
        "brand": "LG",
        "model": '27GP850-B 27" 1440p 165Hz IPS',
        "specs": {
            "resolution": "2560x1440",
            "size_inches": "27",
            "panel": "IPS",
            "refresh_hz": "165",
            "response_ms": "1",
        },
        "links": [{"store": "amazon", "asin": "B09QG3SJG3", "price_eur": 279.00}],
    },
    {
        "category": "monitor",
        "brand": "Dell",
        "model": 'S2722DGM 27" 1440p 165Hz VA Curved',
        "specs": {
            "resolution": "2560x1440",
            "size_inches": "27",
            "panel": "VA",
            "refresh_hz": "165",
            "response_ms": "1",
        },
        "links": [{"store": "amazon", "asin": "B09PVZD74D", "price_eur": 249.00}],
    },
    {
        "category": "monitor",
        "brand": "ASUS",
        "model": 'VG27AQ1A 27" 1440p 170Hz IPS',
        "specs": {
            "resolution": "2560x1440",
            "size_inches": "27",
            "panel": "IPS",
            "refresh_hz": "170",
            "response_ms": "1",
        },
        "links": [{"store": "amazon", "asin": "B09GFL94HH", "price_eur": 269.00}],
    },
    {
        "category": "monitor",
        "brand": "LG",
        "model": '24GS60F 24" 1080p 180Hz IPS',
        "specs": {
            "resolution": "1920x1080",
            "size_inches": "24",
            "panel": "IPS",
            "refresh_hz": "180",
            "response_ms": "1",
        },
        "links": [{"store": "amazon", "asin": "B0D2C1FJPB", "price_eur": 139.00}],
    },
    {
        "category": "monitor",
        "brand": "Samsung",
        "model": 'Odyssey G7 S28BG702 28" 4K 144Hz IPS',
        "specs": {
            "resolution": "3840x2160",
            "size_inches": "28",
            "panel": "IPS",
            "refresh_hz": "144",
            "response_ms": "1",
        },
        "links": [{"store": "amazon", "asin": "B0B3H4SK6C", "price_eur": 449.00}],
    },
    # ===== Keyboards =====
    {
        "category": "keyboard",
        "brand": "Logitech",
        "model": "G413 SE Mechanical",
        "specs": {
            "type": "mechanical",
            "switch": "tactile",
            "layout": "full",
            "backlight": "white",
        },
        "links": [{"store": "amazon", "asin": "B09ZK3R3QN", "price_eur": 49.00}],
    },
    {
        "category": "keyboard",
        "brand": "Corsair",
        "model": "K60 PRO TKL RGB",
        "specs": {
            "type": "mechanical",
            "switch": "Corsair OPX",
            "layout": "TKL",
            "backlight": "RGB",
        },
        "links": [{"store": "amazon", "asin": "B0CJZRFWPN", "price_eur": 69.00}],
    },
    {
        "category": "keyboard",
        "brand": "HyperX",
        "model": "Alloy Origins Core TKL",
        "specs": {
            "type": "mechanical",
            "switch": "HyperX Red",
            "layout": "TKL",
            "backlight": "RGB",
        },
        "links": [{"store": "amazon", "asin": "B07YMN61NS", "price_eur": 59.00}],
    },
    # ===== Mice =====
    {
        "category": "mouse",
        "brand": "Logitech",
        "model": "G502 X LIGHTSPEED",
        "specs": {
            "sensor": "HERO 25K",
            "weight_g": "102",
            "wireless": "yes",
            "dpi_max": "25600",
        },
        "links": [{"store": "amazon", "asin": "B0B18GMV71", "price_eur": 89.00}],
    },
    {
        "category": "mouse",
        "brand": "Logitech",
        "model": "G305 LIGHTSPEED",
        "specs": {
            "sensor": "HERO 12K",
            "weight_g": "99",
            "wireless": "yes",
            "dpi_max": "12000",
        },
        "links": [{"store": "amazon", "asin": "B07CMS5Q6P", "price_eur": 39.00}],
    },
    {
        "category": "mouse",
        "brand": "Razer",
        "model": "DeathAdder V3",
        "specs": {
            "sensor": "Focus Pro 30K",
            "weight_g": "59",
            "wireless": "no",
            "dpi_max": "30000",
        },
        "links": [{"store": "amazon", "asin": "B0CY65WFVH", "price_eur": 69.00}],
    },
    {
        "category": "mouse",
        "brand": "SteelSeries",
        "model": "Rival 3",
        "specs": {
            "sensor": "TrueMove Core",
            "weight_g": "77",
            "wireless": "no",
            "dpi_max": "8500",
        },
        "links": [{"store": "amazon", "asin": "B07THJKG53", "price_eur": 29.00}],
    },
]


async def seed_catalog(db: AsyncSession) -> None:
    """Insert seed components and affiliate links. Skips if catalog already has data."""
    count = (await db.execute(text("SELECT count(*) FROM components"))).scalar()
    if count and count > 0:
        log.info("Catalog already has %d components — skipping seed.", count)
        return

    products = _load_catalog()
    log.info("Seeding %d components...", len(products))

    for item in products:
        component = Component(
            category=item["category"],
            brand=item["brand"],
            model=item["model"],
            specs=item["specs"],
            in_stock=True,
        )
        db.add(component)
        await db.flush()  # get component.id

        for link in item["links"]:
            db.add(
                AffiliateLink(
                    component_id=component.id,
                    store=link["store"],
                    url=_amazon_url(link["asin"]),
                    price_eur=link["price_eur"],
                )
            )

    await db.commit()
    log.info("Seeded %d components with affiliate links.", len(products))


async def _main() -> None:
    """Entry point for `python -m app.db.seed`."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    init_db()

    from app.database import get_db

    async for db in get_db():
        await seed_catalog(db)


if __name__ == "__main__":
    asyncio.run(_main())
