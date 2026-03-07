from enum import Enum

from pydantic import BaseModel, Field


class UserGoal(str, Enum):
    high_end_gaming = "high_end_gaming"
    mid_range_gaming = "mid_range_gaming"
    low_end_gaming = "low_end_gaming"
    light_work = "light_work"
    heavy_work = "heavy_work"
    designer = "designer"
    architecture = "architecture"


class BudgetRange(str, Enum):
    range_0_1000 = "0_1000"
    range_1000_1500 = "1000_1500"
    range_1500_2000 = "1500_2000"
    range_2000_3000 = "2000_3000"
    over_3000 = "over_3000"


class FormFactor(str, Enum):
    atx = "atx"
    micro_atx = "micro_atx"
    mini_itx = "mini_itx"


class CPUBrand(str, Enum):
    intel = "intel"
    amd = "amd"
    no_preference = "no_preference"


class GPUBrand(str, Enum):
    nvidia = "nvidia"
    amd = "amd"
    no_preference = "no_preference"


class BuildStatus(str, Enum):
    pending = "pending"
    quoted = "quoted"
    ordered = "ordered"
    cancelled = "cancelled"


class BuildRequestAI(BaseModel):
    """Sent to Claude — high-level preferences, AI figures out the components."""
    goal: UserGoal
    budget_range: BudgetRange
    form_factor: FormFactor = FormFactor.atx
    cpu_brand: CPUBrand = CPUBrand.no_preference
    gpu_brand: GPUBrand = GPUBrand.no_preference
    include_peripherals: bool = Field(
        False, description="Include monitor, keyboard, and mouse"
    )
    existing_parts: list[str] = Field(
        default_factory=list,
        description="Parts the customer already owns e.g. ['GPU', 'Case']",
    )
    notes: str | None = Field(None, max_length=500)


class BuildRequest(BaseModel):
    """Manual build — customer picks specific components by ID."""
    component_ids: list[int] = Field(
        ..., min_length=1, description="IDs of selected components"
    )
    include_peripherals: bool = Field(
        False, description="Include monitor, keyboard, and mouse"
    )
    notes: str | None = Field(None, max_length=500)


class Build(BuildRequest):
    id: int
    status: BuildStatus = BuildStatus.pending
    total_price: float | None = None
