# PcCoach — Claude Code Guide

## Project Overview

PcCoach is an AI-powered PC build recommendation tool for the Cyprus market (Limassol).
Users describe their needs and budget; Claude recommends a full component list with affiliate links to buy each part.
Revenue model: affiliate commissions (Amazon.de for MVP, more stores planned) — no inventory, no ordering, no services.

## Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Backend   | Python 3.12, FastAPI, Anthropic SDK              |
| Engine    | pccoach-engine (standalone Python pkg, zero backend deps) |
| Database  | PostgreSQL 16 + SQLAlchemy 2 (async) + Alembic  |
| Frontend  | Next.js 15, React 19, TypeScript, Tailwind CSS  |
| AI        | Claude (`claude-sonnet-4-6`) via `ClaudeService`|
| Dev tools | uv (package manager), ruff (lint/format), pytest|
| Runtime   | Docker + Docker Compose                         |

## Project Structure

```
PcCoach/
├── backend/                    # See backend/CLAUDE.md for detailed docs
│   ├── app/
│   │   ├── api/v1/             # Route handlers (builder, search, router)
│   │   ├── db/                 # ORM models, product catalog JSON, seed script
│   │   ├── models/             # Pydantic request/response models
│   │   ├── services/           # ClaudeService, CatalogService, BuildValidator
│   │   ├── security/           # Input/output guardrails, prompt guard, blocklist
│   │   ├── prompts/            # YAML prompt sections + manager
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── database.py         # Async engine, session factory, Base
│   │   ├── limiter.py          # slowapi rate limiter + IP resolution
│   │   └── main.py             # FastAPI app + middleware + lifespan
│   ├── tests/                  # pytest suite (7 test files)
│   ├── alembic/                # DB migrations
│   ├── pyproject.toml          # Dependencies + ruff + pytest config
│   └── Dockerfile / Dockerfile.dev
├── frontend/                   # See frontend/CLAUDE.md for detailed docs
│   ├── src/
│   │   ├── app/                # Next.js App Router pages
│   │   ├── components/         # Shared React components
│   │   └── lib/                # API client, types, URL/price utilities
│   ├── next.config.js          # Rewrites, CSP, proxy timeout
│   ├── tailwind.config.ts      # Obsidian dark theme
│   ├── package.json
│   └── Dockerfile / Dockerfile.dev
├── engine/                     # See engine/CLAUDE.md for detailed docs
│   ├── __init__.py             # Public API: select_build()
│   ├── ports.py                # CatalogPort Protocol (abstract DB interface)
│   ├── models/                 # Frozen dataclasses: ProductRecord, BuildEngineResult
│   ├── core/                   # Dedup, families, scorer, selector, optimizer, validator
│   ├── config/                 # YAML profiles + hardware tiers + loader
│   └── tests/                  # 107 tests (unit + integration)
├── shared/
│   └── budget_goals.json       # Single source of truth (synced via `make sync-config`)
├── docker-compose.yml          # Production (4 services)
├── docker-compose.dev.yml      # Development (hot reload)
├── Makefile                    # All commands: dev, build, test, deploy, etc.
├── scripts/setup-nginx.sh      # Production nginx + SSL setup
└── requests.http               # Manual endpoint testing
```

## Core Flow

Two build paths exist, toggled by the `USE_BUILD_ENGINE` env var (default: `false`).

### Engine Path (`USE_BUILD_ENGINE=true`) — Recommended

```
User fills form → POST /api/v1/build (BuildRequest)
               → InputGuardrail checks (scope, toxicity, budget, dedup)
               → Cache check (Build table by request_hash)
               → Build engine selects components deterministically:
                   Phase 1 — Selecting: dedup → families → scoring → greedy select → optimize
               → Claude writes summary (single API call, no tools):
                   Phase 2 — Summarizing: 2-3 sentence narrative + upgrade/downgrade reasons
               → OutputGuardrail checks (leak, off-topic, URL allowlist, PII, price)
               → BuildResult streamed as SSE events
               → Persisted to DB (Build table)
```

Cost: ~$0.001-0.003/request. Latency: <5s. Deterministic component selection.

### Agentic Path (`USE_BUILD_ENGINE=false`) — Legacy fallback

