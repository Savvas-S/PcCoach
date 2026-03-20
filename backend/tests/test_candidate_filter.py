"""Tests for the CandidateFilter service."""

from unittest.mock import AsyncMock, MagicMock

from app.models.builder import (
    BudgetRange,
    BuildRequest,
    ComponentCategory,
    CoolingPreference,
    CPUBrand,
    FormFactor,
    GPUBrand,
    UserGoal,
)
from app.services.candidate_filter import (
    _MAX_PER_CATEGORY,
    CandidateFilter,
)
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
# Platform determination
# ---------------------------------------------------------------------------


class TestValidSockets:
    def test_amd_returns_amd_sockets(self):
        sockets = CandidateFilter._valid_sockets(CPUBrand.amd)
        assert "AM5" in sockets
        assert "AM4" in sockets
        assert "LGA1700" not in sockets

    def test_intel_returns_intel_sockets(self):
        sockets = CandidateFilter._valid_sockets(CPUBrand.intel)
        assert "LGA1851" in sockets
        assert "LGA1700" in sockets
        assert "AM5" not in sockets

    def test_no_preference_returns_none(self):
        assert CandidateFilter._valid_sockets(CPUBrand.no_preference) is None


# ---------------------------------------------------------------------------
# CPU filtering
# ---------------------------------------------------------------------------


class TestFilterCPUs:
    def test_amd_preference_filters_intel(self):
        items = [
            _product(1, "AMD", "Ryzen 5", {"socket": "AM5"}),
            _product(2, "Intel", "Core i5", {"socket": "LGA1700"}),
        ]
        result = CandidateFilter._filter_cpus(
            items, CPUBrand.amd, frozenset({"AM5", "AM4"})
        )
        assert len(result) == 1
        assert result[0].id == 1

    def test_intel_preference_filters_amd(self):
        items = [
            _product(1, "AMD", "Ryzen 5", {"socket": "AM5"}),
            _product(2, "Intel", "Core i5", {"socket": "LGA1700"}),
        ]
        result = CandidateFilter._filter_cpus(
            items, CPUBrand.intel, frozenset({"LGA1851", "LGA1700"})
        )
        assert len(result) == 1
        assert result[0].id == 2

    def test_no_preference_keeps_all(self):
        items = [
            _product(1, "AMD", "Ryzen 5", {"socket": "AM5"}),
            _product(2, "Intel", "Core i5", {"socket": "LGA1700"}),
        ]
        result = CandidateFilter._filter_cpus(items, CPUBrand.no_preference, None)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# GPU filtering
# ---------------------------------------------------------------------------


class TestFilterGPUs:
    def test_nvidia_preference_keeps_nvidia(self):
        items = [
            _product(1, "MSI", "GeForce RTX 5070", {}),
            _product(2, "Sapphire", "Radeon RX 9070", {}),
        ]
        result = CandidateFilter._filter_gpus(items, GPUBrand.nvidia)
        assert len(result) == 1
        assert result[0].id == 1

    def test_amd_preference_keeps_amd(self):
        items = [
            _product(1, "MSI", "GeForce RTX 5070", {}),
            _product(2, "Sapphire", "Radeon RX 9070", {}),
        ]
        result = CandidateFilter._filter_gpus(items, GPUBrand.amd)
        assert len(result) == 1
        assert result[0].id == 2

    def test_nvidia_excludes_amd_from_same_aib(self):
        """MSI makes both NVIDIA and AMD cards — AMD must be excluded."""
        items = [
            _product(1, "MSI", "GeForce RTX 5070", {}),
            _product(2, "MSI", "Radeon RX 9070 XT", {}),
            _product(3, "ASUS", "ROG Strix GeForce RTX 5080", {}),
            _product(4, "ASUS", "TUF Radeon RX 9070", {}),
        ]
        result = CandidateFilter._filter_gpus(items, GPUBrand.nvidia)
        assert len(result) == 2
        assert {r.id for r in result} == {1, 3}

    def test_amd_excludes_nvidia_from_same_aib(self):
        """MSI makes both — NVIDIA must be excluded when AMD preferred."""
        items = [
            _product(1, "MSI", "GeForce RTX 5070", {}),
            _product(2, "MSI", "Radeon RX 9070 XT", {}),
        ]
        result = CandidateFilter._filter_gpus(items, GPUBrand.amd)
        assert len(result) == 1
        assert result[0].id == 2

    def test_no_preference_keeps_all(self):
        items = [
            _product(1, "MSI", "GeForce RTX 5070", {}),
            _product(2, "Sapphire", "Radeon RX 9070", {}),
        ]
        result = CandidateFilter._filter_gpus(items, GPUBrand.no_preference)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Motherboard filtering
