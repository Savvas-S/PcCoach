import json
from enum import Enum
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


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
    completed = "completed"


# Single source of truth: shared/budget_goals.json — synced here via `make sync-config`.
# frontend/src/lib/budget_goals.json and telegram_bot/budget_goals.json are kept in sync
# by the same command. Edit shared/budget_goals.json, then run `make sync-config`.
_budget_goals_path = Path(__file__).parent.parent / "budget_goals.json"
try:
    _VALID_GOALS_FOR_BUDGET: dict[BudgetRange, set[UserGoal]] = {
        BudgetRange(k): {UserGoal(g) for g in v}
        for k, v in json.loads(_budget_goals_path.read_text(encoding="utf-8")).items()
    }
except FileNotFoundError:
    raise RuntimeError(
        f"budget_goals.json not found at {_budget_goals_path}. "
        "Run `make sync-config` to copy it from shared/budget_goals.json."
    ) from None

_ALLOWED_AFFILIATE_HOSTS: frozenset[str] = frozenset({
    "amazon.de",
    "www.amazon.de",
    "computeruniverse.net",
    "www.computeruniverse.net",
    "caseking.de",
    "www.caseking.de",
})


def _validate_affiliate_url(v: HttpUrl | None) -> HttpUrl | None:
    """Ensure affiliate_url points to one of the three allowed stores."""
    if v is None:
        return v
    host = urlparse(str(v)).hostname or ""
    if host not in _ALLOWED_AFFILIATE_HOSTS:
        raise ValueError(f"affiliate_url host '{host}' is not an allowed store")
    return v


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

    @field_validator("existing_parts", mode="after")
    @classmethod
    def deduplicate_existing_parts(cls, v: list[ComponentCategory]) -> list[ComponentCategory]:
        seen: set[ComponentCategory] = set()
        result = []
        for x in v:
            if x not in seen:
                seen.add(x)
                result.append(x)
        return result

    @model_validator(mode="after")
    def validate_goal_for_budget(self) -> "BuildRequest":
        valid = _VALID_GOALS_FOR_BUDGET.get(self.budget_range, set())
        if self.goal not in valid:
            raise ValueError(
                f"Goal '{self.goal.value}' is not available for budget '{self.budget_range.value}'"
            )
        return self


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
    affiliate_source: Literal["computeruniverse", "caseking", "amazon"] | None = None

    @field_validator("affiliate_url", mode="after")
    @classmethod
    def check_affiliate_url(cls, v: HttpUrl | None) -> HttpUrl | None:
        return _validate_affiliate_url(v)


class UpgradeSuggestion(BaseModel):
    """Optional single-component upgrade that meaningfully improves the build."""
    component_category: ComponentCategory
    current_name: str
    upgrade_name: str
    extra_cost_eur: float = Field(..., gt=0)
    reason: str
    affiliate_url: HttpUrl | None = None
    affiliate_source: Literal["computeruniverse", "caseking", "amazon"] | None = None

    @field_validator("affiliate_url", mode="after")
    @classmethod
    def check_affiliate_url(cls, v: HttpUrl | None) -> HttpUrl | None:
        return _validate_affiliate_url(v)


class DowngradeSuggestion(BaseModel):
    """Optional single-component downgrade that saves money while still meeting the use case."""
    component_category: ComponentCategory
    current_name: str
    downgrade_name: str
    savings_eur: float = Field(..., gt=0)
    reason: str
    affiliate_url: HttpUrl | None = None
    affiliate_source: Literal["computeruniverse", "caseking", "amazon"] | None = None

    @field_validator("affiliate_url", mode="after")
    @classmethod
    def check_affiliate_url(cls, v: HttpUrl | None) -> HttpUrl | None:
        return _validate_affiliate_url(v)


class ComponentSearchRequest(BaseModel):
    """User's request to find a specific component."""
    category: ComponentCategory
    description: str = Field(..., min_length=1, max_length=300)


class StoreLink(BaseModel):
    store: Literal["computeruniverse", "caseking", "amazon"]
    url: HttpUrl

    @field_validator("url", mode="after")
    @classmethod
    def check_store_url(cls, v: HttpUrl) -> HttpUrl:
        _validate_affiliate_url(v)  # raises ValueError if host is not an allowed store
        return v


class ComponentSearchResult(BaseModel):
    """AI recommendation for a single component with search links to all stores."""
    name: str
    brand: str
    category: ComponentCategory
    estimated_price_eur: float = Field(..., gt=0)
    reason: str
    specs: dict[str, str] = Field(default_factory=dict)
    store_links: list[StoreLink] = []


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
    status: BuildStatus = BuildStatus.completed
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warnings from output guardrails (e.g. budget overage)",
    )

    @model_validator(mode="after")
    def compute_total_price(self) -> "BuildResult":
        if self.components:
            self.total_price_eur = sum(c.price_eur for c in self.components)
        return self
