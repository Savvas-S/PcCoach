# Agentic Framework Implementation Plan

## Overview

Replace the current single-shot Claude call with a **catalog-driven architecture**:
- **DB is the catalog** — real components, real prices, real affiliate links
- **Claude is the brain** — picks the optimal combination from pre-filtered candidates
- **No hallucinated products** — Claude only sees what's actually in stock

**Target branch**: `development` (PR from `claude/agentic-framework-evaluation-4KTyz` → `development`)

---

## Architecture

```
User fills form → POST /api/v1/build (BuildRequest)
               → Input guardrails (blocklist, duplicate, budget sanity)
               → Builder service:
                   1. Parse request (goal, budget, preferences)
                   2. Query DB → candidate components per category
                      (filtered by: in_stock, brand pref, form_factor)
                      (joined with cheapest affiliate_link per component)
                   3. Build Claude prompt with candidate list as structured data
                   4. Claude picks optimal combination (budget + compat + priorities)
               → Output guardrails
               → Persist build → Return BuildResult
```

**Key insight**: Hard constraints (stock, brand, form factor) are filtered by SQL.
Soft optimization (budget allocation, compatibility, value ranking) is Claude's job.

---

## Current State

- Single Claude API call with `tool_choice={"type": "tool", "name": "recommend_build"}`
- Claude invents products from training data — no real catalog
- DB only has `builds` table (caching completed builds)
- Input/output guardrails, rate limiting, prompt sections all in place

---

## Step 1: DB Schema — 2 New Tables + Migration

### `components` table

Stores every PC component we track across all stores.

```python
class Component(Base):
    __tablename__ = "components"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(30), index=True)      # "cpu", "gpu", etc.
    brand: Mapped[str] = mapped_column(String(100))                     # "AMD", "NVIDIA", etc.
    model: Mapped[str] = mapped_column(String(200))                     # "Ryzen 7 7800X3D"
    specs: Mapped[dict] = mapped_column(JSONB, default=dict)            # {"socket": "AM5", "tdp": "120", ...}
    in_stock: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"), onupdate=func.now())

    affiliate_links: Mapped[list["AffiliateLink"]] = relationship(back_populates="component")
```

**Indexes**: `(category, in_stock)` composite for the candidate query.

### `affiliate_links` table

Per-component, per-store pricing and affiliate URLs.

```python
class AffiliateLink(Base):
    __tablename__ = "affiliate_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id"), index=True)
    store: Mapped[str] = mapped_column(String(30))                      # "amazon", "computeruniverse", "caseking"
    url: Mapped[str] = mapped_column(String(500))                       # Full affiliate URL
    price_eur: Mapped[float] = mapped_column(nullable=False)
    last_checked: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    component: Mapped["Component"] = relationship(back_populates="affiliate_links")

    __table_args__ = (UniqueConstraint("component_id", "store"),)
```

### `builds` table (existing — minor update)

Add `request` JSONB column to store the original `BuildRequest` alongside the result.
Keep existing `request_hash` for cache lookups.

```python
class Build(Base):
    __tablename__ = "builds"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), unique=True)
    request: Mapped[dict] = mapped_column(JSONB, nullable=True)         # NEW: original BuildRequest
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
```

### Alembic migration

`alembic/versions/0002_component_catalog.py`:
- CREATE TABLE `components`
- CREATE TABLE `affiliate_links` with FK + unique constraint
- ALTER TABLE `builds` ADD COLUMN `request` JSONB

---

## Step 2: Seed Data — Initial Component Catalog

### `backend/app/db/seed.py`

Script to populate the catalog with real components and prices.
Organized by category with actual current pricing from the 3 stores.

**Minimum viable catalog** (enough to cover all budget ranges and goals):

| Category     | ~Count | Examples |
|-------------|--------|----------|
| CPU         | 12-15  | Ryzen 5 7600, i5-14600K, Ryzen 7 7800X3D, i7-14700K, Ryzen 9 7950X |
| GPU         | 10-12  | RTX 4060, RX 7600, RTX 4070 Super, RX 7800 XT, RTX 4080 Super |
| Motherboard | 10-12  | B650 boards (AM5), B760/Z790 (LGA1700), varying form factors |
| RAM         | 6-8    | DDR4 16/32GB kits, DDR5 16/32GB kits |
| Storage     | 6-8    | 500GB/1TB/2TB NVMe SSDs |
| PSU         | 6-8    | 550W through 850W, 80+ Gold/Platinum |
| Case        | 8-10   | ATX/mATX/mITX cases at various price points |
| Cooling     | 6-8    | Air coolers + 240/360mm AIOs |
| Monitor     | 4-6    | 1080p/1440p/4K gaming + work monitors |
| Keyboard    | 3-4    | Budget to mid-range mechanical |
| Mouse       | 3-4    | Budget to mid-range gaming/office |