# ---------------------------------------------------------------------------


class TestFilterMotherboards:
    def test_socket_filter(self):
        items = [
            _product(1, "MSI", "B650", {"socket": "AM5", "form_factor": "ATX"}),
            _product(2, "ASUS", "Z790", {"socket": "LGA1700", "form_factor": "ATX"}),
        ]
        result = CandidateFilter._filter_motherboards(items, frozenset({"AM5"}), 3)
        assert len(result) == 1
        assert result[0].id == 1

    def test_form_factor_filter(self):
        items = [
            _product(1, "MSI", "B650", {"socket": "AM5", "form_factor": "ATX"}),
            _product(2, "ASUS", "B650M", {"socket": "AM5", "form_factor": "micro_atx"}),
        ]
        # Requested micro_atx (rank 2) — ATX (rank 3) boards should be excluded
        result = CandidateFilter._filter_motherboards(items, frozenset({"AM5"}), 2)
        assert len(result) == 1
        assert result[0].id == 2

    def test_no_socket_preference_keeps_all(self):
        items = [
            _product(1, "MSI", "B650", {"socket": "AM5", "form_factor": "ATX"}),
            _product(2, "ASUS", "Z790", {"socket": "LGA1700", "form_factor": "ATX"}),
        ]
        result = CandidateFilter._filter_motherboards(items, None, 3)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# RAM filtering
# ---------------------------------------------------------------------------


class TestFilterRAM:
    def test_ddr_filter(self):
        items = [
            _product(1, "Corsair", "Vengeance DDR5", {"ddr_type": "DDR5"}),
            _product(2, "Kingston", "Fury DDR4", {"ddr_type": "DDR4"}),
        ]
        result = CandidateFilter._filter_ram(items, {"DDR5"})
        assert len(result) == 1
        assert result[0].id == 1

    def test_empty_mobo_ddr_keeps_all(self):
        items = [
            _product(1, "Corsair", "Vengeance DDR5", {"ddr_type": "DDR5"}),
            _product(2, "Kingston", "Fury DDR4", {"ddr_type": "DDR4"}),
        ]
        result = CandidateFilter._filter_ram(items, set())
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Case filtering
# ---------------------------------------------------------------------------


class TestFilterCases:
    def test_form_factor_too_small_excluded(self):
        items = [
            _product(1, "NZXT", "H5", {"form_factor": "ATX", "max_gpu_length": "400"}),
            _product(
                2,
                "Fractal",
                "Pop Mini",
                {"form_factor": "micro_atx", "max_gpu_length": "400"},
            ),
        ]
        # Request ATX (rank 3) — micro_atx case (rank 2) is too small
        result = CandidateFilter._filter_cases(items, 3, 300.0)
        assert len(result) == 1
        assert result[0].id == 1

    def test_gpu_length_filter(self):
        items = [
            _product(1, "NZXT", "H5", {"form_factor": "ATX", "max_gpu_length": "400"}),
            _product(2, "SFF", "Tiny", {"form_factor": "ATX", "max_gpu_length": "250"}),
        ]
        result = CandidateFilter._filter_cases(items, 3, 300.0)
        assert len(result) == 1
        assert result[0].id == 1


# ---------------------------------------------------------------------------
# PSU filtering
# ---------------------------------------------------------------------------


class TestFilterPSUs:
    def test_underpowered_excluded(self):
        items = [
            _product(1, "Corsair", "RM650", {"wattage": "650"}),
            _product(2, "Corsair", "RM850", {"wattage": "850"}),
        ]
        # Need at least 700W
        result = CandidateFilter._filter_psus(items, 700.0)
        assert len(result) == 1
        assert result[0].id == 2

    def test_zero_min_keeps_all(self):
        items = [
            _product(1, "Corsair", "RM650", {"wattage": "650"}),
        ]
        result = CandidateFilter._filter_psus(items, 0.0)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Cooling filtering
# ---------------------------------------------------------------------------


