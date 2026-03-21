"""User notes pattern extraction — zero LLM cost.

Extracts structured preferences from free-text user notes using regex.
Output feeds into the scoring/selection algorithm as preference hints.
"""

from __future__ import annotations

import re

from engine.models.types import NotesPreferences

# Brand patterns (case-insensitive)
_BRAND_PATTERNS = [
    r"\b(nvidia|geforce|rtx|gtx)\b",
    r"\b(amd|radeon|ryzen)\b",
    r"\b(intel|core\s+i[3579]|core\s+ultra)\b",
    r"\b(corsair)\b",
    r"\b(samsung)\b",
    r"\b(crucial)\b",
    r"\b(kingston)\b",
    r"\b(asus|rog)\b",
    r"\b(msi)\b",
    r"\b(gigabyte|aorus)\b",
    r"\b(nzxt)\b",
    r"\b(be\s*quiet|bequiet)\b",
    r"\b(fractal)\b",
    r"\b(arctic)\b",
    r"\b(thermalright)\b",
    r"\b(noctua)\b",
]

# Map regex matches to canonical brand names
_BRAND_MAP = {
    "nvidia": "NVIDIA",
    "geforce": "NVIDIA",
    "rtx": "NVIDIA",
    "gtx": "NVIDIA",
    "amd": "AMD",
    "radeon": "AMD",
    "ryzen": "AMD",
    "intel": "Intel",
    "corsair": "Corsair",
    "samsung": "Samsung",
    "crucial": "Crucial",
    "kingston": "Kingston",
    "asus": "ASUS",
    "rog": "ASUS",
    "msi": "MSI",
    "gigabyte": "Gigabyte",
    "aorus": "Gigabyte",
    "nzxt": "NZXT",
    "noctua": "Noctua",
    "arctic": "Arctic",
    "thermalright": "Thermalright",
    "fractal": "Fractal Design",
}

# Resolution patterns
_RESOLUTION_PATTERNS = [
    (r"\b4k\b", "4K"),
    (r"\b2160p\b", "4K"),
    (r"\b1440p\b", "1440p"),
    (r"\b2k\b", "1440p"),
    (r"\bqhd\b", "1440p"),
    (r"\b1080p\b", "1080p"),
    (r"\bfull\s*hd\b", "1080p"),
    (r"\bfhd\b", "1080p"),
]

# Specific model name patterns
_MODEL_PATTERNS = [
    r"\b(rtx\s*\d{4}\s*(?:ti|super)?)\b",
    r"\b(rx\s*\d{4}\s*(?:xt)?)\b",
    r"\b(ryzen\s*\d\s*\d{4}x?3?d?)\b",
    r"\b(core\s*(?:i[3579]|ultra\s*[579])\s*[\w-]*)\b",
]

# Keywords that might affect selection
_KEYWORD_PATTERNS = [
    (r"\bsilent\b", "silent"),
    (r"\bquiet\b", "quiet"),
    (r"\brgb\b", "rgb"),
    (r"\bcompact\b", "compact"),
    (r"\bsmall\b", "compact"),
    (r"\bwhite\b", "white"),
    (r"\bwifi\b", "wifi"),
    (r"\bfuture\s*proof\b", "future_proof"),
    (r"\bupgrad(?:e|able)\b", "upgradeable"),
    (r"\bovercloc\w*\b", "overclock"),
]


def parse_notes(notes: str | None) -> NotesPreferences:
    """Extract structured preferences from free-text user notes.

    Returns a NotesPreferences with extracted brands, resolution target,
    specific model references, and keywords. Used as hints during scoring
    — not hard constraints.
    """
    if not notes:
        return NotesPreferences()

    text = notes.lower()

    # Extract brands
    brands: list[str] = []
    seen_brands: set[str] = set()
    for pattern in _BRAND_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            key = match.group(1).lower().replace(" ", "")
            # Find canonical name
            for map_key, canonical in _BRAND_MAP.items():
                if map_key.replace(" ", "") == key or key.startswith(
                    map_key.replace(" ", "")
                ):
                    if canonical not in seen_brands:
                        seen_brands.add(canonical)
                        brands.append(canonical)
                    break

    # Extract resolution
    resolution: str | None = None
    for pattern, res in _RESOLUTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            resolution = res
            break

    # Extract specific model names
    models: list[str] = []
    for pattern in _MODEL_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            models.append(match.group(1).strip())

    # Extract keywords
    keywords: list[str] = []
    for pattern, keyword in _KEYWORD_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            keywords.append(keyword)

    return NotesPreferences(
        brands=brands,
        resolution=resolution,
        specific_models=models,
        keywords=keywords,
    )
