"""Pure unit tests for BuildValidator — no DB, no mocks."""

from app.services.build_validator import (
    BuildValidator,
    ResolvedComponent,
    ValidationError,
    format_repair_error,
    required_categories,
)


def _comp(category, specs=None, **kwargs):
    defaults = {
        "id": 1,
        "category": category,
        "brand": "TestBrand",
        "model": "TestModel",
        "specs": specs or {},
        "price_eur": 100.0,
        "affiliate_url": "https://www.amazon.de/dp/TEST?tag=thepccoach-21",
        "affiliate_source": "amazon",
    }
    defaults.update(kwargs)
    return ResolvedComponent(**defaults)


_REQUIRED_CORE = {"cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooling"}
validator = BuildValidator()


class TestSocketCheck:
    def test_cpu_am5_mobo_lga1700_fails(self):
        components = {
            "cpu": _comp("cpu", {"socket": "AM5"}),
            "motherboard": _comp("motherboard", {"socket": "LGA1700"}),
        }
        result = validator.validate(components, set())
        assert not result.valid
        rules = [e.rule for e in result.errors]
        assert "socket_mismatch" in rules

    def test_cpu_am5_mobo_am5_passes(self):
        components = {
            "cpu": _comp("cpu", {"socket": "AM5"}),
            "motherboard": _comp("motherboard", {"socket": "AM5"}),
        }
        result = validator.validate(components, set())
        assert result.valid


class TestDDRCheck:
    def test_ddr4_ram_ddr5_mobo_fails(self):
        components = {
            "ram": _comp("ram", {"ddr_type": "DDR4"}),
            "motherboard": _comp("motherboard", {"ddr_type": "DDR5"}),
        }
        result = validator.validate(components, set())
        assert not result.valid
        rules = [e.rule for e in result.errors]
        assert "ddr_mismatch" in rules

    def test_ddr5_ram_ddr5_mobo_passes(self):
        components = {
            "ram": _comp("ram", {"ddr_type": "DDR5"}),
            "motherboard": _comp("motherboard", {"ddr_type": "DDR5"}),
        }
        result = validator.validate(components, set())
        assert result.valid


class TestFormFactorCheck:
    def test_atx_mobo_in_mini_itx_case_fails(self):
        components = {
            "motherboard": _comp("motherboard", {"form_factor": "ATX"}),
            "case": _comp("case", {"form_factor": "mini_itx"}),
        }
        result = validator.validate(components, set())
        assert not result.valid
        rules = [e.rule for e in result.errors]
        assert "form_factor_mismatch" in rules

    def test_micro_atx_mobo_in_atx_case_passes(self):
        components = {
            "motherboard": _comp("motherboard", {"form_factor": "micro_atx"}),
            "case": _comp("case", {"form_factor": "ATX"}),
        }
        result = validator.validate(components, set())
        assert result.valid


class TestGPULength:
    def test_gpu_too_long_for_case_fails(self):
        components = {
            "gpu": _comp("gpu", {"length_mm": "360"}),
            "case": _comp("case", {"max_gpu_length": "330"}),
        }
        result = validator.validate(components, set())
        assert not result.valid
        rules = [e.rule for e in result.errors]
        assert "gpu_too_long" in rules

    def test_gpu_fits_case_passes(self):
        components = {
            "gpu": _comp("gpu", {"length_mm": "300"}),
            "case": _comp("case", {"max_gpu_length": "330"}),
        }
        result = validator.validate(components, set())
        assert result.valid


