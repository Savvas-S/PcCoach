import asyncio
import logging
import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.models.builder import ComponentRecommendation

logger = logging.getLogger(__name__)

_TIMEOUT = 8.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Priority order for store selection
_STORE_PRIORITY = ["computeruniverse", "caseking", "amazon"]
_STORE_DOMAINS = {
    "computeruniverse": "computeruniverse.net",
    "caseking": "caseking.de",
    "amazon": "amazon.de",
}


async def _fetch(client: httpx.AsyncClient, url: str) -> BeautifulSoup | None:
    try:
        r = await client.get(url)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        logger.debug("Fetch failed %s: %s", url, e)
        return None


def _extract_real_url(href: str) -> str:
    """Unwrap geizhals redirect links to get the real store URL."""
    parsed = urlparse(href)
    params = parse_qs(parsed.query)
    for key in ("url", "ued"):
        if key in params:
            return unquote(params[key][0])
    return href


def _parse_price(text: str) -> float | None:
    text = text.replace("\xa0", "").strip()
    m = re.search(r"(\d[\d.]*,\d{2}|\d[\d,]*\.\d{2}|\d+)", text)
    if not m:
        return None
    raw = m.group(1)
    # European format: 1.299,99 → 1299.99
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        val = float(raw)
        return val if val > 0 else None
    except ValueError:
        return None


async def _find_product_page(client: httpx.AsyncClient, name: str) -> str | None:
    """Search geizhals.de and return the URL of the best matching product page."""
    search_url = f"https://geizhals.de/?fs={quote_plus(name)}&hloc=de"
    try:
        r = await client.get(search_url)
        r.raise_for_status()
    except Exception as e:
        logger.debug("Geizhals search failed for %r: %s", name, e)
        return None

    # Exact match: geizhals redirects straight to the product page
    if re.search(r"/a\d+\.html", str(r.url)):
        return str(r.url)

    soup = BeautifulSoup(r.text, "html.parser")
    selectors = [
        "a.productlist--name",
        "h3.productlist-name a",
        "article a[href*='/a']",
        "a[href$='.html'][href*='/a']",
    ]
    for sel in selectors:
        tag = soup.select_one(sel)
        if tag and tag.get("href"):
            href = tag["href"]
            return f"https://geizhals.de{href}" if href.startswith("/") else href

    return None


async def _get_store_offers(
    client: httpx.AsyncClient, product_url: str
) -> dict[str, tuple[str, float | None]]:
    """Parse a geizhals product page and return {store: (url, price)} for target stores."""
    soup = await _fetch(client, product_url)
    if not soup:
        return {}

    results: dict[str, tuple[str, float | None]] = {}

    # Geizhals offer rows — try known selectors, fall back to all table rows
    offer_rows = soup.select("tr.offer, .offer-list__row, tr[id^='offer']")
    if not offer_rows:
        offer_rows = soup.select("table tr")

    for row in offer_rows:
        row_text = row.get_text(" ", strip=True).lower()
        for store_key, domain in _STORE_DOMAINS.items():
            if store_key in results:
                continue
            if domain.split(".")[0] not in row_text:
                continue

            # Find the outbound link for this store
            link = (
                row.select_one(f"a[href*='{domain}']")
                or row.select_one("a[href*='url='], a[href*='ued=']")
                or row.select_one("a[href]")
            )
            if not link:
                continue

            real_url = _extract_real_url(link["href"])
            if not real_url.startswith("http"):
                real_url = f"https://geizhals.de{real_url}"

            price_tag = row.select_one("[class*='price'], strong, .price")
            price = _parse_price(price_tag.get_text()) if price_tag else None

            results[store_key] = (real_url, price)

    return results


async def _enrich_one(
    client: httpx.AsyncClient, c: ComponentRecommendation
) -> ComponentRecommendation:
    try:
        product_page = await _find_product_page(client, c.name)
        if not product_page:
            return c

        offers = await _get_store_offers(client, product_page)
        if not offers:
            return c

        # Prefer the store Claude already chose; otherwise pick by priority
        chosen = c.affiliate_source if c.affiliate_source in offers else next(
            (s for s in _STORE_PRIORITY if s in offers), None
        )
        if not chosen:
            return c

        url, price = offers[chosen]
        updates: dict = {"affiliate_url": url, "affiliate_source": chosen}
        if price:
            updates["price_eur"] = price

        return ComponentRecommendation.model_validate(
            {**c.model_dump(mode="json"), **updates}
        )
    except Exception as e:
        logger.warning("Enrichment failed for %r: %s", c.name, e)
        return c


async def enrich_components(
    components: list[ComponentRecommendation],
) -> list[ComponentRecommendation]:
    """Placeholder — not currently called. Intended to replace search URLs with real
    product URLs via geizhals.de once bot protection is resolved or a paid scraping
    service / affiliate product feed is integrated."""
    async with httpx.AsyncClient(
        headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True
    ) as client:
        return list(await asyncio.gather(*[_enrich_one(client, c) for c in components]))
