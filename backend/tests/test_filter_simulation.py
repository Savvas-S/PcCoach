"""Stress-test the CandidateFilter with a large (~1000 product) synthetic catalog.

Simulates realistic build scenarios to verify that brand preferences, platform
compatibility constraints, and the max-per-category cap all behave correctly
at scale.
"""

from __future__ import annotations

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
# Catalog generation helpers
# ---------------------------------------------------------------------------

_NEXT_ID = 0


def _next_id() -> int:
    global _NEXT_ID
    _NEXT_ID += 1
    return _NEXT_ID


def _reset_ids() -> None:
    global _NEXT_ID
    _NEXT_ID = 0


def _p(
    brand: str,
    model: str,
    specs: dict,
    price: float = 100.0,
) -> ToolCatalogResult:
    return ToolCatalogResult(
        id=_next_id(),
        brand=brand,
        model=model,
        specs=specs,
        price_eur=price,
    )


def _generate_catalog(n: int = 1000) -> dict[str, list[ToolCatalogResult]]:
    """Create a realistic synthetic catalog with ~n products across 8 categories.

    Distribution (approximate):
      - cpu          : 100
      - gpu          : 120
      - motherboard  : 100
      - ram          : 100
      - storage      : 100
      - psu          : 100
      - case         : 100
      - cooling      :  80
      - monitor      :  40  (peripherals)
      - keyboard     :  30
      - mouse        :  30
    """
    _reset_ids()
    catalog: dict[str, list[ToolCatalogResult]] = {
        cat: [] for cat in [
            "cpu", "gpu", "motherboard", "ram", "storage",
            "psu", "case", "cooling", "monitor", "keyboard", "mouse",
        ]
    }

    # ------------------------------------------------------------------
    # CPUs — 100 products
    # AM5: 25, AM4: 25, LGA1851: 25, LGA1700: 25
    # ------------------------------------------------------------------
    amd_am5_cpus = [
        ("AMD", f"Ryzen 9 9950X{'3D' if i % 5 == 0 else ''}", "AM5", 170)
        for i in range(5)
    ] + [
        ("AMD", f"Ryzen 7 9700X Variant{i}", "AM5", 105)
        for i in range(10)
    ] + [
        ("AMD", f"Ryzen 5 9600X Variant{i}", "AM5", 65)
        for i in range(10)
    ]
    amd_am4_cpus = [
        ("AMD", f"Ryzen 9 5950X Variant{i}", "AM4", 170)
        for i in range(7)
    ] + [
        ("AMD", f"Ryzen 7 5800X Variant{i}", "AM4", 105)
        for i in range(9)
    ] + [
        ("AMD", f"Ryzen 5 5600X Variant{i}", "AM4", 65)
        for i in range(9)
    ]
    intel_lga1851_cpus = [
        ("Intel", f"Core Ultra 9 285K Variant{i}", "LGA1851", 250)
        for i in range(6)
    ] + [
        ("Intel", f"Core Ultra 7 265K Variant{i}", "LGA1851", 125)
        for i in range(10)
    ] + [
        ("Intel", f"Core Ultra 5 245K Variant{i}", "LGA1851", 65)
        for i in range(9)
    ]
    intel_lga1700_cpus = [
        ("Intel", f"Core i9-14900K Variant{i}", "LGA1700", 253)
        for i in range(6)
    ] + [
        ("Intel", f"Core i7-14700K Variant{i}", "LGA1700", 125)
        for i in range(10)
    ] + [
        ("Intel", f"Core i5-14600K Variant{i}", "LGA1700", 65)
        for i in range(9)
    ]

    # Interleave AMD and Intel CPUs so that the first _MAX_PER_CATEGORY entries
    # contain both brands — otherwise the cap would hide one platform entirely.
    amd_all = amd_am5_cpus + amd_am4_cpus
    intel_all = intel_lga1851_cpus + intel_lga1700_cpus
    # Zip the two lists together so odd slots are AMD, even are Intel
    all_cpu_specs: list[tuple[str, str, str, int]] = []
    for amd_item, intel_item in zip(amd_all, intel_all):
        all_cpu_specs.append(amd_item)
        all_cpu_specs.append(intel_item)
    # Append any remainder (when list lengths differ)
    max_len = max(len(amd_all), len(intel_all))
    if len(amd_all) > len(intel_all):
        all_cpu_specs.extend(amd_all[len(intel_all):])
    else:
        all_cpu_specs.extend(intel_all[len(amd_all):])

    for brand, model, socket, tdp in all_cpu_specs:
        price = 100.0 + tdp * 1.5
        catalog["cpu"].append(
            _p(brand, model, {"socket": socket, "tdp": str(tdp), "cores": "16"}, price)
        )

    # ------------------------------------------------------------------
    # GPUs — 120 products
    # NVIDIA: 60, AMD: 60
    # ------------------------------------------------------------------
    nvidia_models = [
        ("MSI", "GeForce RTX 5090", 575, 355),
        ("ASUS", "ROG Strix GeForce RTX 5080", 320, 340),
        ("Gigabyte", "GeForce RTX 5070 Ti", 285, 320),
        ("MSI", "GeForce RTX 5070", 250, 310),
        ("ASUS", "TUF GeForce RTX 5060 Ti", 185, 285),
        ("Zotac", "GeForce RTX 5060", 150, 260),
    ]
    amd_models = [
        ("Sapphire", "Radeon RX 9070 XT", 304, 360),
        ("PowerColor", "Radeon RX 9070", 220, 345),
        ("XFX", "Radeon RX 7900 XTX", 355, 360),
        ("Sapphire", "Radeon RX 7900 XT", 315, 340),
        ("ASRock", "Radeon RX 7800 XT", 263, 310),
        ("MSI", "Radeon RX 7600 XT", 165, 260),
    ]

    # Interleave NVIDIA and AMD GPUs so both brands appear within the first
    # _MAX_PER_CATEGORY entries — otherwise the cap would hide one brand entirely.
    nvidia_entries = [
        (brand, f"{model} v{i}", tdp, length)
        for i in range(10)
        for brand, model, tdp, length in nvidia_models
    ]
    amd_entries = [
        (brand, f"{model} v{i}", tdp, length)
        for i in range(10)
        for brand, model, tdp, length in amd_models
    ]
    # Interleave: alternate NVIDIA/AMD pairs
    for (nb, nm, nt, nl), (ab, am, at_, al) in zip(nvidia_entries, amd_entries):
        catalog["gpu"].append(
            _p(nb, nm, {"tdp": str(nt), "length_mm": str(nl), "vram_gb": "16"}, float(400 + nt))
        )
        catalog["gpu"].append(
            _p(ab, am, {"tdp": str(at_), "length_mm": str(al), "vram_gb": "16"}, float(380 + at_))
        )
    # Append remainder if lists differ in length
    for brand, model, tdp, length in nvidia_entries[len(amd_entries):]:
        catalog["gpu"].append(
            _p(brand, model, {"tdp": str(tdp), "length_mm": str(length), "vram_gb": "16"}, float(400 + tdp))
        )
    for brand, model, tdp, length in amd_entries[len(nvidia_entries):]:
        catalog["gpu"].append(
            _p(brand, model, {"tdp": str(tdp), "length_mm": str(length), "vram_gb": "16"}, float(380 + tdp))
        )

    # ------------------------------------------------------------------
    # Motherboards — 100 products
    # 4 sockets × 3 form factors × ~8 boards each
    # ------------------------------------------------------------------
    mobo_configs = [
        ("MSI", "MAG B650", "AM5", "ATX", "DDR5"),
        ("ASUS", "ROG Strix X670E", "AM5", "ATX", "DDR5"),
        ("Gigabyte", "B650M DS3H", "AM5", "micro_atx", "DDR5"),
        ("ASRock", "B650M ITX", "AM5", "mini_itx", "DDR5"),
        ("MSI", "B550", "AM4", "ATX", "DDR4"),
        ("ASUS", "X570", "AM4", "ATX", "DDR4"),
        ("Gigabyte", "B450M", "AM4", "micro_atx", "DDR4"),
        ("ASRock", "B550M ITX/ac", "AM4", "mini_itx", "DDR4"),
        ("MSI", "Z890 Tomahawk", "LGA1851", "ATX", "DDR5"),
        ("ASUS", "ROG Maximus Z890", "LGA1851", "ATX", "DDR5"),
        ("Gigabyte", "B860M DS3H", "LGA1851", "micro_atx", "DDR5"),
        ("ASRock", "Z890I Nova WiFi", "LGA1851", "mini_itx", "DDR5"),
        ("MSI", "Z790 Tomahawk", "LGA1700", "ATX", "DDR5"),
        ("ASUS", "ProArt Z790-Creator", "LGA1700", "ATX", "DDR5"),
        ("Gigabyte", "B760M DS3H", "LGA1700", "micro_atx", "DDR5"),
        ("ASRock", "Z790M ITX", "LGA1700", "mini_itx", "DDR5"),
    ]
    # Also include DDR4 variants for LGA1700 for variety
    mobo_lga1700_ddr4 = [
        ("MSI", "Z790 DDR4 Edition", "LGA1700", "ATX", "DDR4"),
        ("ASUS", "Z790-P DDR4", "LGA1700", "ATX", "DDR4"),
        ("Gigabyte", "B760M DDR4", "LGA1700", "micro_atx", "DDR4"),
    ]
    all_mobo_configs = mobo_configs + mobo_lga1700_ddr4

    # Generate variants to reach ~100
    for i in range(6):
        for brand, model, socket, ff, ddr in all_mobo_configs[:16]:
            catalog["motherboard"].append(
                _p(
                    brand,
                    f"{model} v{i}",
                    {"socket": socket, "form_factor": ff, "ddr_type": ddr, "chipset": "B"},
                    float(150 + i * 15),
                )
            )
            if len(catalog["motherboard"]) >= 100:
                break
        if len(catalog["motherboard"]) >= 100:
            break

    # ------------------------------------------------------------------
    # RAM — 100 products (DDR4 and DDR5)
    # ------------------------------------------------------------------
    ram_configs = [
        ("Corsair", "Vengeance DDR5-6000", "DDR5", "32", "6000"),
        ("G.Skill", "Trident Z5 DDR5-7200", "DDR5", "32", "7200"),
        ("Kingston", "Fury Beast DDR5-5200", "DDR5", "16", "5200"),
        ("Crucial", "Pro DDR5-5600", "DDR5", "64", "5600"),
        ("TeamGroup", "T-Force DDR5-6400", "DDR5", "32", "6400"),
        ("Corsair", "Vengeance LPX DDR4-3200", "DDR4", "32", "3200"),
        ("G.Skill", "Ripjaws V DDR4-3600", "DDR4", "32", "3600"),
        ("Kingston", "HyperX Fury DDR4-2666", "DDR4", "16", "2666"),
        ("Crucial", "Ballistix DDR4-3200", "DDR4", "32", "3200"),
        ("TeamGroup", "Vulcan Z DDR4-3000", "DDR4", "16", "3000"),
    ]
    for i in range(10):
        for brand, model, ddr, cap, speed in ram_configs:
            catalog["ram"].append(
                _p(
                    brand,
                    f"{model} v{i}",
                    {"ddr_type": ddr, "capacity_gb": cap, "speed_mhz": speed, "modules": "2"},
                    float(60 + i * 5),
                )
            )

    # ------------------------------------------------------------------
    # Storage — 100 products
    # ------------------------------------------------------------------
    storage_configs = [
        ("Samsung", "990 Pro", "NVMe", "1000", "7450"),
        ("WD", "Black SN850X", "NVMe", "2000", "7300"),
        ("Seagate", "FireCuda 530", "NVMe", "4000", "7300"),
        ("Corsair", "MP600 Pro LPX", "NVMe", "2000", "7100"),
        ("Kingston", "KC3000", "NVMe", "1000", "7000"),
        ("Samsung", "870 EVO", "SATA", "1000", "560"),
        ("WD", "Blue 3D NAND", "SATA", "2000", "560"),
        ("Seagate", "BarraCuda", "SATA", "4000", "540"),
        ("Crucial", "MX500", "SATA", "1000", "560"),
        ("Kingston", "A400 SSD", "SATA", "480", "500"),
    ]
    for i in range(10):
        for brand, model, stype, cap, read_mbps in storage_configs:
            catalog["storage"].append(
                _p(
                    brand,
                    f"{model} v{i}",
                    {"type": stype, "capacity_gb": cap, "interface": "M.2", "read_mbps": read_mbps},
                    float(80 + i * 10),
                )
            )

    # ------------------------------------------------------------------
    # PSUs — 100 products (450W–1200W)
    # ------------------------------------------------------------------
    psu_configs = [
        ("Corsair", "RM1000x", "1000"),
        ("Seasonic", "Focus GX-850", "850"),
        ("be quiet!", "Straight Power 12 750W", "750"),
        ("EVGA", "SuperNOVA 650 G6", "650"),
        ("Corsair", "CX550", "550"),
        ("Seasonic", "Focus GM-1200", "1200"),
        ("be quiet!", "Pure Power 12 M 750W", "750"),
        ("ASUS", "ROG Thor 850P", "850"),
        ("MSI", "MEG Ai1000P", "1000"),
        ("Thermaltake", "Toughpower GF3 650W", "650"),
    ]
    for i in range(10):
        for brand, model, wattage in psu_configs:
            catalog["psu"].append(
                _p(
                    brand,
                    f"{model} v{i}",
                    {"wattage": wattage, "efficiency": "80+ Gold"},
                    float(80 + int(wattage) * 0.1 + i * 5),
                )
            )

    # ------------------------------------------------------------------
    # Cases — 100 products (ATX / micro_atx / mini_itx, max_gpu_length 280-420mm)
    # ------------------------------------------------------------------
    case_configs = [
        ("NZXT", "H9 Flow", "ATX", "400"),
        ("Fractal Design", "North", "ATX", "420"),
        ("Lian Li", "PC-O11 Dynamic", "ATX", "380"),
        ("Corsair", "5000D Airflow", "ATX", "400"),
        ("NZXT", "H5 Flow", "micro_atx", "360"),
        ("Fractal Design", "Pop Mini", "micro_atx", "350"),
        ("Cooler Master", "NR400", "micro_atx", "340"),
        ("Lian Li", "Q58 ITX", "mini_itx", "320"),
        ("NZXT", "H1 V2", "mini_itx", "305"),
        ("Cooler Master", "MasterBox NR200P", "mini_itx", "330"),
    ]
    for i in range(10):
        for brand, model, ff, gpu_len in case_configs:
            catalog["case"].append(
                _p(
                    brand,
                    f"{model} v{i}",
                    {"form_factor": ff, "max_gpu_length": gpu_len},
                    float(70 + i * 10),
                )
            )

    # ------------------------------------------------------------------
    # Coolers — 80 products (air + liquid, various socket support combos)
    # ------------------------------------------------------------------
    # Socket support combos: some AMD-only, some Intel-only, most both
    cooler_configs = [
        ("Noctua", "NH-D15", "air", "AM5,AM4,LGA1851,LGA1700"),
        ("be quiet!", "Dark Rock Pro 5", "air", "AM5,AM4,LGA1851,LGA1700"),
        ("Cooler Master", "Hyper 212 Halo", "air", "AM5,AM4,LGA1851,LGA1700"),
        ("Thermalright", "Peerless Assassin 120", "air", "AM5,AM4,LGA1851,LGA1700"),
        ("DeepCool", "AK620", "air", "AM5,AM4,LGA1700"),
        ("Corsair", "H150i Elite LCD", "liquid", "AM5,AM4,LGA1851,LGA1700"),
        ("NZXT", "Kraken Elite 240", "liquid", "AM5,AM4,LGA1851,LGA1700"),
        ("be quiet!", "Silent Loop 3 360", "liquid", "AM5,LGA1851,LGA1700"),
        ("Cooler Master", "MasterLiquid 360L Core", "liquid", "AM5,AM4,LGA1851,LGA1700"),
        ("Lian Li", "Galahad II 360", "liquid", "AM5,AM4,LGA1851,LGA1700"),
    ]
    for i in range(8):
        for brand, model, ctype, sockets in cooler_configs:
            catalog["cooling"].append(
                _p(
                    brand,
                    f"{model} v{i}",
                    {
                        "type": ctype,
                        "socket_support": sockets,
                        "radiator_mm": "360" if ctype == "liquid" else "0",
                    },
                    float(60 + i * 10),
                )
            )

    # ------------------------------------------------------------------
    # Peripherals — monitors, keyboards, mice
    # ------------------------------------------------------------------
    for i in range(40):
        catalog["monitor"].append(
            _p(
                "LG" if i % 2 == 0 else "Samsung",
                f"UltraWide Monitor {i}",
                {"resolution": "2560x1440", "size_inches": "27", "panel": "IPS", "refresh_hz": "165"},
                float(250 + i * 10),
            )
        )
    for i in range(30):
        catalog["keyboard"].append(
            _p(
                "Logitech" if i % 2 == 0 else "Corsair",
                f"Mechanical Keyboard {i}",
                {"type": "mechanical", "switch": "Cherry MX Red", "layout": "full"},
                float(80 + i * 5),
            )
        )
    for i in range(30):
        catalog["mouse"].append(
            _p(
                "Razer" if i % 2 == 0 else "Logitech",
                f"Gaming Mouse {i}",
                {"sensor": "PixArt 3395", "weight_g": "95", "wireless": "false"},
                float(50 + i * 5),
            )
        )

    return catalog


