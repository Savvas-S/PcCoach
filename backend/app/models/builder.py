from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, model_validator


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


class CoolingPreference(str, Enum):
    no_preference = "no_preference"
    liquid = "liquid"
    air = "air"


class ComponentCategory(str, Enum):
    cpu = "cpu"
    gpu = "gpu"
    motherboard = "motherboard"
    ram = "ram"
    storage = "storage"
    psu = "psu"
    case = "case"
    cooling = "cooling"
    monitor = "monitor"
    keyboard = "keyboard"
    mouse = "mouse"


class BuildStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class BuildRequest(BaseModel):
    """User's requirements — passed to Claude to generate a build recommendation."""
    goal: UserGoal
    budget_range: BudgetRange
    form_factor: FormFactor = FormFactor.atx
    cpu_brand: CPUBrand = CPUBrand.no_preference
    gpu_brand: GPUBrand = GPUBrand.no_preference
    cooling_preference: CoolingPreference = CoolingPreference.no_preference
    include_peripherals: bool = Field(
        False, description="Include monitor, keyboard, and mouse"
    )
    existing_parts: list[ComponentCategory] = Field(
        default_factory=list,
        description="Categories the customer already owns and wants to exclude",
    )
    notes: str | None = Field(None, max_length=500)


class ComponentRecommendation(BaseModel):
    """A single recommended component with affiliate link."""
    category: ComponentCategory
    name: str
    brand: str
    price_eur: float = Field(..., gt=0)
    specs: dict[str, str] = Field(
        default_factory=dict,
        description="Key specs e.g. {'cores': '8', 'tdp': '65W'}",
    )
    affiliate_url: HttpUrl | None = None
    affiliate_source: str | None = Field(
        None, description="e.g. 'amazon', 'computeruniverse', 'caseking'"
    )


class UpgradeSuggestion(BaseModel):
    """Optional single-component upgrade that meaningfully improves the build."""
    component_category: ComponentCategory
    current_name: str
    upgrade_name: str
    extra_cost_eur: float = Field(..., gt=0)
    reason: str
    affiliate_url: HttpUrl | None = None
    affiliate_source: str | None = Field(
        None, description="e.g. 'amazon', 'computeruniverse', 'caseking'"
    )


class DowngradeSuggestion(BaseModel):
    """Optional single-component downgrade that saves money while still meeting the use case."""
    component_category: ComponentCategory
    current_name: str
    downgrade_name: str
    savings_eur: float = Field(..., gt=0)
    reason: str
    affiliate_url: HttpUrl | None = None
    affiliate_source: str | None = Field(
        None, description="e.g. 'amazon', 'computeruniverse', 'caseking'"
    )


class BuildResult(BaseModel):
    """The full build recommendation returned to the user."""
    id: str
    components: list[ComponentRecommendation] = []
    total_price_eur: float | None = None
    summary: str | None = Field(
        None, description="Claude's explanation of the build choices"
    )
    upgrade_suggestion: UpgradeSuggestion | None = None
    downgrade_suggestion: DowngradeSuggestion | None = None
    status: BuildStatus = BuildStatus.pending

    @model_validator(mode="after")
    def compute_total_price(self) -> "BuildResult":
        if self.components:
            self.total_price_eur = sum(c.price_eur for c in self.components)
        return self
