"""Pre-filters catalog products before sending to the LLM.

Reduces the full catalog to ~10-15 compatible candidates per category by
applying brand preferences, compatibility constraints, and budget-aware
trimming. This allows Claude to submit a build in a single turn instead
of needing a separate scout turn.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.builder import (
    BuildRequest,
    CoolingPreference,
    CPUBrand,
    GPUBrand,
)
from app.services.build_validator import _FF_RANK
from app.services.catalog import CatalogService, ToolCatalogResult, get_catalog_service

log = logging.getLogger(__name__)

# Max candidates per category after filtering
_MAX_PER_CATEGORY = 15

# Socket sets by CPU brand
_AMD_SOCKETS = frozenset({"AM5", "AM4"})
_INTEL_SOCKETS = frozenset({"LGA1851", "LGA1700"})


def _safe_float(val: str | None) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


class CandidateFilter:
    """Pre-filters catalog products for the LLM.

    Applies brand preferences, compatibility constraints (socket, DDR,
    form factor, cooling type), and trims to top candidates per category.
    """

    def __init__(self, catalog: CatalogService | None = None):
        self._catalog = catalog or get_catalog_service()

    async def filter_candidates(
        self,
        request: BuildRequest,
        required_categories: set[str],
        db: AsyncSession,
    ) -> dict[str, list[ToolCatalogResult]]:
        """Return pre-filtered candidates per category.

        Fetches full catalog via scout_all, then filters by:
        1. Brand preferences (cpu_brand, gpu_brand)
        2. Platform compatibility (socket, DDR, form factor, cooling)
        3. Budget-aware trimming (top N by price)
        """
        # Fetch all products for required categories
        all_products = await self._catalog.scout_all(db, list(required_categories))

        # Determine valid sockets from cpu_brand preference
        valid_sockets = self._valid_sockets(request.cpu_brand)

        # Requested form factor rank — motherboards must be ≤ this rank
        requested_ff_rank = _FF_RANK.get(request.form_factor.value, 3)

        # Phase 1: Filter CPU and GPU first (they drive other constraints)
        cpus = self._filter_cpus(
            all_products.get("cpu", []), request.cpu_brand, valid_sockets
        )
        gpus = self._filter_gpus(all_products.get("gpu", []), request.gpu_brand)

        # Phase 2: Filter motherboards (depends on valid sockets + form factor)
        mobos = self._filter_motherboards(
            all_products.get("motherboard", []),
            valid_sockets,
            requested_ff_rank,
        )

        # Phase 3: Filter RAM (depends on motherboard DDR types)
        mobo_ddr_types = {
            m.specs.get("ddr_type") for m in mobos if m.specs.get("ddr_type")
        }
        ram = self._filter_ram(all_products.get("ram", []), mobo_ddr_types)

        # Phase 4: Filter cases (depends on form factor + GPU lengths)
        min_gpu_length = self._min_gpu_length(gpus)
        cases = self._filter_cases(
            all_products.get("case", []),
            requested_ff_rank,
            min_gpu_length,
        )

        # Phase 5: Filter PSU (depends on CPU TDP + GPU TDP)
        min_psu_wattage = self._min_psu_wattage(cpus, gpus)
        psus = self._filter_psus(all_products.get("psu", []), min_psu_wattage)

        # Phase 6: Filter cooling (depends on valid sockets + preference)
        cooling = self._filter_cooling(
            all_products.get("cooling", []),
            valid_sockets,
            request.cooling_preference,
        )

        # Phase 7: Storage — no compatibility filtering needed
        storage = all_products.get("storage", [])

        # Build result map
        result: dict[str, list[ToolCatalogResult]] = {}
        category_map = {
            "cpu": cpus,
            "gpu": gpus,
            "motherboard": mobos,
            "ram": ram,
            "case": cases,
            "psu": psus,
            "cooling": cooling,
            "storage": storage,
        }

        for cat in required_categories:
            if cat in category_map:
                items = category_map[cat]
            else:
                # Peripherals and other categories — pass through unfiltered
                items = all_products.get(cat, [])

            if not items:
                log.warning("Pre-filter: 0 candidates for category=%s", cat)

            # Trim to max candidates (already sorted by price from scout_all)
            result[cat] = items[:_MAX_PER_CATEGORY]

        total = sum(len(v) for v in result.values())
        log.info(
            "Pre-filter: %d categories, %d total candidates",
            len(result),
            total,
        )

        return result

    # ------------------------------------------------------------------
    # Platform determination
    # ------------------------------------------------------------------

    @staticmethod
    def _valid_sockets(cpu_brand: CPUBrand) -> frozenset[str] | None:
        """Return valid sockets for the given CPU brand preference.

        Returns None if no_preference (all sockets valid).
        """
        if cpu_brand == CPUBrand.amd:
            return _AMD_SOCKETS
        if cpu_brand == CPUBrand.intel:
            return _INTEL_SOCKETS
        return None  # no_preference — all sockets valid

    # ------------------------------------------------------------------
    # Per-category filters
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_cpus(
        items: list[ToolCatalogResult],
        cpu_brand: CPUBrand,
        valid_sockets: frozenset[str] | None,
    ) -> list[ToolCatalogResult]:
        result = []
        for item in items:
            # Brand filter
            if cpu_brand == CPUBrand.intel:
                if item.brand.lower() not in {"intel"}:
                    continue
            elif cpu_brand == CPUBrand.amd:
                if item.brand.lower() not in {"amd"}:
                    continue
            # Socket filter
            if valid_sockets:
                socket = item.specs.get("socket", "")
                if socket not in valid_sockets:
                    continue
            result.append(item)
        return result

    @staticmethod
    def _filter_gpus(
        items: list[ToolCatalogResult],
        gpu_brand: GPUBrand,
    ) -> list[ToolCatalogResult]:
        if gpu_brand == GPUBrand.no_preference:
            return items
        result = []
        for item in items:
            # AIB partners (MSI, ASUS, etc.) make GPUs for both NVIDIA and
            # AMD, so we always identify the chip by model name keywords.
            model_lower = item.model.lower()
            if gpu_brand == GPUBrand.nvidia:
                if not any(kw in model_lower for kw in ["geforce", "rtx", "gtx"]):
                    continue
            elif gpu_brand == GPUBrand.amd:
                if not any(kw in model_lower for kw in ["radeon", "rx "]):
                    continue
            result.append(item)
        return result

    @staticmethod
    def _filter_motherboards(
        items: list[ToolCatalogResult],
        valid_sockets: frozenset[str] | None,
        requested_ff_rank: int,
    ) -> list[ToolCatalogResult]:
        result = []
        for item in items:
            # Socket filter
            if valid_sockets:
                socket = item.specs.get("socket", "")
                if socket not in valid_sockets:
                    continue
            # Form factor filter — board must be ≤ requested rank
            mobo_ff = item.specs.get("form_factor", "")
            mobo_rank = _FF_RANK.get(mobo_ff.lower(), 0)
            if mobo_rank == 0:
                continue  # Unknown form factor
            if mobo_rank > requested_ff_rank:
                continue  # Board too large for requested form factor
            result.append(item)
        return result

    @staticmethod
    def _filter_ram(
        items: list[ToolCatalogResult],
        mobo_ddr_types: set[str],
    ) -> list[ToolCatalogResult]:
        if not mobo_ddr_types:
            return items  # Can't filter without motherboard info
        result = []
        for item in items:
            ddr = item.specs.get("ddr_type", "")
            if ddr in mobo_ddr_types:
                result.append(item)
        return result

    @staticmethod
    def _filter_cases(
        items: list[ToolCatalogResult],
        requested_ff_rank: int,
        min_gpu_length: float,
    ) -> list[ToolCatalogResult]:
        result = []
        for item in items:
            # Case must fit the motherboard form factor
            case_ff = item.specs.get("form_factor", "")
            case_rank = _FF_RANK.get(case_ff.lower(), 0)
            if case_rank == 0:
                continue
            if case_rank < requested_ff_rank:
                continue  # Case too small for motherboard
            # GPU length clearance
            if min_gpu_length > 0:
                max_gpu = _safe_float(item.specs.get("max_gpu_length"))
                if max_gpu > 0 and max_gpu < min_gpu_length:
                    continue
            result.append(item)
        return result

    @staticmethod
    def _filter_psus(
        items: list[ToolCatalogResult],
        min_wattage: float,
    ) -> list[ToolCatalogResult]:
        if min_wattage <= 0:
            return items
        result = []
        for item in items:
            wattage = _safe_float(item.specs.get("wattage"))
            if wattage >= min_wattage:
                result.append(item)
        return result

    @staticmethod
    def _filter_cooling(
        items: list[ToolCatalogResult],
        valid_sockets: frozenset[str] | None,
        cooling_pref: CoolingPreference,
    ) -> list[ToolCatalogResult]:
        result = []
        for item in items:
            # Cooling type preference
            cooling_type = item.specs.get("type", "").lower()
            if cooling_pref == CoolingPreference.liquid:
                if cooling_type != "liquid":
                    continue
            elif cooling_pref == CoolingPreference.air:
                if cooling_type != "air":
                    continue
            # Socket support filter
            if valid_sockets:
                support = item.specs.get("socket_support", "")
                supported = {s.strip() for s in support.split(",")}
                if not supported & valid_sockets:
                    continue
            result.append(item)
        return result

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _min_gpu_length(gpus: list[ToolCatalogResult]) -> float:
        """Return the minimum GPU length across all candidates.

        Cases must fit at least the smallest GPU.
        """
        lengths = [
            _safe_float(g.specs.get("length_mm"))
            for g in gpus
            if _safe_float(g.specs.get("length_mm")) > 0
        ]
        return min(lengths) if lengths else 0.0

    @staticmethod
    def _min_psu_wattage(
        cpus: list[ToolCatalogResult],
        gpus: list[ToolCatalogResult],
    ) -> float:
        """Minimum PSU wattage to support at least one (CPU, GPU) pair.

        Uses the lowest TDP CPU + lowest TDP GPU as the baseline.
        Formula: (cpu_tdp + gpu_tdp + 80) × 1.3
        """
        cpu_tdps = [
            _safe_float(c.specs.get("tdp"))
            for c in cpus
            if _safe_float(c.specs.get("tdp")) > 0
        ]
        gpu_tdps = [
            _safe_float(g.specs.get("tdp"))
            for g in gpus
            if _safe_float(g.specs.get("tdp")) > 0
        ]
        if not cpu_tdps or not gpu_tdps:
            return 0.0
        min_cpu_tdp = min(cpu_tdps)
        min_gpu_tdp = min(gpu_tdps)
        return (min_cpu_tdp + min_gpu_tdp + 80) * 1.3


@lru_cache(maxsize=1)
def get_candidate_filter() -> CandidateFilter:
    return CandidateFilter()
