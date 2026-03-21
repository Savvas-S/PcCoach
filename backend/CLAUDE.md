# PcCoach Backend — Claude Code Guide

## Architecture Overview

FastAPI application with two build paths (toggled by `USE_BUILD_ENGINE`):
1. **Engine path** (recommended): deterministic component selection via `pccoach-engine` + single Claude summary call
2. **Agentic path** (legacy fallback): Claude queries a product catalog through tools, selects components via agentic tool loop

```
app/
├── api/v1/
│   ├── router.py              # Mounts builder + search routers under /api/v1
│   ├── builder.py             # POST /build (SSE stream), GET /build/{id}
│   └── search.py              # POST /search, in-memory cache, clear_search_cache()
├── adapters/
│   └── catalog_adapter.py     # SqlAlchemyCatalogAdapter (implements engine CatalogPort)
├── db/
│   ├── models.py              # ORM: Component, AffiliateLink, Build
│   ├── all_products.json      # Scraped product catalog (~200 products, 8 categories)
│   └── seed.py                # Loads JSON + hardcoded peripherals → seeds DB
├── models/
│   └── builder.py             # Pydantic: BuildRequest, BuildResult, enums, validators
├── services/
│   ├── claude.py              # ClaudeService: agentic loop + summarize_build() for engine path
│   ├── catalog.py             # CatalogService: scout_all, query_for_tool, resolve_components
│   └── build_validator.py     # BuildValidator: socket, DDR, form factor, PSU, GPU checks
├── security/
│   ├── guardrails.py          # InputGuardrail: scope, blocklist, budget, duplicate
│   ├── output_guard.py        # OutputGuardrail: leak, off-topic, URL, price, PII
│   ├── prompt_guard.py        # sanitize_user_input(): truncate, detect, strip, neutralize
│   ├── blocklist.py           # Compiled regex patterns for toxicity detection
│   └── events.py              # Structured JSON logging (security.events logger)
├── prompts/
│   ├── manager.py             # build_system_prompt(), search_system_prompt() — @lru_cache
│   ├── search.yaml            # Search prompt (single component)
│   └── sections/              # Build prompt sections (loaded in SECTION_ORDER)
│       ├── identity.yaml
│       ├── budget_ranges.yaml
│       ├── goals.yaml
│       ├── stores.yaml
│       ├── candidate_selection.yaml
│       ├── rules.yaml
│       ├── compatibility.yaml
│       └── summary.yaml       # Summary-only prompt (engine path)
├── config.py                  # Settings (pydantic-settings, SecretStr)
├── database.py                # init_db(), get_db(), async engine + session factory
├── limiter.py                 # slowapi Limiter, _get_client_ip() with proxy trust
└── main.py                    # FastAPI app, lifespan, middleware, exception handlers

tests/
├── test_builder_api.py        # SSE streaming, caching, error mapping
├── test_guardrails.py         # Input + output guardrail checks
├── test_build_validator.py    # All compatibility rules
├── test_catalog.py            # scout_all, query_for_tool, resolve_components
├── test_tool_loop.py          # Agentic loop mechanics (mocked Claude API)
├── test_models.py             # Pydantic validators, affiliate URL validation
└── test_seed.py               # Catalog seeding idempotency
```

## Database Schema

### Component
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | Auto-increment |
| category | String(30) | Indexed. Values: cpu, gpu, motherboard, ram, storage, psu, case, cooling, monitor, keyboard, mouse, toolkit |
| brand | String(100) | |
| model | String(200) | |
| normalized_model | String(200) | Nullable. Used by engine for multi-shop dedup. Defaults to `model` value. |
| specs | JSONB | Dict of component properties (filtered by `CATEGORY_SPEC_KEYS` on read) |
| in_stock | Boolean | Indexed, default True |
| created_at | DateTime(tz) | |
| updated_at | DateTime(tz) | |
| affiliate_links | Relationship | One-to-many, cascade delete-orphan |

### AffiliateLink
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| component_id | Integer FK | CASCADE delete, indexed |
| store | String(30) | "amazon" |
| url | String(500) | Full Amazon.de URL with `?tag=thepccoach-21` |
| price_eur | Float | |
| last_checked | DateTime(tz) | |
| Unique | (component_id, store) | |

### Build (cache)
| Column | Type | Notes |
|--------|------|-------|
| id | String(16) PK | `secrets.token_urlsafe(8)` |
| request_hash | String(64) UNIQUE | SHA-256 of canonical BuildRequest JSON |
| request | JSONB | Full BuildRequest |
| result | JSONB | Full BuildResult |
| created_at | DateTime(tz) | |