def _mock_catalog_from(
    products: dict[str, list[ToolCatalogResult]],
) -> MagicMock:
    """Create a mock CatalogService whose scout_all returns the given products."""
    catalog = MagicMock()
    catalog.scout_all = AsyncMock(return_value=products)
    return catalog


# ---------------------------------------------------------------------------
# Request factory
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Simulation test class
# ---------------------------------------------------------------------------


class TestBuildSimulations:
    """Simulates realistic build scenarios against a large synthetic catalog."""

    # Shared catalog for all simulation tests (generated once per class).
    # Each test method uses the same catalog but a fresh CandidateFilter.
    _catalog: dict[str, list[ToolCatalogResult]] | None = None

    @classmethod
    def _get_catalog(cls) -> dict[str, list[ToolCatalogResult]]:
        if cls._catalog is None:
            cls._catalog = _generate_catalog(1000)
        return cls._catalog

    def _make_filter(
        self, products: dict[str, list[ToolCatalogResult]] | None = None
    ) -> CandidateFilter:
        if products is None:
            products = self._get_catalog()
        return CandidateFilter(catalog=_mock_catalog_from(products))

    # ------------------------------------------------------------------
    # a) AMD gaming ATX build
    # ------------------------------------------------------------------

    async def test_amd_gaming_atx_build(self):
        cf = self._make_filter()
        req = _request(
            cpu_brand=CPUBrand.amd,
            gpu_brand=GPUBrand.no_preference,
            form_factor=FormFactor.atx,
            cooling_preference=CoolingPreference.no_preference,
        )
        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # All CPUs must be AMD
        assert result["cpu"], "Expected at least one AMD CPU"
        assert all(p.brand.lower() == "amd" for p in result["cpu"]), (
            "Non-AMD CPUs leaked through"
        )

        # All mobos must have AM5 or AM4 sockets
        amd_sockets = {"AM5", "AM4"}
        assert result["motherboard"], "Expected at least one motherboard"
        for mobo in result["motherboard"]:
            assert mobo.specs.get("socket") in amd_sockets, (
                f"Mobo has non-AMD socket: {mobo.specs.get('socket')}"
            )

        # RAM DDR type must match mobo DDR types
        mobo_ddr_types = {m.specs.get("ddr_type") for m in result["motherboard"]}
        for ram in result["ram"]:
            assert ram.specs.get("ddr_type") in mobo_ddr_types, (
                f"RAM DDR type {ram.specs.get('ddr_type')} not in mobo DDR types {mobo_ddr_types}"
            )

        # Cases must fit ATX motherboards (form_factor rank >= 3)
        from app.services.build_validator import _FF_RANK
        for case in result["case"]:
            case_ff = case.specs.get("form_factor", "").lower()
            case_rank = _FF_RANK.get(case_ff, 0)
            assert case_rank >= 3, (
                f"Case {case.model} has rank {case_rank} — too small for ATX"
            )

        # PSUs must meet minimum wattage
        catalog_products = self._get_catalog()
        cpus_all = [p for p in catalog_products["cpu"] if p.brand.lower() == "amd"]
        gpus_all = catalog_products["gpu"]
        min_wattage = CandidateFilter._min_psu_wattage(cpus_all, gpus_all)
        if min_wattage > 0:
            for psu in result["psu"]:
                w = float(psu.specs.get("wattage", 0))
                assert w >= min_wattage, (
                    f"PSU {psu.model} wattage {w} < minimum {min_wattage}"
                )

    # ------------------------------------------------------------------
    # b) Intel gaming micro-ATX with liquid cooling
    # ------------------------------------------------------------------

    async def test_intel_gaming_micro_atx_liquid(self):
        cf = self._make_filter()
        req = _request(
            cpu_brand=CPUBrand.intel,
            gpu_brand=GPUBrand.nvidia,
            form_factor=FormFactor.micro_atx,
            cooling_preference=CoolingPreference.liquid,
        )
        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        # All CPUs must be Intel
        assert result["cpu"], "Expected at least one Intel CPU"
        assert all(p.brand.lower() == "intel" for p in result["cpu"])

        # All GPUs must be NVIDIA (GeForce / RTX / GTX in model name)
        assert result["gpu"], "Expected at least one NVIDIA GPU"
        for gpu in result["gpu"]:
            model_lower = gpu.model.lower()
            assert any(kw in model_lower for kw in ["geforce", "rtx", "gtx"]), (
                f"Non-NVIDIA GPU leaked: {gpu.model}"
            )

        # Motherboards must be micro_atx or smaller, with Intel sockets
        intel_sockets = {"LGA1851", "LGA1700"}
        from app.services.build_validator import _FF_RANK
        assert result["motherboard"], "Expected at least one motherboard"
        for mobo in result["motherboard"]:
            assert mobo.specs.get("socket") in intel_sockets, (
                f"Mobo has non-Intel socket: {mobo.specs.get('socket')}"
            )
            ff = mobo.specs.get("form_factor", "").lower()
            rank = _FF_RANK.get(ff, 0)
            assert rank <= 2, (
                f"Mobo form factor {ff!r} (rank {rank}) too large for micro_atx request"
            )

        # Cooling must be liquid
        assert result["cooling"], "Expected at least one liquid cooler"
        for cooler in result["cooling"]:
            assert cooler.specs.get("type") == "liquid", (
                f"Non-liquid cooler leaked: {cooler.model}"
            )

        # Cooling must support at least one Intel socket
        for cooler in result["cooling"]:
            support_raw = cooler.specs.get("socket_support", "")
            supported = {s.strip() for s in support_raw.split(",")}
            assert supported & intel_sockets, (
                f"Cooler {cooler.model} has no Intel socket support: {support_raw}"
            )

        # Cases must fit micro_atx or larger
        for case in result["case"]:
            case_ff = case.specs.get("form_factor", "").lower()
            case_rank = _FF_RANK.get(case_ff, 0)
            assert case_rank >= 2, (
                f"Case {case.model} (rank {case_rank}) too small for micro_atx"
            )

    # ------------------------------------------------------------------
    # c) No CPU/GPU preference keeps both platforms
    # ------------------------------------------------------------------

    async def test_no_preference_keeps_both_platforms(self):
        cf = self._make_filter()
        req = _request(
            cpu_brand=CPUBrand.no_preference,
            gpu_brand=GPUBrand.no_preference,
            form_factor=FormFactor.atx,
        )
        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        cpu_brands = {p.brand.lower() for p in result["cpu"]}
        assert "amd" in cpu_brands, "AMD CPUs missing when no_preference"
        assert "intel" in cpu_brands, "Intel CPUs missing when no_preference"

        # Both NVIDIA and AMD GPUs should be present
        def _is_nvidia(model: str) -> bool:
            m = model.lower()
            return any(kw in m for kw in ["geforce", "rtx", "gtx"])

        def _is_amd_gpu(model: str) -> bool:
            m = model.lower()
            return any(kw in m for kw in ["radeon", "rx "])

        gpu_models = result["gpu"]
        has_nvidia = any(_is_nvidia(g.model) for g in gpu_models)
        has_amd = any(_is_amd_gpu(g.model) for g in gpu_models)
        assert has_nvidia, "NVIDIA GPUs missing when no GPU preference"
        assert has_amd, "AMD GPUs missing when no GPU preference"

    # ------------------------------------------------------------------
    # d) Mini-ITX severely constrains options
    # ------------------------------------------------------------------

    async def test_mini_itx_severely_constrains_options(self):
        """Mini-ITX must restrict motherboards to mini_itx only, and cases to those
        that fit mini-ITX or larger (i.e., all form factors). The raw (pre-cap)
        candidate pool for motherboards must be smaller than in an ATX build."""
        catalog = self._get_catalog()
        db = MagicMock()

        req_mini = _request(form_factor=FormFactor.mini_itx)
        req_atx = _request(form_factor=FormFactor.atx)

        result_mini = await self._make_filter().filter_candidates(req_mini, REQUIRED_CATS, db)
        result_atx = await self._make_filter().filter_candidates(req_atx, REQUIRED_CATS, db)

        # All mini-ITX result mobos must be mini_itx
        for mobo in result_mini["motherboard"]:
            ff = mobo.specs.get("form_factor", "").lower()
            assert ff in {"mini_itx", "mini-itx"}, (
                f"Non mini-ITX mobo in mini-ITX build: {ff}"
            )

        # Cases must have a known form factor
        from app.services.build_validator import _FF_RANK
        for case in result_mini["case"]:
            case_ff = case.specs.get("form_factor", "").lower()
            case_rank = _FF_RANK.get(case_ff, 0)
            assert case_rank >= 1, f"Unknown case form factor: {case_ff}"

        # The raw motherboard pool for mini-ITX must be smaller than for ATX.
        # We compute this by directly running the filter logic on the full catalog.
        valid_sockets_any = None  # no_preference → all sockets
        requested_atx_rank = _FF_RANK["atx"]   # 3
        requested_itx_rank = _FF_RANK["mini_itx"]  # 1

        all_mobos = catalog["motherboard"]
        raw_atx = CandidateFilter._filter_motherboards(
            all_mobos, valid_sockets_any, requested_atx_rank
        )
        raw_itx = CandidateFilter._filter_motherboards(
            all_mobos, valid_sockets_any, requested_itx_rank
        )
        assert len(raw_itx) < len(raw_atx), (
            f"Mini-ITX raw mobo pool ({len(raw_itx)}) should be smaller than "
            f"ATX raw mobo pool ({len(raw_atx)})"
        )

    # ------------------------------------------------------------------
    # e) Air cooling filters out liquid coolers
    # ------------------------------------------------------------------

    async def test_air_cooling_filters_liquid(self):
        cf = self._make_filter()
        req = _request(cooling_preference=CoolingPreference.air)
        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert result["cooling"], "Expected at least one air cooler"
        for cooler in result["cooling"]:
            assert cooler.specs.get("type") == "air", (
                f"Liquid cooler leaked through: {cooler.model}"
            )

    # ------------------------------------------------------------------
    # f) NVIDIA GPU preference
    # ------------------------------------------------------------------

    async def test_nvidia_gpu_preference(self):
        cf = self._make_filter()
        req = _request(gpu_brand=GPUBrand.nvidia)
        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert result["gpu"], "Expected at least one NVIDIA GPU"
        for gpu in result["gpu"]:
            model_lower = gpu.model.lower()
            assert any(kw in model_lower for kw in ["geforce", "rtx", "gtx"]), (
                f"Non-NVIDIA GPU present: {gpu.model}"
            )
            assert not any(kw in model_lower for kw in ["radeon", "rx "]), (
                f"AMD GPU leaked: {gpu.model}"
            )

    # ------------------------------------------------------------------
    # g) AMD GPU preference
    # ------------------------------------------------------------------

    async def test_amd_gpu_preference(self):
        cf = self._make_filter()
        req = _request(gpu_brand=GPUBrand.amd)
        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        assert result["gpu"], "Expected at least one AMD GPU"
        for gpu in result["gpu"]:
            model_lower = gpu.model.lower()
            assert any(kw in model_lower for kw in ["radeon", "rx "]), (
                f"Non-AMD GPU present: {gpu.model}"
            )
            assert not any(kw in model_lower for kw in ["geforce", "rtx", "gtx"]), (
                f"NVIDIA GPU leaked: {gpu.model}"
            )

    # ------------------------------------------------------------------
    # h) Max per category cap enforced
    # ------------------------------------------------------------------

    async def test_max_per_category_enforced(self):
        cf = self._make_filter()
        req = _request()
        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        for cat, items in result.items():
            assert len(items) <= _MAX_PER_CATEGORY, (
                f"Category {cat!r} has {len(items)} items — exceeds cap {_MAX_PER_CATEGORY}"
            )

    # ------------------------------------------------------------------
    # i) Existing parts excluded from results
    # ------------------------------------------------------------------

    async def test_existing_parts_excluded_from_results(self):
        cf = self._make_filter()
        req = _request(
            existing_parts=[ComponentCategory.gpu, ComponentCategory.case],
        )
        cats = REQUIRED_CATS - {"gpu", "case"}

        result = await cf.filter_candidates(req, cats, MagicMock())

        assert "gpu" not in result, "GPU should be excluded (existing part)"
        assert "case" not in result, "Case should be excluded (existing part)"
        assert "cpu" in result
        assert "motherboard" in result

    # ------------------------------------------------------------------
    # j) Peripherals pass through unfiltered
    # ------------------------------------------------------------------

    async def test_peripherals_pass_through_unfiltered(self):
        catalog = self._get_catalog()
        cf = self._make_filter(catalog)
        req = _request(include_peripherals=True)
        cats = REQUIRED_CATS | {"monitor", "keyboard", "mouse"}

        result = await cf.filter_candidates(req, cats, MagicMock())

        assert "monitor" in result
        assert "keyboard" in result
        assert "mouse" in result

        # Peripherals are capped at _MAX_PER_CATEGORY, not filtered by hardware rules
        assert len(result["monitor"]) == _MAX_PER_CATEGORY
        assert len(result["keyboard"]) == _MAX_PER_CATEGORY
        assert len(result["mouse"]) == _MAX_PER_CATEGORY

    # ------------------------------------------------------------------
    # k) PSU wattage floor correct
    # ------------------------------------------------------------------

    async def test_psu_wattage_floor_correct(self):
        cf = self._make_filter()
        req = _request(
            cpu_brand=CPUBrand.amd,
            gpu_brand=GPUBrand.nvidia,
            form_factor=FormFactor.atx,
        )
        result = await cf.filter_candidates(req, REQUIRED_CATS, MagicMock())

        cpus = result["cpu"]
        gpus = result["gpu"]

        cpu_tdps = [
            float(c.specs.get("tdp", 0))
            for c in cpus
            if float(c.specs.get("tdp", 0)) > 0
        ]
        gpu_tdps = [
            float(g.specs.get("tdp", 0))
            for g in gpus
            if float(g.specs.get("tdp", 0)) > 0
        ]

        if not cpu_tdps or not gpu_tdps:
            # Can't validate without TDP data — pass
            return

        min_cpu_tdp = min(cpu_tdps)
        min_gpu_tdp = min(gpu_tdps)
        expected_min_wattage = (min_cpu_tdp + min_gpu_tdp + 80) * 1.3

        for psu in result["psu"]:
            w = float(psu.specs.get("wattage", 0))
            assert w >= expected_min_wattage, (
                f"PSU {psu.model} wattage {w}W < expected minimum {expected_min_wattage:.1f}W"
            )


