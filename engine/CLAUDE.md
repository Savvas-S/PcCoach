# PcCoach Build Engine — Claude Code Guide

## Overview

The build engine is a **self-contained deterministic library** that selects optimal PC components for a given goal and budget. It has **zero dependencies on the backend** (no FastAPI, no SQLAlchemy, no Anthropic SDK). Only stdlib + pyyaml.

## Architecture

```
engine/
├── __init__.py          # Public API: select_build(), BuildEngineResult
├── ports.py             # CatalogPort Protocol (abstract data access)
├── models/
│   ├── types.py         # ProductRecord, ListingRecord, CompatibilityFamily, etc.
│   └── result.py        # BuildEngineResult, SelectedComponent
├── config/
│   ├── profiles.yaml    # 7 goal profiles (budget splits, spec weights)
│   ├── hardware_tiers.yaml  # GPU/CPU/chipset tier rankings
│   └── loader.py        # YAML loading + validation + caching
├── core/
│   ├── dedup.py         # Product deduplication across shops
│   ├── families.py      # Compatibility family computation
│   ├── scorer.py        # Product scoring (spec, price, tier)
│   ├── selector.py      # Greedy selection + budget balancing
│   ├── optimizer.py     # Post-selection budget optimization
│   ├── validator.py     # Engine-internal compatibility check
│   └── notes_parser.py  # Regex extraction from user notes
└── tests/
```

## Dependency Rules (strict)

```
backend  →  engine     ✅  Backend imports engine and calls select_build()
engine   →  backend    ❌  Engine NEVER imports from backend.app.*
engine   →  DB models  ❌  Engine defines its own types via ports + dataclasses
```

## Public API

```python
from engine import select_build, BuildEngineResult

result: BuildEngineResult = await select_build(
    goal="high_end_gaming",
    budget_range="2000_3000",
    form_factor="atx",
    cpu_brand="no_preference",
    gpu_brand="no_preference",
    cooling_preference="no_preference",
    existing_parts=[],
    notes=None,
    catalog=my_catalog_port_impl,
)
```

## Selection Algorithm

1. Load profile for goal from `profiles.yaml`
2. Compute budget target = `budget_max × 0.85`
3. Fetch & deduplicate products via CatalogPort
4. Compute compatibility families (socket × DDR grouping)
5. Select best feasible family
6. Compute per-category budgets from profile allocation
7. Score candidates: `spec_score × 0.45 + price_score × 0.30 + tier_score × 0.25`
8. Greedy selection in profile priority order with budget tracking
9. Optimize: upgrade if headroom, downgrade if over budget
10. Identify upgrade/downgrade candidates, validate, resolve best listings

## Config Files (primary tuning knobs)

- `config/profiles.yaml` — Budget allocations, selection order, spec weights, tier guidance per goal
- `config/hardware_tiers.yaml` — GPU/CPU/chipset performance rankings

When new hardware launches or meta shifts, update these YAML files — no code changes needed.

## Running Tests

```bash
cd engine && python -m pytest tests/ -v
```

Tests use a `MockCatalogAdapter` with hardcoded product data — no database, no network.
