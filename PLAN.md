# Agentic Framework Implementation Plan

## Overview

Convert `ClaudeService.generate_build()` from a **single-shot forced tool call** into an **agentic tool loop**. Claude will iteratively search for components, check compatibility, track budget, and finalize only when satisfied.

**Target branch**: `development` (PR from `claude/agentic-framework-evaluation-4KTyz` → `development`)

---

## Current State (on `development`)

- Single Claude API call with `tool_choice={"type": "tool", "name": "recommend_build"}`
- Claude returns the entire build in one pass — no iteration, no validation
- All component knowledge comes from Claude's training data (no real catalog)
- DB caching by request hash already works (PostgreSQL + SQLAlchemy async)
- Input/output guardrails, rate limiting, prompt guard all in place

---

## Step 1: `backend/app/services/budget.py` — Budget Tracker

Pure arithmetic service. No external dependencies.

```python
class BudgetTracker:
    """Track spending against a budget range."""

    def check(budget_range: BudgetRange, components: list[dict]) -> BudgetStatus
```

**Returns** `BudgetStatus`:
- `budget_min_eur`, `budget_max_eur` — parsed from `BudgetRange` enum
- `total_spent_eur` — sum of selected component prices
- `remaining_eur` — `budget_max - total_spent`
- `per_component` — breakdown: `[{category, name, price_eur}]`
- `over_budget` — bool
- `utilization_pct` — percentage of budget used

**Budget range parsing** (from enum values):
- `"0_1000"` → min=0, max=1000
- `"1000_1500"` → min=1000, max=1500
- `"over_3000"` → min=3000, max=5000 (soft cap)

**Tool schema** for Claude:
```json
{
  "name": "get_remaining_budget",
  "description": "Calculate remaining budget given selected components",
  "input_schema": {
    "properties": {
      "selected_components": [{
        "category": "string",
        "name": "string",
        "price_eur": "number"
      }]
    }
  }
}
```

The `budget_range` is injected server-side from the original `BuildRequest` — Claude doesn't pass it.

---

## Step 2: `backend/app/services/compatibility.py` — Compatibility Checker

Rule-based engine. No external APIs. Uses the same rules already in `compatibility.yaml` but enforced programmatically.

```python
class CompatibilityChecker:
    def check(components: list[dict]) -> CompatibilityReport
```

**Returns** `CompatibilityReport`:
- `compatible` — bool (all checks pass)
- `checks` — list of `CompatCheck`:
  - `pair` — e.g. `"CPU ↔ Motherboard"`
  - `status` — `"pass"` | `"fail"` | `"warning"`
  - `reason` — human-readable explanation

**Rules implemented** (matching existing `compatibility.yaml`):

| Check | Logic |
|-------|-------|
| CPU ↔ Motherboard socket | Extract socket from specs (e.g. `"AM5"`, `"LGA1700"`), must match |
| RAM ↔ Motherboard | DDR generation must match (`"DDR4"` vs `"DDR5"`) |
| Case ↔ Motherboard form factor | ATX case fits all; mATX fits mATX+mITX; mITX fits mITX only |
| PSU wattage | CPU TDP + GPU TDP + 80W baseline, require PSU ≥ 130% of that |
| Case ↔ GPU clearance | Compare `max_gpu_length_mm` spec vs GPU `length_mm` spec (if available) |
| Case ↔ Cooler clearance | Compare `max_cooler_height_mm` vs cooler `height_mm` (if available) |

Claude must include relevant specs (socket, ddr_type, tdp, form_factor) in component specs for checks to work. The system prompt will instruct this.

**Tool schema** for Claude:
```json
{
  "name": "check_compatibility",
  "description": "Validate that selected components are compatible with each other",
  "input_schema": {
    "properties": {
      "components": [{
        "category": "string",
        "name": "string",
        "specs": {"socket": "AM5", "ddr_type": "DDR5", "tdp": "105", ...}
      }]
    }
  }
}
```

---

## Step 3: `backend/app/services/catalog.py` — Catalog Search

This is the most complex piece. Starting with **search URL generation** (same approach as the current `SEARCH_TOOL`) — not live scraping.

```python
class CatalogService:
    async def search(category: str, query: str, max_results: int = 5) -> list[CatalogResult]
```

**Phase 1 (this PR)**: Claude uses its own knowledge to identify products, but calls `search_catalog` to get properly formatted store search URLs and estimated pricing guidance. The tool:
- Takes `category` + `query` (e.g. `"cpu"`, `"AMD Ryzen 7 7800X3D"`)
- Returns search URLs for all 3 stores (using existing URL patterns from `stores.yaml`)
- Returns the category constraints (what specs are needed for compatibility checks)

This keeps the current behavior (Claude picks components from training data) but structures it into an iterative flow where each pick is validated.

**Phase 2 (future)**: Replace with real catalog data (web scraping, API, or curated JSON).

**Tool schema** for Claude:
```json
{
  "name": "search_catalog",
  "description": "Search for PC components and get store links. Call this for each component you want to add to the build.",
  "input_schema": {
    "properties": {
      "category": {"type": "string", "enum": ["cpu", "gpu", "motherboard", ...]},
      "query": {"type": "string", "description": "Product name or search terms"},
      "price_eur": {"type": "number", "description": "Your estimated price for this component"}
    }
  }
}
```

**Returns**: store search URLs, the category, formatted specs template (what specs Claude should provide for compatibility).

---

## Step 4: Update Tool Definitions in `claude.py`

Replace `BUILD_TOOL` with 4 tools:

| Tool | Purpose | When Claude calls it |
|------|---------|---------------------|
| `search_catalog` | Find a component + get store URLs | Once per component category |
| `check_compatibility` | Validate current selections | After adding 2+ components |
| `get_remaining_budget` | Check spending vs budget | After each component or periodically |
| `finalize_build` | Submit the final build | Once, when done |

`finalize_build` has the same schema as the current `BUILD_TOOL` — this is the terminal tool call.

**Key change**: Remove `tool_choice={"type": "tool", "name": "recommend_build"}`. Instead, let Claude choose freely from all 4 tools.

---

## Step 5: Implement the Agentic Loop in `ClaudeService.generate_build()`

Replace the single API call with a loop:

```python
async def generate_build(self, request, build_id, client_ip):
    messages = [{"role": "user", "content": user_message}]
    tools = [SEARCH_CATALOG_TOOL, CHECK_COMPAT_TOOL, GET_BUDGET_TOOL, FINALIZE_BUILD_TOOL]

    for iteration in range(MAX_ITERATIONS):  # cap at 20
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=[...],
            tools=tools,
            messages=messages,
        )

        # Check stop reason
        if response.stop_reason == "end_turn":
            raise ValueError("Claude ended without calling finalize_build")

        if response.stop_reason == "tool_use":
            tool_calls = [b for b in response.content if b.type == "tool_use"]

            # Add assistant message to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Process each tool call
            tool_results = []
            for tool_call in tool_calls:
                if tool_call.name == "finalize_build":
                    # Terminal — extract BuildResult and return
                    return self._build_result_from_tool(tool_call, build_id, request, client_ip)

                result = await self._execute_tool(tool_call, request)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result),
                })

            messages.append({"role": "user", "content": tool_results})

    raise ValueError("Max iterations reached without finalizing build")
```

**`_execute_tool()` dispatcher**:
- `"search_catalog"` → `CatalogService.search()`
- `"check_compatibility"` → `CompatibilityChecker.check()`
- `"get_remaining_budget"` → `BudgetTracker.check()` (injects `budget_range` from request)

**Timeout**: Increase `_TIMEOUT` from 90s to 120s per individual API call. Add an overall wall-clock timeout of 180s for the entire loop.

---

## Step 6: Update System Prompt

Add a new YAML section `backend/app/prompts/sections/agentic_workflow.yaml`:

```yaml
title: Agentic Workflow
content: |
  ## How to Build a PC Recommendation

  You have 4 tools. Use them iteratively to construct a complete, compatible,
  within-budget build:

  ### Workflow
  1. Start by deciding which components are needed (exclude existing_parts)
  2. For each component category:
     a. Call search_catalog with the product you want to recommend
     b. Call get_remaining_budget to check spending
  3. After selecting 2+ components, call check_compatibility to validate
  4. If compatibility fails, search for a replacement and re-check
  5. When all components are selected, compatible, and within budget:
     call finalize_build with the complete build

  ### Important
  - Always include these specs for compatibility checking:
    - CPU: socket, tdp
    - Motherboard: socket, ddr_type, form_factor
    - RAM: ddr_type, capacity_gb
    - GPU: tdp, length_mm (if known)
    - PSU: wattage
    - Case: form_factor, max_gpu_length_mm, max_cooler_height_mm
    - Cooler: height_mm (air) or radiator_size_mm (liquid)
  - Do NOT call finalize_build until you have verified compatibility
  - Stay within the budget range
```

Update `prompts/manager.py` to include this new section in the build prompt.

---

## Step 7: Tests

### Unit tests (`backend/tests/`)

1. **`test_budget.py`** — BudgetTracker with various budget ranges and component lists
2. **`test_compatibility.py`** — All compatibility rules (pass/fail cases for each check)
3. **`test_catalog.py`** — CatalogService URL generation and response format
4. **`test_agentic_loop.py`** — Mock Claude responses simulating multi-turn tool calls:
   - Happy path: search → budget → compat → finalize
   - Max iterations hit
   - Compatibility failure → retry with different component
   - Budget exceeded → swap for cheaper component

---

## What Stays Unchanged

- `BuildRequest` / `BuildResult` Pydantic models (API contract preserved)
- `POST /api/v1/build` endpoint signature and error handling
- Input guardrails, output guardrails, prompt guard
- DB caching (request hash → cached result)
- Rate limiting
- Frontend — no changes needed
- `search_component()` method and `/api/v1/search` endpoint (separate flow)

---

## File Changes Summary

| File | Action |
|------|--------|
| `backend/app/services/budget.py` | **New** — BudgetTracker |
| `backend/app/services/compatibility.py` | **New** — CompatibilityChecker |
| `backend/app/services/catalog.py` | **New** — CatalogService |
| `backend/app/services/claude.py` | **Modify** — new tool defs, agentic loop |
| `backend/app/prompts/sections/agentic_workflow.yaml` | **New** — workflow instructions |
| `backend/app/prompts/manager.py` | **Modify** — include new section |
| `backend/tests/test_budget.py` | **New** |
| `backend/tests/test_compatibility.py` | **New** |
| `backend/tests/test_catalog.py` | **New** |
| `backend/tests/test_agentic_loop.py` | **New** |

---

## Open Decisions

1. **Max iterations**: 20 seems safe. Too low = incomplete builds. Too high = cost/latency.
2. **Overall timeout**: 180s for the full loop (vs 90s current single call). Acceptable?
3. **Catalog Phase 1**: Search URL generation only (no real product data). OK for now?