class TestFilterCooling:
    def test_liquid_preference(self):
        items = [
            _product(
                1,
                "Corsair",
                "H100",
                {"type": "liquid", "socket_support": "AM5,LGA1700"},
            ),
            _product(
                2, "Noctua", "NH-D15", {"type": "air", "socket_support": "AM5,LGA1700"}
            ),
        ]
        result = CandidateFilter._filter_cooling(
            items, frozenset({"AM5"}), CoolingPreference.liquid
        )
        assert len(result) == 1
        assert result[0].id == 1

    def test_air_preference(self):
        items = [
            _product(
                1,
                "Corsair",
                "H100",
                {"type": "liquid", "socket_support": "AM5,LGA1700"},
            ),
            _product(
                2, "Noctua", "NH-D15", {"type": "air", "socket_support": "AM5,LGA1700"}
            ),
        ]
        result = CandidateFilter._filter_cooling(
            items, frozenset({"AM5"}), CoolingPreference.air
        )
        assert len(result) == 1
        assert result[0].id == 2

    def test_socket_support_filter(self):
        items = [
            _product(
                1, "Corsair", "H100", {"type": "liquid", "socket_support": "LGA1700"}
            ),
            _product(
                2,
                "Noctua",
                "NH-D15",
                {"type": "liquid", "socket_support": "AM5,LGA1700"},
            ),
        ]
        result = CandidateFilter._filter_cooling(
            items, frozenset({"AM5"}), CoolingPreference.liquid
        )
        assert len(result) == 1
        assert result[0].id == 2


# ---------------------------------------------------------------------------
# Integration: filter_candidates
# ---------------------------------------------------------------------------