**Total**: ~80-100 components with affiliate links across 3 stores.

**Specs JSONB structure** (per category):
```json
// CPU
{"socket": "AM5", "cores": "8", "threads": "16", "tdp": "120", "boost_ghz": "5.0"}

// Motherboard
{"socket": "AM5", "chipset": "B650", "ddr_type": "DDR5", "form_factor": "ATX", "max_ram_gb": "128"}

// GPU
{"vram_gb": "12", "tdp": "200", "length_mm": "310", "interface": "PCIe 4.0 x16"}

// RAM
{"ddr_type": "DDR5", "capacity_gb": "32", "speed_mhz": "6000", "modules": "2x16GB"}

// Case
{"form_factor": "ATX", "max_gpu_length_mm": "370", "max_cooler_height_mm": "170", "included_fans": "3"}

// PSU
{"wattage": "750", "efficiency": "80+ Gold", "modular": "full"}

// Cooling
{"type": "air", "height_mm": "165", "tdp_rating": "250"}
// or
{"type": "liquid", "radiator_size_mm": "360", "tdp_rating": "350"}
```

**Run**: `make seed` or `uv run python -m app.db.seed`

---

## Step 3: `backend/app/services/catalog.py` — Catalog Query Service

Queries the DB for candidate components based on the `BuildRequest`.

```python
class CatalogService:
    async def get_candidates(
        self,
        db: AsyncSession,
        request: BuildRequest,
    ) -> dict[str, list[CandidateComponent]]
```

**Query logic per category**:

```sql
SELECT c.*, al.store, al.url, al.price_eur
FROM components c
JOIN affiliate_links al ON al.component_id = c.id
WHERE c.category = :category
  AND c.in_stock = true
  AND (:brand_filter IS NULL OR c.brand = :brand_filter)
  AND (:form_factor_filter IS NULL OR c.specs->>'form_factor' = :form_factor)
ORDER BY al.price_eur ASC
```

**Filters applied per category**:
- `cpu`: brand filter from `cpu_brand` (if not `no_preference`)
- `gpu`: brand filter from `gpu_brand` (if not `no_preference`)
- `motherboard`: must match CPU socket + requested `form_factor`
- `ram`: must match motherboard DDR type
- `case`: must match requested `form_factor`
- `cooling`: filter by `cooling_preference` (liquid/air/any)

**Returns** `dict[ComponentCategory, list[CandidateComponent]]`:
```python
class CandidateComponent(BaseModel):
    id: int
    category: str
    brand: str
    model: str
    specs: dict[str, str]
    stores: list[StoreOption]  # [{store, url, price_eur}] — sorted cheapest first

class StoreOption(BaseModel):
    store: str
    url: str  # affiliate URL
    price_eur: float
```

**Cheapest price per component**: The `stores` list is sorted by price. The first entry is the cheapest option (used for budget estimation). Claude can pick a different store if consolidation saves on shipping.

**Categories to query**: All standard categories minus `existing_parts`. Add peripherals only if `include_peripherals=True`.

---

## Step 4: Update `ClaudeService.generate_build()` — Catalog-Driven Prompt

Replace the current single-shot approach. No agentic loop needed — Claude gets all candidates upfront and picks in one pass.

### Why single-pass works now

With the catalog approach, Claude doesn't need to iteratively search. It gets:
1. **Pre-filtered candidates** — only compatible, in-stock components
2. **Real prices** — from the affiliate_links table
3. **All categories at once** — can optimize across the full budget

The agentic loop was needed when Claude had to search and validate. With a catalog, the hard work is done by SQL, and Claude just optimizes.

### Updated flow in `generate_build()`

```python
async def generate_build(self, request, build_id, client_ip, db):
    # 1. Get candidates from catalog
    catalog = CatalogService()
    candidates = await catalog.get_candidates(db, request)

    if not candidates:
        raise ValueError("No components available for this configuration")

    # 2. Format candidates for Claude prompt
    candidates_text = self._format_candidates(candidates)

    # 3. Build user message with candidates
    user_message = self._build_user_message(request, candidates_text)

    # 4. Single Claude call — pick from candidates
    response = await self.client.messages.create(
        model=self.model,
        max_tokens=4096,
        system=system_prompt,
        tools=[PICK_BUILD_TOOL],
        tool_choice={"type": "tool", "name": "recommend_build"},
        messages=[{"role": "user", "content": user_message}],
    )

    # 5. Parse and validate result
    return self._parse_build_result(response, build_id, request, client_ip)
```

### Candidate formatting for Claude

