"""Edge-case and adversarial stress tests for CandidateFilter."""

from unittest.mock import AsyncMock, MagicMock

from app.models.builder import (
    BudgetRange,
    BuildRequest,
    CoolingPreference,
    CPUBrand,
    FormFactor,
    GPUBrand,
    UserGoal,
)
from app.services.candidate_filter import _MAX_PER_CATEGORY, CandidateFilter
from app.services.catalog import ToolCatalogResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _product(
    id: int,
    brand: str = "Brand",
    model: str = "Model",
    specs: dict | None = None,
    price: float = 100.0,
) -> ToolCatalogResult:
    return ToolCatalogResult(
        id=id,
        brand=brand,
        model=model,
        specs=specs or {},
        price_eur=price,
    )


def _request(**overrides) -> BuildRequest:
    defaults = {
        "goal": UserGoal.mid_range_gaming,
        "budget_range": BudgetRange.range_1000_1500,
        "form_factor": FormFactor.atx,
        "cpu_brand": CPUBrand.no_preference,
        "gpu_brand": GPUBrand.no_preference,
        "cooling_preference": CoolingPreference.no_preference,
        "include_peripherals": False,
        "existing_parts": [],
        "notes": None,
    }
    defaults.update(overrides)
    return BuildRequest(**defaults)


def _mock_catalog(products: dict[str, list[ToolCatalogResult]]):
    catalog = MagicMock()
    catalog.scout_all = AsyncMock(return_value=products)
    return catalog


REQUIRED_CATS = {
    "cpu",
    "gpu",
    "motherboard",
    "ram",
    "storage",
    "psu",
    "case",
    "cooling",
}

# ---------------------------------------------------------------------------
# Minimal product sets for integration tests
# ---------------------------------------------------------------------------


def _base_products(**overrides) -> dict[str, list[ToolCatalogResult]]:
    """Return a minimal valid catalog. Override any category via kwargs."""
    defaults = {
        "cpu": [_product(1, "AMD", "Ryzen 5", {"socket": "AM5", "tdp": "65"}, 200)],
        "gpu": [
            _product(
                2, "MSI", "GeForce RTX 5060", {"tdp": "150", "length_mm": "280"}, 300
            )
        ],
        "motherboard": [
            _product(
                3,
                "MSI",
                "B650",
                {"socket": "AM5", "form_factor": "ATX", "ddr_type": "DDR5"},
                150,
            )
        ],
        "ram": [_product(4, "Corsair", "DDR5-6000", {"ddr_type": "DDR5"}, 80)],
        "storage": [_product(5, "Samsung", "990 Pro", {"type": "NVMe"}, 100)],
        "psu": [_product(6, "Corsair", "RM750", {"wattage": "750"}, 100)],
        "case": [
            _product(
                7, "NZXT", "H5 Flow", {"form_factor": "ATX", "max_gpu_length": "400"}, 80
            )
        ],
        "cooling": [
            _product(
                8, "Noctua", "NH-D15", {"type": "air", "socket_support": "AM5"}, 90
            )
        ],
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# TestEmptyCatalog
# ---------------------------------------------------------------------------


class TestEmptyCatalog:
    async def test_empty_catalog_returns_empty_results(self):
        """scout_all returns {} — all result categories should have 0 items."""
        catalog = _mock_catalog({})
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        for cat in REQUIRED_CATS:
            assert result[cat] == [], f"Expected empty list for {cat}"

    async def test_single_category_empty_others_populated(self):
        """Only CPU category is empty; all others have products."""
        products = _base_products(cpu=[])
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert result["cpu"] == []
        # Other categories should still be populated
        for cat in REQUIRED_CATS - {"cpu"}:
            assert len(result[cat]) > 0, f"Expected items in {cat}"

    async def test_all_categories_single_product(self):
        """Exactly 1 product per category — no crash on min/max with single item."""
        products = _base_products()
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.amd)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        for cat in REQUIRED_CATS:
            assert len(result[cat]) == 1, f"Expected exactly 1 item in {cat}"


# ---------------------------------------------------------------------------
# TestMalformedSpecs
# ---------------------------------------------------------------------------


