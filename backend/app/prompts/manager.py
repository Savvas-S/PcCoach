from functools import lru_cache
from pathlib import Path

import yaml

SECTIONS_DIR = Path(__file__).parent / "sections"

# Order in which sections appear in the final prompt
SECTION_ORDER = [
    "identity",
    "budget_ranges",
    "goals",
    "stores",
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