```
User fills form → POST /api/v1/build (BuildRequest)
               → InputGuardrail checks (scope, toxicity, budget, dedup)
               → Cache check (Build table by request_hash)
               → ClaudeService starts agentic tool-use loop:
                   Phase 1 — Scout: Claude calls scout_catalog (all categories)
                   Phase 2 — Select: Claude calls query_catalog (only if needed)
                   Phase 3 — Submit: Claude calls submit_build (component_ids)
               → BuildValidator checks compatibility (socket, DDR, form factor, PSU, GPU)
               → If invalid: repair within same loop (max 1 attempt)
               → CatalogService resolves component_ids → affiliate URLs
               → OutputGuardrail checks (leak, off-topic, URL allowlist, PII, price)
               → BuildResult streamed as SSE events
               → Persisted to DB (Build table)
```

Cost: ~$0.01/request. Latency: 7-11s. Non-deterministic.

Both paths share the same `BuildResult` model, DB persistence, and output guardrails. `/api/v1/search` still uses the agentic tool loop.

### SSE Streaming Protocol (`POST /api/v1/build`)

The build endpoint returns an SSE stream (`text/event-stream`, HTTP 200).
Pre-stream errors (guardrail blocks, rate limits) still return normal HTTP errors.

| SSE event type | When | Payload |
|----------------|------|---------|
| `progress` | After each tool call / engine phase | `{"type":"progress","phase":"scouting\|selecting\|validating\|repairing\|summarizing","turn":N,"elapsed_s":N,"categories_scouted":[...],"categories_queried":[...],"tool":"..."}` |
| `result` | Build complete, guardrails passed | Full `BuildResult` JSON |
| `error` | Any exception during streaming | `{"status":NNN,"detail":"..."}` |
| `: keepalive` | Every ~15 s of inactivity | SSE comment (no event/data) |

Clients must handle all event types. Errors arrive as SSE events (not HTTP status codes) because the stream has already started.

The frontend timeout (`120_000 ms`) is coupled to the backend's `AGENTIC_LOOP_TIMEOUT` (default `120.0 s`). Keep them in sync.

### Agentic Tool Loop

Claude does **not** receive the full catalog in the prompt. Instead, it queries incrementally:
- `scout_catalog` — overview of up to 50 products per category (slim format: `id={N} | Brand Model | specs | EUR {price}`)
- `query_catalog` — targeted refinement with filters (socket, DDR, form factor, brand, cooling_type). Only if scout didn't show a compatible option.
- `submit_build` / `recommend_component` — terminal tools that trigger server-side validation

The `BuildValidator` (server-side) enforces hard compatibility rules. If validation fails, errors are sent back as `is_error` tool results and Claude repairs within the same conversation. Max 1 repair attempt; after that, `BuildValidationError` → HTTP 400.

Target loop pattern: **scout → submit** (2 turns). Each extra query_catalog adds ~10s latency.

## API Endpoints

| Method | Path | Description | Rate Limit |
|--------|------|-------------|------------|
| POST | `/api/v1/build` | Submit build requirements (returns SSE stream) | `RATE_LIMIT_AI` (shared) |
| GET | `/api/v1/build` | List all builds | — |
| GET | `/api/v1/build/{id}` | Get a build by ID | `RATE_LIMIT_READ` |
| POST | `/api/v1/search` | Search for a single component | `RATE_LIMIT_AI` (shared) |
| GET | `/health` | Database connectivity check | — |
| POST | `/internal/clear-cache` | Clear in-memory search cache (private/loopback only) | — |

## Common Commands

```bash
make dev          # Start dev environment (hot reload)
make dev-build    # Rebuild dev images (run after dependency changes)
make dev-deploy   # Build, migrate, and start dev containers (detached)
make migrate      # Run pending Alembic migrations (dev)
make seed         # Seed the component catalog (idempotent, clears search cache)
make sync-config  # Copy shared/budget_goals.json to all services
make lock         # Regenerate uv.lock and package-lock.json
make test         # Run pytest in backend container
make test-engine  # Run engine tests locally (no Docker needed)
make lint         # Run ruff check + format check
make logs         # Tail all container logs
make deploy       # Production: pull, sync-config, build, migrate, up, seed
make init         # Copy .env.example to .env for all services
```

## Shared Configuration

`shared/budget_goals.json` is the single source of truth for budget→goal mappings.
It is copied to three locations by `make sync-config`:
- `backend/app/budget_goals.json`
- `frontend/src/lib/budget_goals.json`
- `telegram_bot/budget_goals.json`

