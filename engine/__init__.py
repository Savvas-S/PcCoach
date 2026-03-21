"""PcCoach Build Engine — deterministic PC build selection.

Public API:
    select_build()       — Main entry point for build selection
    BuildEngineResult    — Output type
    SelectedComponent    — Per-category selection
    CatalogPort          — Interface for catalog data access
"""

from engine.models.result import BuildEngineResult, SelectedComponent
from engine.ports import CatalogPort

__all__ = [
    "BuildEngineResult",
    "CatalogPort",
    "SelectedComponent",
    "select_build",
]


async def select_build(
    *,
    goal: str,
    budget_range: str,
    form_factor: str = "atx",
    cpu_brand: str = "no_preference",
    gpu_brand: str = "no_preference",
    cooling_preference: str = "no_preference",
    existing_parts: list[str] | None = None,
    notes: str | None = None,
    catalog: CatalogPort,
) -> BuildEngineResult:
    """Select an optimal PC build deterministically.

    This is the engine's main entry point. It fetches products from the
    catalog, deduplicates, computes compatibility families, scores and
    selects components, then returns a complete build.

    Args:
        goal: Build goal (e.g. "high_end_gaming", "light_work").
        budget_range: Budget range key (e.g. "1000_1500", "over_3000").
        form_factor: Case form factor preference.
        cpu_brand: CPU brand preference ("intel", "amd", "no_preference").
        gpu_brand: GPU brand preference ("nvidia", "amd", "no_preference").
        cooling_preference: Cooling type ("liquid", "air", "no_preference").
        existing_parts: Categories the user already has (excluded).
        notes: Free-text user notes for preference extraction.
        catalog: CatalogPort implementation for data access.

    Returns:
        BuildEngineResult with selected components and metadata.
    """
    # Importing here to avoid circular imports and keep the public API clean
    from engine.core.selector import run_selection

    return await run_selection(
        goal=goal,
        budget_range=budget_range,
        form_factor=form_factor,
        cpu_brand=cpu_brand,
        gpu_brand=gpu_brand,
        cooling_preference=cooling_preference,
        existing_parts=existing_parts or [],
        notes=notes,
        catalog=catalog,
    )
