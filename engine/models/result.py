"""Engine output contract — the build engine's public result type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SelectedComponent:
    """A single component selected by the engine."""

    component_id: int
    category: str
    brand: str
    model: str
    specs: dict[str, Any]
    price_eur: float
    store: str
    affiliate_url: str


@dataclass
class BuildEngineResult:
    """Complete output of the build selection engine."""

    components: dict[str, SelectedComponent]  # category → selection
    upgrade_candidate: SelectedComponent | None
    downgrade_candidate: SelectedComponent | None
    upgrade_category: str | None
    downgrade_category: str | None
    family_used: str  # e.g. "AM5_DDR5"
    total_price_eur: float
    budget_utilization: float  # 0.0–1.0
    metadata: dict[str, Any] = field(default_factory=dict)