Always edit the shared file and run `make sync-config` — never edit the copies directly.

## Environment Variables

Backend (`.env` in `backend/`):
```
ANTHROPIC_API_KEY=...
CORS_ORIGINS=["http://localhost:3000"]
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://pccoach:<password>@db:5432/pccoach
MAX_TOOL_TURNS=20               # Max agentic loop iterations
AGENTIC_LOOP_TIMEOUT=120.0      # Agentic loop wall-clock timeout (seconds)
USE_BUILD_ENGINE=false          # true = deterministic engine + summary, false = agentic loop
RATE_LIMIT_AI=2/day             # Shared pool for /build and /search
RATE_LIMIT_READ=60/minute       # GET /build/{id}
ARIZE_API_KEY=...               # Optional: LLM observability
ARIZE_SPACE_ID=...              # Optional: LLM observability
```

Production shell environment (set on the droplet, not in `.env`):
```
POSTGRES_PASSWORD=<strong-password>   # used by docker-compose.yml for the db service
```

The password in `DATABASE_URL` must match `POSTGRES_PASSWORD`. In dev,
`docker-compose.dev.yml` hardcodes `POSTGRES_PASSWORD=pccoach`, so
`DATABASE_URL` should use `pccoach` as the password locally.

Frontend (`.env` in `frontend/`):
```
BACKEND_URL=http://localhost:8000
```
Note: API calls use relative URLs proxied by Next.js rewrites (`next.config.js`).
`BACKEND_URL` is the var that controls where those rewrites forward to.

## Conventions

- **Package manager**: `uv` only (backend) — never use pip directly
- **Linter/formatter**: `ruff` (line length 88, Python 3.12 target, rules: E, F, I, UP)
- **Settings**: all config via environment variables, loaded through `app/config.py` (pydantic-settings)
- **API versioning**: routes live under `/api/v1/`
- **Claude model**: `claude-sonnet-4-6` — do not downgrade without discussion
- **Async**: use `async def` for all route handlers and service methods
- **Singletons**: ClaudeService, CatalogService use `@lru_cache(maxsize=1)`
- **Branching**: feature → `development` → `master` (production)
- **Tests**: in-memory SQLite (aiosqlite) with JSONB→JSON fallback, mocked Anthropic API, `asyncio_mode = "auto"`

## Docker Architecture

### Production (`docker-compose.yml`)
- **db**: PostgreSQL 16 Alpine, internal only, healthcheck, 512MB RAM
- **backend**: FastAPI on `127.0.0.1:8000`, depends on db, 1GB RAM
- **frontend**: Next.js on `127.0.0.1:3000`, depends on backend, 512MB RAM
- **telegram-bot**: Depends on backend, 256MB RAM

### Development (`docker-compose.dev.yml`)
- **db**: PostgreSQL on `0.0.0.0:5432`, `POSTGRES_PASSWORD=pccoach`
- **backend**: Hot reload via source mount (`./backend:/app`), no resource limits
- **frontend**: Hot reload via source mount, named volumes for `node_modules` and `.next`

### Nginx (Production)
- Domain: `thepccoach.com` + `www.thepccoach.com`
- `/api/` → backend:8000 (120s proxy timeout, buffering OFF for SSE)
- `/health` → backend:8000
- `/` → frontend:3000
- SSL via Certbot (auto-renewal)

---

## Security & Guardrails

### Forbidden Patterns

| Pattern | Why forbidden |
|---------|---------------|
| Raw SQL strings with f-strings or `.format()` from user input | SQL injection. Use SQLAlchemy ORM or `text(...).bindparams(...)` only. |
| `dangerouslySetInnerHTML` with unsanitized data | XSS. Use text content or DOMPurify if HTML rendering is ever needed. |
| `CORS_ORIGINS = ["*"]` in production | Opens all cross-origin requests. Always set explicit origin list. |
| Raw user strings interpolated directly into Claude system prompt | Prompt injection. User text must go through `sanitize_user_input()` and be wrapped in `<user_request>…</user_request>`. |
| Logging `anthropic_api_key`, `database_url`, or any secret value | Secret leakage. Use `SecretStr` — access via `.get_secret_value()` only in the code that needs it, never in logs. |
| Catching `Exception` without re-raising a clean HTTP response | Information leakage. Always log the full traceback server-side and return only `{"detail": "Internal server error"}` to the client. |

### Guardrails Architecture