## Pydantic Models (`app/models/builder.py`)

### Enums
- **UserGoal**: `high_end_gaming`, `mid_range_gaming`, `low_end_gaming`, `light_work`, `heavy_work`, `designer`, `architecture`
- **BudgetRange**: `0_1000`, `1000_1500`, `1500_2000`, `2000_3000`, `over_3000`
- **FormFactor**: `atx`, `micro_atx`, `mini_itx`
- **CPUBrand / GPUBrand**: `intel`/`nvidia`, `amd`, `no_preference`
- **CoolingPreference**: `no_preference`, `liquid`, `air`
- **ComponentCategory**: `cpu`, `gpu`, `motherboard`, `ram`, `storage`, `psu`, `case`, `cooling`, `monitor`, `keyboard`, `mouse`, `toolkit`

### BuildRequest
Fields: `goal`, `budget_range`, `form_factor` (default: atx), `cpu_brand`, `gpu_brand`, `cooling_preference`, `include_peripherals` (default: False), `existing_parts` (list), `notes` (1-500 chars)

Validators:
- `strip_notes()` — strip whitespace, None if empty
- `deduplicate_existing_parts()` — remove dupes preserving order
- `validate_goal_for_budget()` — cross-check via `_VALID_GOALS_FOR_BUDGET` (loaded from `budget_goals.json`)

### BuildResult
Fields: `id`, `components[]`, `total_price_eur` (auto-computed), `summary`, `upgrade_suggestion`, `downgrade_suggestion`, `status` ("completed"), `warnings[]`

### Affiliate URL Validation
`_ALLOWED_AFFILIATE_HOSTS = frozenset({"amazon.de", "www.amazon.de"})` — enforced by Pydantic validators on `ComponentRecommendation`, `UpgradeSuggestion`, `DowngradeSuggestion`, `ComponentSearchResult`.

## ClaudeService (`app/services/claude.py`)

### Tool Schemas (4 tools)

| Tool | Purpose | Category Enum | Terminal? |
|------|---------|---------------|-----------|
| `scout_catalog` | Overview: up to 50 in-stock products/category, sorted by price | Build: `_BUILD_CATEGORIES` (no toolkit) | No |
| `query_catalog` | Filtered: up to 15 results with brand/socket/ff/ddr/cooling filters | Build: `_BUILD_CATEGORIES` | No |
| `submit_build` | Submit final build with component_ids, summary, upgrade/downgrade | — | Yes |
| `recommend_component` | Submit single component pick (search endpoint) | — | Yes |

Search variants (`SCOUT_SEARCH_TOOL`, `QUERY_SEARCH_TOOL`) include `_ALL_CATEGORIES` (including toolkit).

### Agentic Loop (`_tool_loop_gen`)

Async generator driving the loop:
1. Create Claude message with system prompt (ephemeral cache control) + tools + messages
2. Parse `tool_use` blocks from response
3. Route to handler: `_handle_scout_catalog`, `_handle_query_catalog`, or `_handle_terminal_tool`
4. Yield `{"type": "progress", ...}` after each tool call
5. If terminal tool succeeds → yield `{"type": "done", "data": ...}` and return
6. If repair needed → add `is_error` tool result, continue loop (max 1 repair)
7. Track token usage per turn, log estimated cost at completion

Guard rails:
- Max turns: `settings.max_tool_turns` (default 20)
- Wall-clock timeout: `settings.agentic_loop_timeout` (default 120s), checked before AND after each API call
- Duplicate query detection (JSON key comparison)
- Premature submission check (all required categories must be scouted and submitted)

### Prompt Assembly
- `_ROLE_LOCK` prepended to every prompt (anti-injection anchor)
- User notes wrapped in `<user_request>...</user_request>` after `sanitize_user_input()`
- Build prompt: 7 YAML sections loaded via `build_system_prompt()` → `@lru_cache`
- Search prompt: `search.yaml` via `search_system_prompt()` → `@lru_cache`

Prompt section load order: identity → budget_ranges → goals → stores → candidate_selection → rules → compatibility

### Result Building (`_build_result_from_resolved`)
1. Resolve component_ids → `ResolvedComponent` via `CatalogService`
2. Build `ComponentRecommendation[]` with affiliate URLs
3. Handle upgrade/downgrade suggestions (resolve their component_ids too)
4. Run `OutputGuardrail.check()` → may block, warn, or strip
5. Merge validation warnings

### `summarize_build()` (engine path)