class TestFilterCandidates:
    async def test_full_pipeline_amd_build(self):
        products = {
            "cpu": [
                _product(
                    1, "AMD", "Ryzen 5 7600X", {"socket": "AM5", "tdp": "105"}, 200
                ),
                _product(
                    2,
                    "Intel",
                    "Core i5-14600K",
                    {"socket": "LGA1700", "tdp": "125"},
                    250,
                ),
            ],
            "gpu": [
                _product(
                    3,
                    "MSI",
                    "GeForce RTX 5070",
                    {"tdp": "250", "length_mm": "320"},
                    500,
                ),
            ],
            "motherboard": [
                _product(
                    4,
                    "MSI",
                    "B650 Tomahawk",
                    {"socket": "AM5", "form_factor": "ATX", "ddr_type": "DDR5"},
                    180,
                ),
                _product(
                    5,
                    "ASUS",
                    "Z790-P",
                    {"socket": "LGA1700", "form_factor": "ATX", "ddr_type": "DDR5"},
                    200,
                ),
            ],
            "ram": [
                _product(
                    6,
                    "Corsair",
                    "Vengeance DDR5",
                    {"ddr_type": "DDR5", "capacity_gb": "32"},
                    100,
                ),
                _product(
                    7,
                    "Kingston",
                    "Fury DDR4",
                    {"ddr_type": "DDR4", "capacity_gb": "32"},
                    80,
                ),
            ],
            "storage": [_product(8, "Samsung", "990 Pro", {"type": "NVMe"}, 120)],
            "psu": [
                _product(9, "Corsair", "RM850", {"wattage": "850"}, 120),
                _product(10, "EVGA", "500W", {"wattage": "500"}, 50),
            ],
            "case": [
                _product(
                    11,
                    "NZXT",
                    "H5 Flow",
                    {"form_factor": "ATX", "max_gpu_length": "400"},
                    80,
                ),
            ],
            "cooling": [
                _product(
                    12,
                    "Noctua",
                    "NH-D15",
                    {"type": "air", "socket_support": "AM5,LGA1700"},
                    90,
                ),
            ],
        }

        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.amd)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # CPU: only AMD should remain
        assert all(p.brand == "AMD" for p in result["cpu"])
        # Motherboard: only AM5 socket
        assert all(p.specs.get("socket") == "AM5" for p in result["motherboard"])
        # RAM: only DDR5 (matching the AM5 motherboard)
        assert all(p.specs.get("ddr_type") == "DDR5" for p in result["ram"])
        # PSU: 500W excluded (min need: (105+250+80)*1.3 ≈ 565W)
        assert all(float(p.specs.get("wattage", 0)) >= 565 for p in result["psu"])

    async def test_cooling_preference_applied(self):
        products = {
            "cpu": [_product(1, "AMD", "R5", {"socket": "AM5", "tdp": "65"}, 200)],
            "gpu": [
                _product(2, "MSI", "RTX 5060", {"tdp": "150", "length_mm": "280"}, 300)
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
            "ram": [_product(4, "Corsair", "DDR5", {"ddr_type": "DDR5"}, 80)],
            "storage": [_product(5, "Samsung", "SSD", {}, 100)],
            "psu": [_product(6, "Corsair", "RM750", {"wattage": "750"}, 100)],
            "case": [
                _product(
                    7, "NZXT", "H5", {"form_factor": "ATX", "max_gpu_length": "400"}, 80
                )
            ],
            "cooling": [
                _product(
                    8,
                    "Corsair",
                    "H100",
                    {"type": "liquid", "socket_support": "AM5"},
                    120,
                ),
                _product(
                    9, "Noctua", "NH-D15", {"type": "air", "socket_support": "AM5"}, 90
                ),
            ],
        }

        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(
            cpu_brand=CPUBrand.amd, cooling_preference=CoolingPreference.liquid
        )

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # Only liquid cooling should remain
        assert len(result["cooling"]) == 1
        assert result["cooling"][0].specs["type"] == "liquid"

    async def test_form_factor_micro_atx(self):
        products = {
            "cpu": [_product(1, "AMD", "R5", {"socket": "AM5", "tdp": "65"}, 200)],
            "gpu": [
                _product(2, "MSI", "RTX 5060", {"tdp": "150", "length_mm": "280"}, 300)
            ],
            "motherboard": [
                _product(
                    3,
                    "MSI",
                    "B650 ATX",
                    {"socket": "AM5", "form_factor": "ATX", "ddr_type": "DDR5"},
                    180,
                ),
                _product(
                    4,
                    "MSI",
                    "B650M",
                    {"socket": "AM5", "form_factor": "micro_atx", "ddr_type": "DDR5"},
                    150,
                ),
            ],
            "ram": [_product(5, "Corsair", "DDR5", {"ddr_type": "DDR5"}, 80)],
            "storage": [_product(6, "Samsung", "SSD", {}, 100)],
            "psu": [_product(7, "Corsair", "RM750", {"wattage": "750"}, 100)],
            "case": [
                _product(
                    8,
                    "NZXT",
                    "H5 ATX",
                    {"form_factor": "ATX", "max_gpu_length": "400"},
                    80,
                ),
                _product(
                    9,
                    "Fractal",
                    "Pop mATX",
                    {"form_factor": "micro_atx", "max_gpu_length": "350"},
                    70,
                ),
            ],
            "cooling": [
                _product(
                    10, "Noctua", "NH-D15", {"type": "air", "socket_support": "AM5"}, 90
                )
            ],
        }

        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.amd, form_factor=FormFactor.micro_atx)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # ATX motherboard should be excluded (rank 3 > micro_atx rank 2)
        assert len(result["motherboard"]) == 1
        assert result["motherboard"][0].specs["form_factor"] == "micro_atx"
        # Both cases should remain (ATX and micro_atx both fit)
        assert len(result["case"]) == 2

    async def test_max_per_category_trimming(self):
        """More than _MAX_PER_CATEGORY items should be trimmed."""
        items = [
            _product(i, "Brand", f"Model {i}", {"type": "NVMe"}, 50.0 + i)
            for i in range(20)
        ]
        products = {
            "cpu": [_product(100, "AMD", "R5", {"socket": "AM5", "tdp": "65"}, 200)],
            "gpu": [
                _product(101, "MSI", "RTX", {"tdp": "150", "length_mm": "280"}, 300)
            ],
            "motherboard": [
                _product(
                    102,
                    "MSI",
                    "B650",
                    {"socket": "AM5", "form_factor": "ATX", "ddr_type": "DDR5"},
                    150,
                )
            ],
            "ram": [_product(103, "Corsair", "DDR5", {"ddr_type": "DDR5"}, 80)],
            "storage": items,
            "psu": [_product(104, "Corsair", "RM750", {"wattage": "750"}, 100)],
            "case": [
                _product(
                    105,
                    "NZXT",
                    "H5",
                    {"form_factor": "ATX", "max_gpu_length": "400"},
                    80,
                )
            ],
            "cooling": [
                _product(
                    106,
                    "Noctua",
                    "NH-D15",
                    {"type": "air", "socket_support": "AM5"},
                    90,
                )
            ],
        }

        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(cpu_brand=CPUBrand.amd)

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert len(result["storage"]) == _MAX_PER_CATEGORY

    async def test_existing_parts_excluded(self):
        products = {
            "cpu": [_product(1, "AMD", "R5", {"socket": "AM5", "tdp": "65"}, 200)],
            "gpu": [_product(2, "MSI", "RTX", {"tdp": "150", "length_mm": "280"}, 300)],
            "motherboard": [
                _product(
                    3,
                    "MSI",
                    "B650",
                    {"socket": "AM5", "form_factor": "ATX", "ddr_type": "DDR5"},
                    150,
                )
            ],
            "ram": [_product(4, "Corsair", "DDR5", {"ddr_type": "DDR5"}, 80)],
            "storage": [_product(5, "Samsung", "SSD", {}, 100)],
            "psu": [_product(6, "Corsair", "RM750", {"wattage": "750"}, 100)],
            "case": [
                _product(
                    7, "NZXT", "H5", {"form_factor": "ATX", "max_gpu_length": "400"}, 80
                )
            ],
            "cooling": [
                _product(
                    8, "Noctua", "NH-D15", {"type": "air", "socket_support": "AM5"}, 90
                )
            ],
        }

        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(
            cpu_brand=CPUBrand.amd,
            existing_parts=[ComponentCategory.gpu, ComponentCategory.case],
        )
        # Required cats won't include gpu or case
        cats = REQUIRED_CATS - {"gpu", "case"}

        result = await cf.filter_candidates(req, cats, MagicMock())

        assert "gpu" not in result
        assert "case" not in result
        assert "cpu" in result


