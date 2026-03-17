from functools import lru_cache
from pathlib import Path

import yaml

SECTIONS_DIR = Path(__file__).parent / "sections"

# Order in which sections appear in the final build system prompt
SECTION_ORDER = [
    "identity",
    "budget_ranges",
    "goals",
    "stores",
    "candidate_selection",
    "rules",
    "compatibility",
]


@lru_cache(maxsize=1)
def build_system_prompt() -> str:
    # Cached for the process lifetime — restart the container to pick up YAML changes.
    parts = []
    for name in SECTION_ORDER:
        path = SECTIONS_DIR / f"{name}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        parts.append(data["content"].strip())
    return "\n\n".join(parts)


@lru_cache(maxsize=1)
def search_system_prompt() -> str:
    # Cached for the process lifetime — restart the container to pick up YAML changes.
    path = Path(__file__).parent / "search.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["content"].strip()