class TestPSU:
    def test_psu_underpowered_fails(self):
        # CPU 125W + GPU 250W + 80W = 455W * 1.3 = 591.5W needed
        components = {
            "cpu": _comp("cpu", {"tdp": "125"}),
            "gpu": _comp("gpu", {"tdp": "250"}),
            "psu": _comp("psu", {"wattage": "500"}),
        }
        result = validator.validate(components, set())
        assert not result.valid
        rules = [e.rule for e in result.errors]
        assert "psu_underpowered" in rules

    def test_psu_adequate_passes(self):
        # CPU 125W + GPU 250W + 80W = 455W * 1.3 = 591.5W needed
        components = {
            "cpu": _comp("cpu", {"tdp": "125"}),
            "gpu": _comp("gpu", {"tdp": "250"}),
            "psu": _comp("psu", {"wattage": "750"}),
        }
        result = validator.validate(components, set())
        assert result.valid
        assert len(result.warnings) == 0

    def test_psu_tight_warns(self):
        # CPU 65W + GPU 150W + 80W = 295W * 1.3 = 383.5W needed
        # 400W is sufficient but within 10% (383.5 * 1.1 = 421.85)
        components = {
            "cpu": _comp("cpu", {"tdp": "65"}),
            "gpu": _comp("gpu", {"tdp": "150"}),
            "psu": _comp("psu", {"wattage": "400"}),
        }
        result = validator.validate(components, set())
        assert result.valid
        rules = [w.rule for w in result.warnings]
        assert "psu_tight" in rules


class TestMissingCategories:
    def test_missing_cpu_fails(self):
        components = {
            "gpu": _comp("gpu"),
        }
        result = validator.validate(components, {"cpu", "gpu"})
        assert not result.valid
        rules = [e.rule for e in result.errors]
        assert "missing_category" in rules
        cats = [e.category for e in result.errors if e.rule == "missing_category"]
        assert "cpu" in cats

    def test_all_present_passes(self):
        components = {
            "cpu": _comp("cpu"),
            "gpu": _comp("gpu"),
        }
        result = validator.validate(components, {"cpu", "gpu"})
        missing = [e for e in result.errors if e.rule == "missing_category"]
        assert len(missing) == 0

    def test_excluded_category_not_required(self):
        cats = required_categories(
            existing_parts=["cpu"],
            include_peripherals=False,
        )
        assert "cpu" not in cats
        assert "gpu" in cats


class TestMissingSpecs:
    def test_missing_specs_passes(self):
        """Can't validate without data — no false positives."""
        components = {
            "cpu": _comp("cpu", {}),
            "motherboard": _comp("motherboard", {}),
            "ram": _comp("ram", {}),
            "case": _comp("case", {}),
            "gpu": _comp("gpu", {}),
            "psu": _comp("psu", {}),
            "cooling": _comp("cooling", {}),
            "storage": _comp("storage", {}),
        }
        result = validator.validate(components, _REQUIRED_CORE)
        assert result.valid


class TestFormatRepairError:
    def test_format_repair_error_includes_all_rules(self):
        errors = [
            ValidationError("motherboard", "socket_mismatch", "CPU AM5 != mobo LGA1700"),
            ValidationError("ram", "ddr_mismatch", "Mobo DDR5 != RAM DDR4"),
        ]
        text = format_repair_error(errors)
        assert "VALIDATION_FAILED" in text
        assert "[socket_mismatch]" in text
        assert "[ddr_mismatch]" in text
        assert "CPU AM5 != mobo LGA1700" in text
        assert "Mobo DDR5 != RAM DDR4" in text
        assert "submit_build" in text


class TestCoolerSocket:
    def test_cooler_supports_cpu_socket_passes(self):
        components = {
            "cpu": _comp("cpu", {"socket": "AM5"}),
            "cooling": _comp("cooling", {"socket_support": "AM5,AM4,LGA1700"}),
        }
        result = validator.validate(components, set())
        assert result.valid

    def test_cooler_does_not_support_cpu_socket_fails(self):
        components = {
            "cpu": _comp("cpu", {"socket": "LGA1851"}),
            "cooling": _comp("cooling", {"socket_support": "AM5,AM4,LGA1700"}),
        }
        result = validator.validate(components, set())
        assert not result.valid
        rules = [e.rule for e in result.errors]
        assert "cooler_socket_mismatch" in rules