Module-level async function (not a method on ClaudeService). Used when `USE_BUILD_ENGINE=true`.
- Input: `BuildRequest` + `BuildEngineResult` from engine
- Makes a single Claude API call (max_tokens=400, timeout=30s) with `summary.yaml` prompt
- Parses `SUMMARY:` / `UPGRADE_REASON:` / `DOWNGRADE_REASON:` format from response
- Returns `(summary_text, upgrade_reason, downgrade_reason)`
- No tools attached — pure text generation

## Engine Integration (`app/adapters/catalog_adapter.py`)

`SqlAlchemyCatalogAdapter` implements the engine's `CatalogPort` Protocol:
- `get_all_products(category?)` → queries Component table with eager-loaded affiliate_links
- Maps ORM models to engine `ProductRecord` / `ListingRecord` frozen dataclasses
- Uses `comp.normalized_model or comp.model` for dedup key

The engine path in `builder.py` (`_build_events_engine`):
1. Emits SSE `progress(phase="selecting")`
2. Calls `engine.select_build()` via `SqlAlchemyCatalogAdapter`
3. Emits SSE `progress(phase="summarizing")`
4. Calls `summarize_build()` for narrative text
5. Assembles `BuildResult` from engine output + summary
6. Runs `OutputGuardrail.check()` before returning

## CatalogService (`app/services/catalog.py`)

### CATEGORY_SPEC_KEYS
Per-category spec filtering — only these keys are exposed to Claude and in results:
- **cpu**: socket, cores, threads, boost_ghz, tdp, integrated_graphics
- **gpu**: vram_gb, tdp, length_mm
- **motherboard**: socket, chipset, form_factor, ddr_type
- **ram**: ddr_type, capacity_gb, speed_mhz, modules
- **storage**: type, capacity_gb, interface, read_mbps
- **psu**: wattage, efficiency
- **case**: form_factor, max_gpu_length
- **cooling**: type, radiator_mm, socket_support
- **monitor**: resolution, size_inches, panel, refresh_hz
- **keyboard**: type, switch, layout
- **mouse**: sensor, weight_g, wireless
- **toolkit**: type

### Key Methods
- `scout_all(db, categories, limit=50)` — sequential queries per category (AsyncSession not thread-safe), returns `dict[str, list[ToolCatalogResult]]`
- `query_for_tool(db, category, brand?, socket?, form_factor?, ddr_type?, cooling_type?, limit=15)` — filtered query with MIN(price) grouping, case-insensitive filters
- `resolve_components(db, component_ids)` — eager-load affiliate_links, picks cheapest link, returns `dict[int, ResolvedComponent]`

## BuildValidator (`app/services/build_validator.py`)

### Compatibility Checks (in order)
1. **Missing categories** — all required must be present
2. **Socket match** — CPU.socket == motherboard.socket
3. **DDR match** — RAM.ddr_type == motherboard.ddr_type
4. **Form factor** — motherboard form factor rank ≤ case rank (ATX=3, Micro-ATX=2, Mini-ITX=1)
5. **GPU length** — GPU.length_mm ≤ case.max_gpu_length
6. **Cooler socket** — CPU.socket in cooler.socket_support (comma-separated)
7. **PSU wattage** — PSU ≥ (CPU TDP + GPU TDP + 80W) × 1.3. Warning if < ×1.1

### Helper Functions
- `required_categories(existing_parts, include_peripherals)` — computes required set from CORE + optional PERIPHERAL minus excluded
- `format_repair_error(errors)` — formats errors for Claude to fix: `"- [rule] message"`

## Input Guardrails (`app/security/guardrails.py`)

### Checks (in order, short-circuit on first failure)
1. **Hardware intent** — currently always passes (intent encoded in validated enums)
2. **Blocklist** — regex patterns from `blocklist.py` (violence, sexual, hate, spam)
3. **Budget** — defence-in-depth: budget upper ≤ €100,000
4. **Duplicate** — TTLCache keyed by `"{client_ip}:{body_hash}"`, allows 3 per 600s window

### Hashing
- `hash_build_request()` — canonical JSON, sorted keys, lowercased notes → SHA-256
- `hash_search_request()` — lowercased description → SHA-256

## Output Guardrails (`app/security/output_guard.py`)

### Checks (in order)
1. **Prompt leak** — regex patterns on all text fields → `GuardrailBlocked` (500)
2. **Off-topic/refusal** — "I cannot", "As an AI", etc. → `GuardrailBlocked` (400)
3. **Affiliate URL sanitize** — strip non-allowlisted URLs via `model_copy`
4. **Price sanity** — strip ≤0 or >€50k components; warn if total > budget × 1.5
5. **PII strip** — phone, email, non-allowlisted URLs → "[removed]" in summary text

