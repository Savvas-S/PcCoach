"""Engine-internal compatibility validation (defense-in-depth).

Families guarantee socket/DDR compatibility by construction, but this
module provides an extra check after selection. It catches edge cases
that family grouping might miss (e.g., PSU wattage, GPU length).
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.models.types import ProductRecord


@dataclass
class ValidationIssue:
    """A compatibility problem found during validation."""

    category: str
    message: str
    severity: str = "error"  # "error" or "warning"


def validate_build(
    selections: dict[str, ProductRecord],
) -> list[ValidationIssue]:
    """Validate compatibility of selected components.

    Returns a list of issues (empty = all good). Errors should block
    the build; warnings are informational.
    """
    issues: list[ValidationIssue] = []

    cpu = selections.get("cpu")
    mobo = selections.get("motherboard")
    ram = selections.get("ram")
    psu = selections.get("psu")
    gpu = selections.get("gpu")
    case = selections.get("case")

    # Socket match
    if cpu and mobo:
        cpu_socket = cpu.specs.get("socket", "")
        mobo_socket = mobo.specs.get("socket", "")
        if cpu_socket and mobo_socket and cpu_socket != mobo_socket:
            issues.append(ValidationIssue(
                "cpu",
                f"CPU socket {cpu_socket} != motherboard socket {mobo_socket}",
            ))

    # DDR match
    if ram and mobo:
        ram_ddr = ram.specs.get("ddr_type", "")
        mobo_ddr = mobo.specs.get("ddr_type", "")
        if ram_ddr and mobo_ddr and ram_ddr != mobo_ddr:
            issues.append(ValidationIssue(
                "ram",
                f"RAM {ram_ddr} != motherboard {mobo_ddr}",
            ))

    # PSU wattage
    if psu and cpu and gpu:
        psu_w = _safe_int(psu.specs.get("wattage", "0"))
        cpu_tdp = _safe_int(cpu.specs.get("tdp", "0"))
        gpu_tdp = _safe_int(gpu.specs.get("tdp", "0"))
        min_psu = int((cpu_tdp + gpu_tdp + 80) * 1.3)
        if psu_w < min_psu:
            issues.append(ValidationIssue(
                "psu",
                f"PSU {psu_w}W may be insufficient "
                f"(recommended ≥{min_psu}W for CPU {cpu_tdp}W + GPU {gpu_tdp}W)",
                severity="warning",
            ))

    # GPU length vs case (if data available)
    if gpu and case:
        gpu_len = _safe_int(gpu.specs.get("length_mm", "0"))
        case_max = _safe_int(case.specs.get("max_gpu_length", "0"))
        if gpu_len > 0 and case_max > 0 and gpu_len > case_max:
            issues.append(ValidationIssue(
                "gpu",
                f"GPU length {gpu_len}mm exceeds case max {case_max}mm",
            ))

    # Form factor
    if mobo and case:
        mobo_ff = mobo.specs.get("form_factor", "").lower()
        case_ff = case.specs.get("form_factor", "").lower()
        if mobo_ff and case_ff:
            ff_rank = {"atx": 3, "micro_atx": 2, "micro-atx": 2,
                       "mini_itx": 1, "mini-itx": 1}
            mobo_r = ff_rank.get(mobo_ff, 3)
            case_r = ff_rank.get(case_ff, 3)
            if mobo_r > case_r:
                issues.append(ValidationIssue(
                    "motherboard",
                    f"Motherboard {mobo_ff} too large for case {case_ff}",
                ))

    return issues


def _safe_int(value: str) -> int:
    """Safely convert a string to int."""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0