# ---------------------------------------------------------------------------
# Price floor logic
# ---------------------------------------------------------------------------


class TestPriceFloor:
    def test_low_budget_no_floor(self):
        """0_1000 budget should produce a €0 floor (all products pass)."""
        floor = CandidateFilter._price_floor("0_1000", "low_end_gaming", "gpu")
        assert floor == 0.0

    def test_mid_budget_gpu_floor(self):
        """1500_2000 mid_range_gaming GPU: 1500 × 0.35 = 525."""
        floor = CandidateFilter._price_floor("1500_2000", "mid_range_gaming", "gpu")
        assert floor == 525.0

    def test_high_budget_cpu_floor(self):
        """over_3000 high_end_gaming CPU: 3000 × 0.18 = 540."""
        floor = CandidateFilter._price_floor("over_3000", "high_end_gaming", "cpu")
        assert floor == 540.0

    def test_unknown_goal_no_floor(self):
        floor = CandidateFilter._price_floor("2000_3000", "unknown_goal", "gpu")
        assert floor == 0.0

    def test_unknown_budget_no_floor(self):
        """Unknown budget string falls back to 0.0 via .get() default."""
        floor = CandidateFilter._price_floor("unknown_budget", "mid_range_gaming", "gpu")
        assert floor == 0.0

    def test_peripheral_category_no_floor(self):
        """Categories not in the goal share dict get no floor."""
        floor = CandidateFilter._price_floor("2000_3000", "high_end_gaming", "monitor")
        assert floor == 0.0


class TestApplyPriceFloor:
    def test_zero_floor_passes_all(self):
        items = [_product(i, price=50.0 + i * 10) for i in range(5)]
        result = CandidateFilter._apply_price_floor(items, 0.0)
        assert len(result) == 5

    def test_floor_excludes_cheap(self):
        items = [
            _product(1, price=100.0),
            _product(2, price=200.0),
            _product(3, price=300.0),
            _product(4, price=400.0),
            _product(5, price=500.0),
        ]
        result = CandidateFilter._apply_price_floor(items, 250.0)
        assert len(result) == 3
        assert all(p.price_eur >= 250.0 for p in result)

    def test_fallback_when_fewer_than_3_remain(self):
        """If floor leaves < 3 items but catalog has >= 3, return all."""
        items = [
            _product(1, price=100.0),
            _product(2, price=150.0),
            _product(3, price=200.0),
            _product(4, price=250.0),
        ]
        # Floor at 240 would leave only 1 item — fallback to all 4
        result = CandidateFilter._apply_price_floor(items, 240.0)
        assert len(result) == 4

    def test_no_fallback_when_catalog_small(self):
        """If catalog itself has < 3 items, apply the floor normally."""
        items = [
            _product(1, price=100.0),
            _product(2, price=500.0),
        ]
        result = CandidateFilter._apply_price_floor(items, 200.0)
        assert len(result) == 1
        assert result[0].id == 2

    def test_empty_after_floor_returns_original(self):
        """If all items are below floor, return original list."""
        items = [_product(1, price=50.0), _product(2, price=60.0)]
        result = CandidateFilter._apply_price_floor(items, 1000.0)
        assert len(result) == 2