# ---------------------------------------------------------------------------
# Cross-compatibility validation class
# ---------------------------------------------------------------------------


class TestCrossCompatibility:
    """Run the filter across many (CPUBrand × FormFactor × CoolingPreference) combos."""

    # Shared large catalog for all cross-compat tests
    _catalog: dict[str, list[ToolCatalogResult]] | None = None

    @classmethod
    def _get_catalog(cls) -> dict[str, list[ToolCatalogResult]]:
        if cls._catalog is None:
            cls._catalog = _generate_catalog(1000)
        return cls._catalog

    def _make_filter(self) -> CandidateFilter:
        return CandidateFilter(catalog=_mock_catalog_from(self._get_catalog()))

    # ------------------------------------------------------------------
    # a) All combos produce non-empty results for core categories
    # ------------------------------------------------------------------

    async def test_all_scenarios_produce_nonempty_results(self):
        """Every (CPUBrand × FormFactor × CoolingPreference) combo must yield
        at least one candidate for each core category."""
        core_cats = {"cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooling"}
        db = MagicMock()

        for cpu_brand in CPUBrand:
            for form_factor in FormFactor:
                for cooling_pref in CoolingPreference:
                    cf = self._make_filter()
                    req = _request(
                        cpu_brand=cpu_brand,
                        form_factor=form_factor,
                        cooling_preference=cooling_pref,
                    )
                    result = await cf.filter_candidates(req, core_cats, db)
                    for cat in core_cats:
                        assert len(result.get(cat, [])) > 0, (
                            f"No candidates for {cat!r} with "
                            f"cpu_brand={cpu_brand}, form_factor={form_factor}, "
                            f"cooling_pref={cooling_pref}"
                        )

    # ------------------------------------------------------------------
    # b) Mobo sockets match the requested CPU brand's valid sockets
    # ------------------------------------------------------------------

    async def test_mobo_socket_matches_cpu_socket(self):
        """When a CPU brand is specified, all filtered motherboards must
        have a socket that belongs to that brand's valid socket set."""
        db = MagicMock()
        brand_to_sockets = {
            CPUBrand.amd: {"AM5", "AM4"},
            CPUBrand.intel: {"LGA1851", "LGA1700"},
        }

        for cpu_brand, valid_sockets in brand_to_sockets.items():
            cf = self._make_filter()
            req = _request(cpu_brand=cpu_brand)
            result = await cf.filter_candidates(req, REQUIRED_CATS, db)
            for mobo in result["motherboard"]:
                socket = mobo.specs.get("socket", "")
                assert socket in valid_sockets, (
                    f"Mobo socket {socket!r} not in {valid_sockets} "
                    f"for cpu_brand={cpu_brand}"
                )

    # ------------------------------------------------------------------
    # c) RAM DDR type matches mobo DDR types
    # ------------------------------------------------------------------

    async def test_ram_ddr_matches_mobo_ddr(self):
        """After filtering, every RAM item's DDR type must be present among
        the filtered motherboards' DDR types."""
        db = MagicMock()

        # Test for each CPU brand so we have a constrained mobo set
        for cpu_brand in (CPUBrand.amd, CPUBrand.intel, CPUBrand.no_preference):
            cf = self._make_filter()
            req = _request(cpu_brand=cpu_brand)
            result = await cf.filter_candidates(req, REQUIRED_CATS, db)

            mobo_ddr_types = {
                m.specs.get("ddr_type") for m in result["motherboard"]
                if m.specs.get("ddr_type")
            }
            if not mobo_ddr_types:
                continue  # No motherboards — skip

            for ram in result["ram"]:
                ddr = ram.specs.get("ddr_type", "")
                assert ddr in mobo_ddr_types, (
                    f"RAM DDR type {ddr!r} not in mobo DDR types {mobo_ddr_types} "
                    f"for cpu_brand={cpu_brand}"
                )
