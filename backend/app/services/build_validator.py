"""Server-side compatibility validation for PC builds.

Checks hard constraints (socket, DDR, form factor, PSU, GPU length, cooler socket)
and returns structured errors that Claude can use to repair invalid builds.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResolvedComponent:
    id: int
    category: str
    brand: str
    model: str
    specs: dict[str, str]
    price_eur: float
    affiliate_url: str
    affiliate_source: str


@dataclass(frozen=True)
class ValidationError:
    category: str
    rule: str
    message: str


@dataclass(frozen=True)
class ValidationWarning:
    rule: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationWarning] = field(default_factory=list)


class BuildValidationError(ValueError):
    """Raised when a build fails validation after the repair attempt."""

    def __init__(self, errors: list[ValidationError]):
        self.errors = errors
        msg = "; ".join(e.message for e in errors)
        super().__init__(f"Build validation failed: {msg}")


# Core categories required in every build (unless excluded)
_CORE_CATEGORIES = frozenset(
    {"cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooling"}
)

_PERIPHERAL_CATEGORIES = frozenset({"monitor", "keyboard", "mouse"})

# Form factor size hierarchy: larger rank fits smaller boards
_FF_RANK: dict[str, int] = {
    "ATX": 3,
    "atx": 3,
    "micro_atx": 2,
    "Micro-ATX": 2,
    "mini_itx": 1,
    "Mini-ITX": 1,
}


class BuildValidator:
    """Validates component compatibility for a submitted build."""

    def validate(
        self,
        components: dict[str, ResolvedComponent],
        required_categories: set[str],
    ) -> ValidationResult:
        """Run all compatibility checks.

        Args:
            components: dict keyed by category -> ResolvedComponent.
            required_categories: categories that must be present.
        """
        errors: list[ValidationError] = []
        warnings: list[ValidationWarning] = []

        # Missing categories
        errors.extend(self._check_missing_categories(components, required_categories))

        # Socket match: CPU <-> motherboard
        errors.extend(self._check_socket(components))

        # DDR match: RAM <-> motherboard
        errors.extend(self._check_ddr(components))

        # Form factor: motherboard must fit case
        errors.extend(self._check_form_factor(components))

        # GPU length vs case clearance
        errors.extend(self._check_gpu_length(components))

        # Cooler socket support
        errors.extend(self._check_cooler_socket(components))

        # PSU wattage
        psu_errors, psu_warnings = self._check_psu(components)
        errors.extend(psu_errors)
        warnings.extend(psu_warnings)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _check_missing_categories(
        self,
        components: dict[str, ResolvedComponent],
        required: set[str],
    ) -> list[ValidationError]:
        errors = []
        present = set(components.keys())
        for cat in sorted(required - present):
            errors.append(
                ValidationError(
                    category=cat,
                    rule="missing_category",
                    message=f"Required category '{cat}' is missing from the build",
                )
            )
        return errors

    def _check_socket(
        self, components: dict[str, ResolvedComponent]
    ) -> list[ValidationError]:
        cpu = components.get("cpu")
        mobo = components.get("motherboard")
        if not cpu or not mobo:
            return []
        cpu_socket = cpu.specs.get("socket")
        mobo_socket = mobo.specs.get("socket")
        if not cpu_socket or not mobo_socket:
            return []
        if cpu_socket != mobo_socket:
            return [
                ValidationError(
                    category="motherboard",
                    rule="socket_mismatch",
                    message=(
                        f"CPU socket {cpu_socket} != "
                        f"motherboard socket {mobo_socket}"
                    ),
                )
            ]
        return []

    def _check_ddr(
        self, components: dict[str, ResolvedComponent]
    ) -> list[ValidationError]:
        ram = components.get("ram")
        mobo = components.get("motherboard")
        if not ram or not mobo:
            return []
        ram_ddr = ram.specs.get("ddr_type")
        mobo_ddr = mobo.specs.get("ddr_type")
        if not ram_ddr or not mobo_ddr:
            return []
        if ram_ddr != mobo_ddr:
            return [
                ValidationError(
                    category="ram",
                    rule="ddr_mismatch",
                    message=(
                        f"Motherboard DDR type {mobo_ddr} != "
                        f"RAM DDR type {ram_ddr}"
                    ),
                )
            ]
        return []

    def _check_form_factor(
        self, components: dict[str, ResolvedComponent]
    ) -> list[ValidationError]:
        mobo = components.get("motherboard")
        case = components.get("case")
        if not mobo or not case:
            return []
        mobo_ff = mobo.specs.get("form_factor")
        case_ff = case.specs.get("form_factor")
        if not mobo_ff or not case_ff:
            return []
        mobo_rank = _FF_RANK.get(mobo_ff)
        case_rank = _FF_RANK.get(case_ff)
        if mobo_rank is None or case_rank is None:
            return []
        if mobo_rank > case_rank:
            return [
                ValidationError(
                    category="case",
                    rule="form_factor_mismatch",
                    message=(
                        f"Motherboard form factor {mobo_ff} does not fit "
                        f"case form factor {case_ff}"
                    ),
                )
            ]
        return []

    def _check_gpu_length(
        self, components: dict[str, ResolvedComponent]
    ) -> list[ValidationError]:
        gpu = components.get("gpu")
        case = components.get("case")
        if not gpu or not case:
            return []
        gpu_len = gpu.specs.get("length_mm")
        case_max = case.specs.get("max_gpu_length")
        if not gpu_len or not case_max:
            return []
        try:
            gpu_len_f = float(gpu_len)
            case_max_f = float(case_max)
        except (ValueError, TypeError):
            return []
        if gpu_len_f > case_max_f:
            return [
                ValidationError(
                    category="gpu",
                    rule="gpu_too_long",
                    message=(
                        f"GPU length {gpu_len}mm exceeds "
                        f"case max GPU length {case_max}mm"
                    ),
                )
            ]
        return []

    def _check_cooler_socket(
        self, components: dict[str, ResolvedComponent]
    ) -> list[ValidationError]:
        cpu = components.get("cpu")
        cooling = components.get("cooling")
        if not cpu or not cooling:
            return []
        cpu_socket = cpu.specs.get("socket")
        socket_support = cooling.specs.get("socket_support")
        if not cpu_socket or not socket_support:
            return []
        # socket_support can be comma-separated: "AM5,AM4,LGA1700"
        supported = [s.strip() for s in socket_support.split(",")]
        if cpu_socket not in supported:
            return [
                ValidationError(
                    category="cooling",
                    rule="cooler_socket_mismatch",
                    message=(
                        f"Cooler does not support CPU socket {cpu_socket} "
                        f"(supports: {socket_support})"
                    ),
                )
            ]
        return []

    def _check_psu(
        self, components: dict[str, ResolvedComponent]
    ) -> tuple[list[ValidationError], list[ValidationWarning]]:
        psu = components.get("psu")
        cpu = components.get("cpu")
        gpu = components.get("gpu")
        if not psu:
            return [], []
        psu_wattage_str = psu.specs.get("wattage")
        if not psu_wattage_str:
            return [], []
        try:
            psu_wattage = float(psu_wattage_str)
        except (ValueError, TypeError):
            return [], []

        # Estimate system TDP
        cpu_tdp = _safe_float(cpu.specs.get("tdp")) if cpu else 0.0
        gpu_tdp = _safe_float(gpu.specs.get("tdp")) if gpu else 0.0
        if cpu_tdp == 0.0 and gpu_tdp == 0.0:
            return [], []

        estimated_need = (cpu_tdp + gpu_tdp + 80) * 1.3

        if psu_wattage < estimated_need:
            return [
                ValidationError(
                    category="psu",
                    rule="psu_underpowered",
                    message=(
                        f"PSU {psu_wattage:.0f}W is insufficient. "
                        f"Estimated need: {estimated_need:.0f}W "
                        f"(CPU {cpu_tdp:.0f}W + GPU {gpu_tdp:.0f}W + 80W baseline, "
                        f"x1.3 headroom)"
                    ),
                )
            ], []

        # Tight margin warning: within 10% of estimated need
        if psu_wattage < estimated_need * 1.1:
            return [], [
                ValidationWarning(
                    rule="psu_tight",
                    message=(
                        f"PSU {psu_wattage:.0f}W is tight. "
                        f"Estimated need: {estimated_need:.0f}W"
                    ),
                )
            ]

        return [], []


def format_repair_error(errors: list[ValidationError]) -> str:
    """Format validation errors as compact text for Claude's repair pass."""
    lines = [
        "VALIDATION_FAILED: Your build has compatibility errors. "
        "Fix and resubmit."
    ]
    for e in errors:
        lines.append(f"- [{e.rule}] {e.message}")
    lines.append(
        "Query the catalog for compatible alternatives, "
        "then call submit_build with corrected component_ids."
    )
    return "\n".join(lines)


def required_categories(
    existing_parts: list[str],
    include_peripherals: bool,
) -> set[str]:
    """Compute which categories must be present in a build submission."""
    excluded = set(existing_parts)
    cats = {c for c in _CORE_CATEGORIES if c not in excluded}
    if include_peripherals:
        cats.update(c for c in _PERIPHERAL_CATEGORIES if c not in excluded)
    return cats


def _safe_float(val: str | None) -> float:
    """Parse a string to float, returning 0.0 on failure."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