class TestPriceFloorIntegration:
    async def test_high_budget_excludes_cheap_gpus(self):
        """High budget build should not see budget GPUs."""
        products = {
            "cpu": [
                _product(
                    1, "AMD", "Ryzen 9 9900X", {"socket": "AM5", "tdp": "120"}, 500
                ),
            ],
            "gpu": [
                _product(
                    2,
                    "MSI",
                    "GeForce RTX 5060",
                    {"tdp": "150", "length_mm": "280"},
                    300,
                ),
                _product(
                    3,
                    "MSI",
                    "GeForce RTX 5070",
                    {"tdp": "220", "length_mm": "310"},
                    550,
                ),
                _product(
                    4,
                    "MSI",
                    "GeForce RTX 5080",
                    {"tdp": "300", "length_mm": "330"},
                    800,
                ),
                _product(
                    5,
                    "MSI",
                    "GeForce RTX 5090",
                    {"tdp": "350", "length_mm": "340"},
                    1200,
                ),
            ],
            "motherboard": [
                _product(
                    6,
                    "MSI",
                    "X670E",
                    {
                        "socket": "AM5",
                        "form_factor": "ATX",
                        "ddr_type": "DDR5",
                    },
                    300,
                ),
            ],
            "ram": [
                _product(7, "Corsair", "DDR5 64GB", {"ddr_type": "DDR5"}, 200),
            ],
            "storage": [_product(8, "Samsung", "990 Pro", {"type": "NVMe"}, 150)],
            "psu": [_product(9, "Corsair", "RM1000", {"wattage": "1000"}, 180)],
            "case": [
                _product(
                    10,
                    "NZXT",
                    "H7",
                    {"form_factor": "ATX", "max_gpu_length": "400"},
                    120,
                ),
            ],
            "cooling": [
                _product(
                    11,
                    "Corsair",
                    "H150i",
                    {
                        "type": "liquid",
                        "socket_support": "AM5,LGA1700",
                    },
                    150,
                ),
            ],
        }

        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(
            cpu_brand=CPUBrand.amd,
            budget_range=BudgetRange.over_3000,
            goal=UserGoal.high_end_gaming,
        )

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # GPU floor: 3000 × 0.35 = €1050 → only RTX 5090 (€1200) passes
        # But that leaves < 3 items while catalog has 4 → fallback returns all 4
        # Actually: 4 GPUs total, only 1 >= 1050 → < 3 → fallback
        assert len(result["gpu"]) == 4

    async def test_entry_budget_sees_all(self):
        """0_1000 budget should see all products (floor = €0)."""
        products = {
            "cpu": [
                _product(1, "AMD", "Ryzen 5 7600", {"socket": "AM5", "tdp": "65"}, 180),
                _product(
                    2, "AMD", "Ryzen 5 7500F", {"socket": "AM5", "tdp": "65"}, 140
                ),
            ],
            "gpu": [
                _product(
                    3,
                    "MSI",
                    "GeForce RTX 5060",
                    {"tdp": "150", "length_mm": "280"},
                    300,
                ),
            ],
            "motherboard": [
                _product(
                    4,
                    "MSI",
                    "B650",
                    {
                        "socket": "AM5",
                        "form_factor": "ATX",
                        "ddr_type": "DDR5",
                    },
                    130,
                ),
            ],
            "ram": [_product(5, "Corsair", "DDR5", {"ddr_type": "DDR5"}, 70)],
            "storage": [_product(6, "Samsung", "SSD", {"type": "NVMe"}, 80)],
            "psu": [_product(7, "Corsair", "RM650", {"wattage": "650"}, 80)],
            "case": [
                _product(
                    8,
                    "NZXT",
                    "H5",
                    {"form_factor": "ATX", "max_gpu_length": "400"},
                    70,
                ),
            ],
            "cooling": [
                _product(
                    9,
                    "Noctua",
                    "NH-D15",
                    {"type": "air", "socket_support": "AM5"},
                    80,
                ),
            ],
        }

        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        req = _request(
            cpu_brand=CPUBrand.amd,
            budget_range=BudgetRange.range_0_1000,
            goal=UserGoal.low_end_gaming,
        )

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # All products should pass — no floor applied
        assert len(result["cpu"]) == 2
        assert len(result["gpu"]) == 1

    async def test_mid_budget_filters_cheap_gpus(self):
        """Mid budget should exclude cheap GPUs when enough remain above floor."""
        products = {
            "cpu": [
                _product(
                    1, "AMD", "Ryzen 5 7600X", {"socket": "AM5", "tdp": "105"}, 250
                ),
            ],
            "gpu": [
                _product(
                    10,
                    "MSI",
                    "GeForce GTX 1650",
                    {"tdp": "75", "length_mm": "200"},
                    150,
                ),
                _product(
                    11,
                    "MSI",
                    "GeForce RTX 5060",
                    {"tdp": "150", "length_mm": "280"},
                    300,
                ),
                _product(
                    12,
                    "MSI",
                    "GeForce RTX 5070",
                    {"tdp": "220", "length_mm": "310"},
                    550,
                ),
                _product(
                    13,
                    "ASUS",
                    "GeForce RTX 5070 Ti",
                    {"tdp": "250", "length_mm": "320"},
                    650,
                ),
                _product(
                    14,
                    "MSI",
                    "GeForce RTX 5080",
                    {"tdp": "300", "length_mm": "330"},
                    800,
                ),
            ],
            "motherboard": [
                _product(
                    2,
                    "MSI",
                    "B650",
                    {
                        "socket": "AM5",
                        "form_factor": "ATX",
                        "ddr_type": "DDR5",
                    },
                    150,
                ),
            ],
            "ram": [_product(3, "Corsair", "DDR5", {"ddr_type": "DDR5"}, 80)],
            "storage": [_product(4, "Samsung", "SSD", {"type": "NVMe"}, 100)],
            "psu": [_product(5, "Corsair", "RM750", {"wattage": "750"}, 100)],
            "case": [
                _product(
                    6,
                    "NZXT",
                    "H5",
                    {"form_factor": "ATX", "max_gpu_length": "400"},
                    80,
                ),
            ],
            "cooling": [
                _product(
                    7,
                    "Noctua",
                    "NH-D15",
                    {"type": "air", "socket_support": "AM5"},
                    90,
                ),
            ],
        }

        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        # 1500_2000 mid_range_gaming: GPU floor = 1500 × 0.35 = €525
        req = _request(
            cpu_brand=CPUBrand.amd,
            budget_range=BudgetRange.range_1500_2000,
            goal=UserGoal.mid_range_gaming,
        )

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # GPU floor €525 → GTX 1650 (€150), RTX 5060 (€300) excluded
        # RTX 5070 (€550), RTX 5070 Ti (€650), RTX 5080 (€800) remain → 3 items ≥ 3
        assert len(result["gpu"]) == 3
        assert all(p.price_eur >= 525.0 for p in result["gpu"])

    async def test_heavy_work_goal_different_allocation(self):
        """Non-gaming goal (heavy_work) weights CPU/RAM higher, GPU lower."""
        products = {
            "cpu": [
                _product(
                    1, "AMD", "Ryzen 5 7600", {"socket": "AM5", "tdp": "65"}, 200
                ),
                _product(
                    2, "AMD", "Ryzen 7 7700X", {"socket": "AM5", "tdp": "105"}, 300
                ),
                _product(
                    3, "AMD", "Ryzen 9 7900X", {"socket": "AM5", "tdp": "170"}, 400
                ),
                _product(
                    4, "AMD", "Ryzen 9 7950X", {"socket": "AM5", "tdp": "170"}, 550
                ),
            ],
            "gpu": [
                _product(
                    10,
                    "MSI",
                    "GeForce RTX 5060",
                    {"tdp": "150", "length_mm": "280"},
                    300,
                ),
                _product(
                    11,
                    "MSI",
                    "GeForce RTX 5070",
                    {"tdp": "220", "length_mm": "310"},
                    550,
                ),
                _product(
                    12,
                    "MSI",
                    "GeForce RTX 5080",
                    {"tdp": "300", "length_mm": "330"},
                    800,
                ),
            ],
            "motherboard": [
                _product(
                    20,
                    "MSI",
                    "B650",
                    {
                        "socket": "AM5",
                        "form_factor": "ATX",
                        "ddr_type": "DDR5",
                    },
                    150,
                ),
            ],
            "ram": [
                _product(30, "Corsair", "DDR5 16GB", {"ddr_type": "DDR5"}, 60),
                _product(31, "Kingston", "DDR5 32GB", {"ddr_type": "DDR5"}, 100),
                _product(32, "G.Skill", "DDR5 64GB", {"ddr_type": "DDR5"}, 250),
            ],
            "storage": [_product(40, "Samsung", "SSD", {"type": "NVMe"}, 100)],
            "psu": [_product(50, "Corsair", "RM850", {"wattage": "850"}, 120)],
            "case": [
                _product(
                    60,
                    "NZXT",
                    "H5",
                    {"form_factor": "ATX", "max_gpu_length": "400"},
                    80,
                ),
            ],
            "cooling": [
                _product(
                    70,
                    "Noctua",
                    "NH-D15",
                    {"type": "air", "socket_support": "AM5"},
                    90,
                ),
            ],
        }

        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        # 2000_3000 heavy_work: GPU share=0.20, CPU share=0.25
        req = _request(
            cpu_brand=CPUBrand.amd,
            budget_range=BudgetRange.range_2000_3000,
            goal=UserGoal.heavy_work,
        )

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # GPU floor = 2000 × 0.20 = €400 → RTX 5060 (€300) excluded
        # RTX 5070 (€550), RTX 5080 (€800) remain → 2 < 3, but catalog has 3 → fallback
        assert len(result["gpu"]) == 3

        # CPU floor = 2000 × 0.25 = €500 → only Ryzen 9 7950X (€550) passes
        # 1 < 3, catalog has 4 → fallback
        assert len(result["cpu"]) == 4

        # RAM floor = 2000 × 0.15 = €300 → all below → fallback
        assert len(result["ram"]) == 3

    async def test_compatibility_filter_then_price_floor(self):
        """Price floor applies to post-compatibility-filter results."""
        products = {
            "cpu": [
                # 3 AMD CPUs + 3 Intel CPUs
                _product(
                    1, "AMD", "Ryzen 5 7600", {"socket": "AM5", "tdp": "65"}, 200
                ),
                _product(
                    2, "AMD", "Ryzen 7 7700X", {"socket": "AM5", "tdp": "105"}, 350
                ),
                _product(
                    3, "AMD", "Ryzen 9 7900X", {"socket": "AM5", "tdp": "170"}, 500
                ),
                _product(
                    4, "Intel", "i5-14600K", {"socket": "LGA1700", "tdp": "125"}, 280
                ),
                _product(
                    5, "Intel", "i7-14700K", {"socket": "LGA1700", "tdp": "125"}, 380
                ),
                _product(
                    6, "Intel", "i9-14900K", {"socket": "LGA1700", "tdp": "125"}, 530
                ),
            ],
            "gpu": [
                _product(
                    10,
                    "MSI",
                    "GeForce RTX 5070",
                    {"tdp": "220", "length_mm": "310"},
                    550,
                ),
            ],
            "motherboard": [
                _product(
                    20,
                    "MSI",
                    "B650",
                    {
                        "socket": "AM5",
                        "form_factor": "ATX",
                        "ddr_type": "DDR5",
                    },
                    150,
                ),
            ],
            "ram": [_product(30, "Corsair", "DDR5", {"ddr_type": "DDR5"}, 80)],
            "storage": [_product(40, "Samsung", "SSD", {"type": "NVMe"}, 100)],
            "psu": [_product(50, "Corsair", "RM750", {"wattage": "750"}, 100)],
            "case": [
                _product(
                    60,
                    "NZXT",
                    "H5",
                    {"form_factor": "ATX", "max_gpu_length": "400"},
                    80,
                ),
            ],
            "cooling": [
                _product(
                    70,
                    "Noctua",
                    "NH-D15",
                    {"type": "air", "socket_support": "AM5"},
                    90,
                ),
            ],
        }

        catalog = _mock_catalog(products)
        cf = CandidateFilter(catalog=catalog)
        # AMD preference: compatibility filter keeps only 3 AMD CPUs
        # CPU floor = 1500 × 0.20 = €300 → Ryzen 5 7600 (€200) excluded
        # 2 remain (€350, €500) < 3 threshold, but post-compat set has 3 → fallback
        req = _request(
            cpu_brand=CPUBrand.amd,
            budget_range=BudgetRange.range_1500_2000,
            goal=UserGoal.mid_range_gaming,
        )

        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # Compatibility filter removed Intel CPUs → 3 AMD CPUs remain
        # Price floor leaves 2 < 3, original post-compat has 3 → fallback to all 3
        assert len(result["cpu"]) == 3
        assert all(c.brand == "AMD" for c in result["cpu"])