```
Request
  │
  ▼
[InputGuardrail]  ← backend/app/security/guardrails.py
  │  • Scope check: hardware keyword allowlist
  │  • Toxicity/abuse blocklist (regex patterns)
  │  • Budget sanity (€50–€100,000)
  │  • Duplicate flooding (SHA-256 hash + TTLCache, 3 per 600s per IP)
  │
  ▼ (passes)
[ClaudeService]   ← backend/app/services/claude.py
  │  • sanitize_user_input() on all free-text fields
  │  • _ROLE_LOCK prepended to system prompt
  │  • User text wrapped in <user_request>…</user_request>
  │
  ▼ (Claude responds)
[OutputGuardrail] ← backend/app/security/output_guard.py
  │  • System-prompt leak detection → 500
  │  • Off-topic/refusal detection → 400
  │  • Affiliate URL allowlist enforcement (strip non-allowed)
  │  • Price sanity (strip ≤0 or >€50k; warn if total >150% budget)
  │  • PII strip from text (phone, email, external URLs)
  │
  ▼ (clean)
Client
```

### Affiliate URL Allowlist

Only URLs from these hosts are permitted. **All three lists must be kept in sync.**

| Store | Allowed hosts |
|-------|--------------|
| Amazon.de | `amazon.de`, `www.amazon.de` |

| Location | Variable |
|----------|----------|
| Backend models | `backend/app/models/builder.py:_ALLOWED_AFFILIATE_HOSTS` |
| Backend output guard | `backend/app/security/output_guard.py:_AFFILIATE_ALLOWED_HOSTS` |
| Frontend | `frontend/src/lib/url.ts:ALLOWED_AFFILIATE_HOSTS` |

### Rate Limits (configurable via env vars)

| Endpoint | Default | Env var |
|----------|---------|---------|
| POST /api/v1/build | 2/day (shared pool) | `RATE_LIMIT_AI` |
| POST /api/v1/search | 2/day (shared pool) | `RATE_LIMIT_AI` |
| GET /api/v1/build/{id} | 60/minute | `RATE_LIMIT_READ` |

`POST /build` and `POST /search` share a single rate-limit pool (`scope="ai_calls"`).
Format: `"N/period"` where period is `second`, `minute`, `hour`, or `day`.
Rate limiting is disabled when `ENVIRONMENT=development`.

### Secrets

- `ANTHROPIC_API_KEY` and `DATABASE_URL` are `SecretStr` in `config.py`
- Never log these values — log `"set"` / `"unset"` as a boolean indicator
- Never commit `.env` files — only `.env.example` with placeholders

---

## Key Constants

| Item | Value | Location |
|------|-------|----------|
| Max tool turns | 20 | `config.py:max_tool_turns` |
| Agentic loop timeout | 120.0 s | `config.py:agentic_loop_timeout` |
| Claude model | `claude-sonnet-4-6` | `config.py:claude_model` |
| Claude API timeout | 90 s | `claude.py:_TIMEOUT` |
| Search cache TTL | 30 min, 128 entries | `search.py:_search_cache` |
| Duplicate detection window | 600 s, 3 allowed | `guardrails.py:_dup_cache` |
| Max component price | €50,000 | `output_guard.py:_MAX_COMPONENT_PRICE` |
| Budget overage ratio | 1.5x | `output_guard.py:_BUDGET_OVERAGE_RATIO` |
| SSE keepalive interval | 15 s | `builder.py` |
| Scout limit | 50 products/category | `catalog.py:scout_all()` |
| Query limit | 15 products | `catalog.py:query_for_tool()` |
| Max field length (prompt guard) | 2,000 chars | `prompt_guard.py` |
| Amazon affiliate tag | `thepccoach-21` | `seed.py:_AMAZON_TAG` |
| Frontend proxy timeout | 120,000 ms | `next.config.js:proxyTimeout` |
| Engine budget target ratio | 0.85 | `engine/core/selector.py:_BUDGET_TARGET_RATIO` |
| Engine category flex | 1.5x | `engine/core/selector.py:_CATEGORY_FLEX` |
| Engine family feasibility | 40% of budget | `engine/core/selector.py:_select_family()` |

---

## Code Review

The review skill lives at `.claude/skills/pccoach-review/SKILL.md`.
Trigger it by saying **"do a comprehensive review"** (or "review the code", "review my changes").
Do not freeform review without loading the skill first.