Budget upper bounds for overage check: `{0_1000: 1000, 1000_1500: 1500, 1500_2000: 2000, 2000_3000: 3000, over_3000: 5000}`

## Prompt Guard (`app/security/prompt_guard.py`)

`sanitize_user_input(text)` operations (in order):
1. Truncate to 2,000 chars (log warning)
2. Detect injection patterns (log but don't block — InputGuardrail blocks)
3. Strip XML-like tags (`<system>`, `<prompt>`, `<instructions>`, etc.)
4. Neutralize structural chars (triple backticks, triple dashes → spaces)
5. Strip whitespace

## Rate Limiting (`app/limiter.py`)

- `_get_client_ip()`: trusts `X-Real-IP` header only if direct connection is from loopback/private IP (nginx proxy)
- Limiter disabled when `ENVIRONMENT=development`
- Shared scope `"ai_calls"` for POST /build + POST /search
- Separate limit for GET /build/{id}

## SSE Streaming (`app/api/v1/builder.py`)

### Producer-Consumer Pattern
- Producer (`_build_events`): runs agentic loop, puts events into `asyncio.Queue`
- Consumer: reads queue via `asyncio.wait_for` with 15s timeout → sends keepalive comments
- On error: maps exception to `(status, detail)` via `_map_error()`, sends SSE error event
- Special: `AuthenticationError` → 3s sleep before error (avoids API timeout cascade)

### Build Cache
- Pre-stream: check Build table by `request_hash` → if found, return cached `BuildResult` immediately
- Post-stream: persist new Build to DB with `request_hash` for dedup

## Database Seeding (`app/db/seed.py`)

- `_AMAZON_TAG = "thepccoach-21"` — appended to all affiliate URLs
- Loads `all_products.json` (~200 scraped products across 8 categories)
- Appends hardcoded `_PERIPHERAL_COMPONENTS`: 5 monitors, 3 keyboards, 4 mice (with ASINs + prices)
- Idempotent: checks `SELECT count(*)` before seeding
- After seed: calls `POST /internal/clear-cache` to invalidate stale search results

## Testing

### Setup
- In-memory SQLite (`sqlite+aiosqlite:///:memory:`) — no PostgreSQL needed
- JSONB columns patched to JSON at runtime for SQLite compatibility
- Mocked Anthropic API (`unittest.mock.AsyncMock`)
- `asyncio_mode = "auto"` (no `@pytest.mark.asyncio` needed)
- Fresh DB per test via `@pytest.fixture`

### Test Files
| File | Tests |
|------|-------|
| `test_builder_api.py` | POST /build SSE stream parsing, caching, error events, GET /build/{id} |
| `test_guardrails.py` | InputGuardrail + OutputGuardrail for build and search |
| `test_build_validator.py` | Socket, DDR, form factor, GPU length, cooler, PSU validation |
| `test_catalog.py` | scout_all, query_for_tool, resolve_components |
| `test_tool_loop.py` | Agentic loop mechanics, tool handlers, terminal logic, repair flow |
| `test_models.py` | Pydantic validators, affiliate URL checks, enum validation |
| `test_seed.py` | Catalog seeding idempotency |

### Running Tests
```bash
make test                           # via Docker (preferred)
cd backend && uv run pytest         # locally (needs aiosqlite)
cd backend && uv run pytest -x -v   # verbose, stop on first failure
```

## Dependencies

### Core
fastapi, uvicorn[standard], anthropic, pydantic, pydantic-settings, httpx, pyyaml, slowapi, cachetools, sqlalchemy[asyncio], asyncpg, alembic, openinference-instrumentation-anthropic, arize-otel

### Dev
pytest, pytest-asyncio, ruff, aiosqlite, pip-audit

### Build System
hatchling (PEP 517)

## Migrations

```bash
# Create new migration
uv run alembic revision --autogenerate -m "description"
# Apply pending
uv run alembic upgrade head
# Rollback one
uv run alembic downgrade -1
```

Current migrations:
1. `0001_initial.py` — `builds` table (id, request_hash, result, created_at)
2. `0002_component_catalog.py` — `components` + `affiliate_links` tables, adds `request` column to builds
3. `0003_add_normalized_model.py` — adds `normalized_model` column to components, backfills from `model`

`alembic/env.py` reads `DATABASE_URL` from settings at import time.