# ---------------------------------------------------------------------------
# Hash normalization tests (guardrails.py Change 4)
# ---------------------------------------------------------------------------


class TestHashNormalization:
    def test_trivial_notes_normalized_to_none(self):
        from app.security.guardrails import hash_build_request

        base = _request(notes=None)
        h_none = hash_build_request(base)

        for trivial in ["none", "Nothing", "N/A", "-", ".", "  none  "]:
            req = _request(notes=trivial)
            assert hash_build_request(req) == h_none, (
                f"'{trivial}' should hash same as None"
            )

    def test_no_is_not_trivial(self):
        """'no' alone could be shorthand (e.g. 'no RGB') — treat as meaningful."""
        from app.security.guardrails import hash_build_request

        h_none = hash_build_request(_request(notes=None))
        h_no = hash_build_request(_request(notes="no"))
        assert h_no != h_none

    def test_meaningful_notes_differ(self):
        from app.security.guardrails import hash_build_request

        h1 = hash_build_request(_request(notes="I want a quiet PC"))
        h2 = hash_build_request(_request(notes="I want a loud PC"))
        assert h1 != h2

    def test_existing_parts_order_independent(self):
        from app.security.guardrails import hash_build_request

        r1 = _request(existing_parts=[ComponentCategory.gpu, ComponentCategory.cpu])
        r2 = _request(existing_parts=[ComponentCategory.cpu, ComponentCategory.gpu])
        assert hash_build_request(r1) == hash_build_request(r2)