```
## Available Components

### CPUs (12 options)
| # | Brand | Model | Socket | Cores | TDP | Best Price | Store |
|---|-------|-------|--------|-------|-----|-----------|-------|
| 1 | AMD   | Ryzen 7 7800X3D | AM5 | 8/16 | 120W | €389 | amazon.de |
| 2 | Intel | Core i5-14600K  | LGA1700 | 14/20 | 125W | €299 | caseking.de |
| ...

### GPUs (8 options)
| # | Brand | Model | VRAM | TDP | Length | Best Price | Store |
|---|-------|-------|------|-----|--------|-----------|-------|
| 1 | NVIDIA | RTX 4070 Super | 12GB | 220W | 310mm | €569 | computeruniverse |
| ...

(repeat for each category with candidates)
```

### `PICK_BUILD_TOOL` schema update

Same as current `BUILD_TOOL` but with an added constraint: `affiliate_url` and `affiliate_source` must come from the candidate list (Claude picks from provided options, doesn't invent URLs).

---

## Step 5: Update System Prompt

### New section: `backend/app/prompts/sections/candidate_selection.yaml`

```yaml
title: Candidate Selection
content: |
  ## How to Select Components

  You are given a pre-filtered list of available components per category.
  ALL components are in stock and ship to Cyprus.

  ### Your job
  1. Pick ONE component per required category from the candidates provided
  2. Optimize for the user's goal priorities (see Goals section)
  3. Stay within the budget range
  4. Ensure compatibility across all picks:
     - CPU socket must match motherboard socket
     - RAM DDR type must match motherboard
     - Case must fit the motherboard form factor
     - PSU wattage must cover CPU TDP + GPU TDP + 80W with 30% headroom
     - GPU length must fit the case
     - Cooler must fit the case
  5. Minimize total cost including shipping:
     - Each store used adds ~€10-15 shipping
     - If consolidating saves more than the price difference, do it

  ### Rules
  - ONLY select components from the provided candidate list
  - Use the exact affiliate_url from the candidate data
  - Use the exact price_eur from the candidate data
  - Do NOT invent components or prices not in the list
  - If no suitable candidate exists for a category, note it in the summary
```

### Remove `stores.yaml` search URL instructions

Claude no longer constructs search URLs — it uses the affiliate URLs from the DB.

### Keep existing sections
- `identity.yaml` — role lock, identity
- `goals.yaml` — goal priorities (critical/high/med/low)
- `compatibility.yaml` — compatibility rules (Claude still reasons about these)
- `budget_ranges.yaml` — budget tier descriptions
- `rules.yaml` — output format rules

---

## Step 6: Pass `db` Session to `generate_build()`

### `backend/app/api/v1/builder.py`

Update `create_build()` to pass the DB session to `generate_build()`:

```python
build = await claude.generate_build(
    payload, build_id=build_id, client_ip=client_ip, db=db
)
```

Also store the request in the build row:

```python
db.add(Build(
    id=build_id,
    request_hash=body_hash,
    request=payload.model_dump(mode="json"),  # NEW
    result=build.model_dump(mode="json"),
))
```

---

## Step 7: Tests

### Unit tests

1. **`test_catalog.py`** — CatalogService:
   - Returns candidates filtered by brand preference
   - Returns candidates filtered by form factor
   - Excludes out-of-stock components
   - Excludes existing_parts categories
   - Returns cheapest affiliate link first per component
   - Empty result when no matches

2. **`test_seed.py`** — Seed data:
   - All components have valid category enum values
   - All affiliate URLs pass the allowlist check
   - All prices are positive
   - Specs contain required keys per category

3. **`test_generate_build_catalog.py`** — Integration (mocked Claude):
   - Claude receives formatted candidate list
   - Result uses affiliate URLs from candidates (not invented)
   - Result prices match candidate prices
   - Works with different budget ranges / goals

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
| `backend/app/db/models.py` | **Modify** — add `Component`, `AffiliateLink` models; add `request` column to `Build` |
| `backend/alembic/versions/0002_component_catalog.py` | **New** — migration for new tables + builds.request column |
| `backend/app/db/seed.py` | **New** — seed script with ~80-100 real components + affiliate links |
| `backend/app/services/catalog.py` | **New** — CatalogService (DB queries for candidates) |
| `backend/app/services/claude.py` | **Modify** — catalog-driven prompt, format candidates, pass db |
| `backend/app/prompts/sections/candidate_selection.yaml` | **New** — instructions for picking from candidates |
| `backend/app/api/v1/builder.py` | **Modify** — pass db to generate_build, store request |
| `backend/tests/test_catalog.py` | **New** |
| `backend/tests/test_seed.py` | **New** |
| `backend/tests/test_generate_build_catalog.py` | **New** |
| `Makefile` | **Modify** — add `seed` target |

---

## Open Decisions

1. **Seed data source**: Manual curation with real current prices? Or start with a JSON fixture file?
2. **Price staleness**: How often to update prices? (Future: scraper/API. For now: manual updates + `last_checked` timestamp)
3. **Catalog size**: ~80-100 components enough for MVP? Or need more coverage?