class TestMalformedSpecs:
    async def test_missing_socket_spec_on_cpu(self):
        """CPUs with no 'socket' key. With no_preference, they should be included."""
        products = _base_products(
            cpu=[
                _product(1, "AMD", "Ryzen 5", {}, 200),  # no socket key
                _product(2, "Intel", "Core i5", {}, 250),  # no socket key
            ]
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.no_preference)

        # Should not raise KeyError
        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert len(result["cpu"]) == 2

    async def test_missing_tdp_spec(self):
        """CPUs/GPUs with no 'tdp'. PSU filter should return all PSUs (min_wattage=0)."""
        products = _base_products(
            cpu=[_product(1, "AMD", "Ryzen 5", {"socket": "AM5"}, 200)],  # no tdp
            gpu=[
                _product(
                    2, "MSI", "GeForce RTX 5060", {"length_mm": "280"}, 300
                )
            ],  # no tdp
            psu=[
                _product(10, "Corsair", "RM550", {"wattage": "550"}, 80),
                _product(11, "Corsair", "RM750", {"wattage": "750"}, 100),
            ],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # Both PSUs should be returned because min_wattage falls back to 0
        assert len(result["psu"]) == 2

    async def test_non_numeric_wattage(self):
        """PSU with wattage='N/A' or ''. _safe_float returns 0.0, no crash."""
        psu_na = _product(10, "Brand", "PSU NA", {"wattage": "N/A"}, 80)
        psu_empty = _product(11, "Brand", "PSU Empty", {"wattage": ""}, 90)
        psu_good = _product(12, "Corsair", "RM750", {"wattage": "750"}, 100)

        # Use a min_wattage > 0 by providing TDP data
        products = _base_products(
            cpu=[
                _product(1, "AMD", "Ryzen 5", {"socket": "AM5", "tdp": "65"}, 200)
            ],
            gpu=[
                _product(
                    2, "MSI", "GeForce RTX 5060", {"tdp": "150", "length_mm": "280"}, 300
                )
            ],
            psu=[psu_na, psu_empty, psu_good],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        # Should not raise, non-numeric PSUs are excluded (wattage parses to 0 < min)
        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        ids = {p.id for p in result["psu"]}
        assert 10 not in ids  # N/A → 0.0 → excluded
        assert 11 not in ids  # "" → 0.0 → excluded
        assert 12 in ids  # 750W → included

    async def test_missing_form_factor_on_motherboard(self):
        """Mobo with form_factor='' or missing → rank 0 → excluded."""
        products = _base_products(
            motherboard=[
                _product(3, "MSI", "B650 No FF", {"socket": "AM5"}, 150),  # no form_factor
                _product(
                    4,
                    "ASUS",
                    "B650 Empty FF",
                    {"socket": "AM5", "form_factor": ""},
                    160,
                ),  # empty form_factor
            ]
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.amd)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # Both should be excluded due to unknown/empty form factor
        assert len(result["motherboard"]) == 0

    async def test_missing_ddr_type_on_mobo(self):
        """All mobos lack ddr_type → mobo_ddr_types empty → no RAM filtering."""
        products = _base_products(
            motherboard=[
                _product(
                    3,
                    "MSI",
                    "B650",
                    {"socket": "AM5", "form_factor": "ATX"},  # no ddr_type
                    150,
                )
            ],
            ram=[
                _product(4, "Corsair", "DDR5-6000", {"ddr_type": "DDR5"}, 120),
                _product(5, "Kingston", "DDR4-3200", {"ddr_type": "DDR4"}, 110),
            ],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.amd)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # mobo_ddr_types is empty → all RAM returned (prices above floor)
        assert len(result["ram"]) == 2

    async def test_missing_max_gpu_length_on_case(self):
        """Case with no max_gpu_length spec → max_gpu=0, no exclusion."""
        products = _base_products(
            case=[
                _product(
                    7, "Brand", "Case No GPU Spec", {"form_factor": "ATX"}, 80
                ),  # no max_gpu_length
            ],
            gpu=[
                _product(
                    2, "MSI", "GeForce RTX 5060", {"tdp": "150", "length_mm": "280"}, 300
                )
            ],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # Case should still be included: max_gpu=0, condition (max_gpu > 0 and ...) fails
        assert len(result["case"]) == 1
        assert result["case"][0].id == 7

    async def test_empty_socket_support_on_cooler(self):
        """Cooler with socket_support='' → split produces {''} → no intersection."""
        products = _base_products(
            cooling=[
                _product(
                    8,
                    "Brand",
                    "Generic Cooler",
                    {"type": "air", "socket_support": ""},
                    50,
                )
            ],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        # AMD build → valid_sockets = {"AM5", "AM4"}
        req = _request(cpu_brand=CPUBrand.amd)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # Empty socket_support split gives {''} which doesn't intersect AMD sockets
        assert len(result["cooling"]) == 0


# ---------------------------------------------------------------------------
# TestBoundaryValues
# ---------------------------------------------------------------------------


class TestBoundaryValues:
    async def test_exactly_max_per_category_items(self):
        """Provide exactly _MAX_PER_CATEGORY (15) items — all should be returned."""
        items = [
            _product(i, "Samsung", f"SSD {i}", {"type": "NVMe"}, 50.0 + i)
            for i in range(_MAX_PER_CATEGORY)
        ]
        products = _base_products(storage=items)
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert len(result["storage"]) == _MAX_PER_CATEGORY

    async def test_one_over_max_per_category(self):
        """Provide 16 items — only _MAX_PER_CATEGORY (15) should be returned."""
        items = [
            _product(i, "Samsung", f"SSD {i}", {"type": "NVMe"}, 50.0 + i)
            for i in range(_MAX_PER_CATEGORY + 1)
        ]
        products = _base_products(storage=items)
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert len(result["storage"]) == _MAX_PER_CATEGORY

    async def test_psu_exactly_at_minimum_wattage(self):
        """PSU wattage equals computed minimum → should be included (>=)."""
        # min = (65 + 150 + 80) * 1.3 = 383.5
        min_wattage = (65 + 150 + 80) * 1.3
        products = _base_products(
            cpu=[_product(1, "AMD", "Ryzen 5", {"socket": "AM5", "tdp": "65"}, 200)],
            gpu=[
                _product(
                    2, "MSI", "GeForce RTX 5060", {"tdp": "150", "length_mm": "280"}, 300
                )
            ],
            psu=[_product(6, "Corsair", "Exact PSU", {"wattage": str(min_wattage)}, 80)],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert len(result["psu"]) == 1

    async def test_psu_one_watt_below_minimum(self):
        """PSU wattage is min - 1 → should be excluded."""
        min_wattage = (65 + 150 + 80) * 1.3
        below_min = min_wattage - 1
        products = _base_products(
            cpu=[_product(1, "AMD", "Ryzen 5", {"socket": "AM5", "tdp": "65"}, 200)],
            gpu=[
                _product(
                    2, "MSI", "GeForce RTX 5060", {"tdp": "150", "length_mm": "280"}, 300
                )
            ],
            psu=[_product(6, "Corsair", "Weak PSU", {"wattage": str(below_min)}, 80)],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert len(result["psu"]) == 0

    async def test_gpu_length_exactly_at_case_max(self):
        """GPU length == case max_gpu_length → case should be included (not < min)."""
        gpu_length = 320.0
        products = _base_products(
            gpu=[
                _product(
                    2,
                    "MSI",
                    "GeForce RTX 5070",
                    {"tdp": "200", "length_mm": str(gpu_length)},
                    500,
                )
            ],
            case=[
                _product(
                    7,
                    "NZXT",
                    "H5",
                    {"form_factor": "ATX", "max_gpu_length": str(gpu_length)},
                    80,
                )
            ],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # Case max == GPU length: condition is (max_gpu < min_gpu_length), so not excluded
        assert len(result["case"]) == 1

    async def test_case_form_factor_equal_to_requested(self):
        """Case rank equals requested FF rank → should be included (condition is <, not <=)."""
        # ATX requested (rank 3), ATX case (rank 3) — case_rank < requested_ff_rank is False
        products = _base_products(
            case=[
                _product(
                    7, "NZXT", "H5 ATX", {"form_factor": "ATX", "max_gpu_length": "400"}, 80
                )
            ]
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(form_factor=FormFactor.atx)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert len(result["case"]) == 1


# ---------------------------------------------------------------------------
# TestPlatformCrossContamination
# ---------------------------------------------------------------------------


class TestPlatformCrossContamination:
    async def test_amd_build_has_zero_intel_cpus(self):
        """AMD build with mixed CPU catalog → 0 Intel CPUs in result."""
        products = _base_products(
            cpu=[
                _product(1, "AMD", "Ryzen 5 7600X", {"socket": "AM5", "tdp": "105"}, 200),
                _product(2, "AMD", "Ryzen 7 7700X", {"socket": "AM5", "tdp": "105"}, 300),
                _product(
                    3, "Intel", "Core i5-14600K", {"socket": "LGA1700", "tdp": "125"}, 250
                ),
                _product(
                    4, "Intel", "Core i7-14700K", {"socket": "LGA1700", "tdp": "125"}, 400
                ),
            ]
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.amd)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        intel_cpus = [p for p in result["cpu"] if p.brand.lower() == "intel"]
        assert len(intel_cpus) == 0

    async def test_intel_build_has_zero_amd_mobos(self):
        """Intel build → 0 AM5/AM4 motherboards in result."""
        products = _base_products(
            cpu=[
                _product(
                    1, "Intel", "Core i5-14600K", {"socket": "LGA1700", "tdp": "125"}, 250
                )
            ],
            motherboard=[
                _product(
                    3,
                    "MSI",
                    "Z790",
                    {"socket": "LGA1700", "form_factor": "ATX", "ddr_type": "DDR5"},
                    200,
                ),
                _product(
                    4,
                    "ASUS",
                    "B650",
                    {"socket": "AM5", "form_factor": "ATX", "ddr_type": "DDR5"},
                    180,
                ),
                _product(
                    5,
                    "Gigabyte",
                    "B550",
                    {"socket": "AM4", "form_factor": "ATX", "ddr_type": "DDR4"},
                    150,
                ),
            ],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.intel)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        amd_mobos = [
            p
            for p in result["motherboard"]
            if p.specs.get("socket") in {"AM5", "AM4"}
        ]
        assert len(amd_mobos) == 0

    async def test_amd_build_ram_matches_amd_mobo_ddr(self):
        """AMD build with mixed AM5+AM4 mobos → RAM includes both DDR4 and DDR5."""
        products = _base_products(
            cpu=[_product(1, "AMD", "Ryzen 5", {"socket": "AM5", "tdp": "65"}, 200)],
            motherboard=[
                _product(
                    3,
                    "MSI",
                    "B650 AM5",
                    {"socket": "AM5", "form_factor": "ATX", "ddr_type": "DDR5"},
                    200,
                ),
                _product(
                    4,
                    "Gigabyte",
                    "B550 AM4",
                    {"socket": "AM4", "form_factor": "ATX", "ddr_type": "DDR4"},
                    150,
                ),
            ],
            ram=[
                _product(5, "Corsair", "DDR5-6000", {"ddr_type": "DDR5"}, 120),
                _product(6, "Kingston", "DDR4-3200", {"ddr_type": "DDR4"}, 110),
                _product(7, "G.Skill", "DDR3-1600", {"ddr_type": "DDR3"}, 100),  # should be excluded by DDR filter
            ],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.amd)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        ddr_types = {p.specs.get("ddr_type") for p in result["ram"]}
        assert "DDR5" in ddr_types
        assert "DDR4" in ddr_types
        assert "DDR3" not in ddr_types

    async def test_liquid_preference_has_zero_air_coolers(self):
        """Liquid preference → 0 air coolers in result."""
        products = _base_products(
            cooling=[
                _product(
                    8,
                    "Corsair",
                    "H100i",
                    {"type": "liquid", "socket_support": "AM5,LGA1700"},
                    120,
                ),
                _product(
                    9,
                    "Noctua",
                    "NH-D15",
                    {"type": "air", "socket_support": "AM5,LGA1700"},
                    90,
                ),
                _product(
                    10,
                    "be quiet!",
                    "Pure Rock 2",
                    {"type": "air", "socket_support": "AM5,LGA1700"},
                    40,
                ),
            ]
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cooling_preference=CoolingPreference.liquid)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        air_coolers = [
            p for p in result["cooling"] if p.specs.get("type") == "air"
        ]
        assert len(air_coolers) == 0


# ---------------------------------------------------------------------------
# TestFilterChainDependency
# ---------------------------------------------------------------------------


class TestFilterChainDependency:
    async def test_mobo_filter_cascades_to_ram(self):
        """If mobo filter removes all DDR4 boards, RAM filter should remove all DDR4 RAM.

        Intel build → only LGA1700/LGA1851 mobos survive socket filter.
        The LGA1700 boards in this catalog are all DDR5, so DDR4 RAM is excluded.
        """
        products = _base_products(
            cpu=[
                _product(
                    1, "Intel", "Core i5-14600K", {"socket": "LGA1700", "tdp": "125"}, 250
                )
            ],
            motherboard=[
                # DDR5 mobo — survives Intel socket filter
                _product(
                    3,
                    "MSI",
                    "Z790 DDR5",
                    {"socket": "LGA1700", "form_factor": "ATX", "ddr_type": "DDR5"},
                    200,
                ),
                # DDR4 mobo on AM4 — filtered out (AM4 not in Intel sockets)
                _product(
                    4,
                    "Gigabyte",
                    "B550 DDR4",
                    {"socket": "AM4", "form_factor": "ATX", "ddr_type": "DDR4"},
                    150,
                ),
            ],
            ram=[
                _product(5, "Corsair", "DDR5-6000", {"ddr_type": "DDR5"}, 80),
                _product(6, "Kingston", "DDR4-3200", {"ddr_type": "DDR4"}, 60),
            ],
            cooling=[
                _product(
                    8,
                    "Noctua",
                    "NH-D15",
                    {"type": "air", "socket_support": "LGA1700,LGA1851"},
                    90,
                )
            ],
            case=[
                _product(
                    7,
                    "NZXT",
                    "H5",
                    {"form_factor": "ATX", "max_gpu_length": "400"},
                    80,
                )
            ],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        # Intel build → LGA1700/LGA1851 sockets only → only DDR5 mobo survives
        req = _request(cpu_brand=CPUBrand.intel, form_factor=FormFactor.atx)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # Only Intel-socket mobo (DDR5) should remain
        assert all(
            p.specs.get("ddr_type") == "DDR5" for p in result["motherboard"]
        )
        # RAM filter should cascade — only DDR5 RAM
        assert all(p.specs.get("ddr_type") == "DDR5" for p in result["ram"])
        ddr4_ram = [p for p in result["ram"] if p.specs.get("ddr_type") == "DDR4"]
        assert len(ddr4_ram) == 0

    async def test_gpu_filter_cascades_to_cases(self):
        """If GPU filter keeps only long GPUs (350mm+), small cases (max_gpu=300) excluded."""
        products = _base_products(
            gpu=[
                # Only keep a long GPU
                _product(
                    2,
                    "MSI",
                    "GeForce RTX 5090",
                    {"tdp": "350", "length_mm": "360"},
                    900,
                ),
            ],
            case=[
                # Large case — fits 360mm GPU
                _product(
                    7,
                    "Fractal",
                    "Torrent",
                    {"form_factor": "ATX", "max_gpu_length": "420"},
                    120,
                ),
                # Small case — cannot fit 360mm GPU
                _product(
                    8,
                    "NZXT",
                    "H1",
                    {"form_factor": "ATX", "max_gpu_length": "300"},
                    80,
                ),
            ],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request()

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # H1 (max 300mm) should be excluded — min GPU length is 360mm
        case_ids = {p.id for p in result["case"]}
        assert 7 in case_ids   # Fractal Torrent (420mm clearance) — fits
        assert 8 not in case_ids  # NZXT H1 (300mm < 360mm) — excluded

    async def test_cpu_filter_cascades_to_cooling(self):
        """AMD build should exclude coolers that only support Intel sockets."""
        products = _base_products(
            cpu=[_product(1, "AMD", "Ryzen 5", {"socket": "AM5", "tdp": "65"}, 200)],
            cooling=[
                _product(
                    8,
                    "Corsair",
                    "H100",
                    {"type": "liquid", "socket_support": "AM5,AM4,LGA1700"},
                    120,
                ),
                _product(
                    9,
                    "Noctua",
                    "NH-D15",
                    {"type": "air", "socket_support": "AM5,AM4"},
                    90,
                ),
                # Intel-only cooler — should be excluded
                _product(
                    10,
                    "Thermalright",
                    "Peerless Assassin Intel",
                    {"type": "air", "socket_support": "LGA1700,LGA1851"},
                    45,
                ),
            ],
        )
        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.amd)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        cooler_ids = {p.id for p in result["cooling"]}
        assert 8 in cooler_ids   # Supports AM5 — included
        assert 9 in cooler_ids   # Supports AM5 — included
        assert 10 not in cooler_ids  # Intel only — excluded
