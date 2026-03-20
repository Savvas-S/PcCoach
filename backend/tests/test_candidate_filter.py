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
# Hash normalization tests (guardrails.py Change 4)
# ---------------------------------------------------------------------------


class TestHashNormalization:
    def test_trivial_notes_normalized_to_none(self):
        from app.security.guardrails import hash_build_request

        base = _request(notes=None)
        h_none = hash_build_request(base)

        for trivial in ["none", "Nothing", "N/A", "no", "-", ".", "  none  "]:
            req = _request(notes=trivial)
            assert hash_build_request(req) == h_none, (
                f"'{trivial}' should hash same as None"
            )

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
