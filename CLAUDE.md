# PcCoach — Claude Code Guide

## Project Overview

PcCoach is an AI-powered PC build recommendation tool for the Cyprus market (Limassol).
Users describe their needs and budget; Claude recommends a full component list with affiliate links to buy each part.
Revenue model: affiliate commissions (Amazon.de, ComputerUniverse, Caseking) — no inventory, no ordering, no services.

## Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Backend   | Python 3.12, FastAPI, Anthropic SDK             |
| Database  | PostgreSQL 16 + SQLAlchemy 2 (async) + Alembic  |
| Frontend  | Next.js 15, React 19, TypeScript, Tailwind CSS  |
| AI        | Claude (`claude-sonnet-4-6`) via `ClaudeService`|
| Dev tools | uv (package manager), ruff (lint/format), pytest|
| Runtime   | Docker + Docker Compose                         |

## Project Structure

```
PcCoach/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── router.py         # Registers all routers
│   │   │   └── builder.py        # Build recommendation endpoints
│   │   ├── models/
│   │   │   └── builder.py        # BuildRequest, ComponentRecommendation, BuildResult
│   │   ├── services/claude.py    # Claude integration (wired up later)
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   └── main.py               # FastAPI app + CORS
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   └── src/app/                  # Next.js App Router
├── requests.http                 # Manual endpoint testing
├── docker-compose.yml            # Production
├── docker-compose.dev.yml        # Development (hot reload)
└── Makefile                      # Common commands
```

## Core Flow

```
User fills form → POST /api/v1/build (BuildRequest)
               → Claude generates ComponentRecommendation list
               → BuildResult returned with affiliate links per component
               → User clicks affiliate link → buys on store
               → You earn commission
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/build` | Submit build requirements |
| GET | `/api/v1/build` | List all builds |
| GET | `/api/v1/build/{id}` | Get a build by ID |

## Common Commands

```bash
make dev          # Start dev environment (hot reload)
make dev-build    # Rebuild dev images
make lock         # Regenerate uv.lock and package-lock.json
make test         # Run pytest in backend container
make lint         # Run ruff check + format check
make logs         # Tail all container logs
```

## Backend Conventions

- **Package manager**: `uv` only — never use pip directly
- **Linter/formatter**: `ruff` (line length 88, Python 3.12 target)
- **Settings**: all config via environment variables, loaded through `app/config.py`
- **API versioning**: routes live under `/api/v1/`
- **Claude model**: `claude-sonnet-4-6` — do not downgrade without discussion
- **Async**: use `async def` for all route handlers and service methods

## Environment Variables

Backend (`.env` in `backend/`):
```
ANTHROPIC_API_KEY=...           # Optional until AI is wired up
CORS_ORIGINS=["http://localhost:3000"]
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://pccoach:pccoach@db:5432/pccoach
POSTGRES_USER=pccoach
POSTGRES_PASSWORD=pccoach
POSTGRES_DB=pccoach
```

Frontend (`.env` in `frontend/`):
```
BACKEND_URL=http://localhost:8000
```
Note: API calls use relative URLs proxied by Next.js rewrites (`next.config.js`).
`BACKEND_URL` is the var that controls where those rewrites forward to — not `NEXT_PUBLIC_API_URL`.

## Key Models (`backend/app/models/builder.py`)

- `BuildRequest` — user's requirements (goal, budget, preferences)
- `ComponentRecommendation` — one component with price + affiliate URL
- `BuildResult` — full response: request + list of components + summary

## Notes for Claude Code

- No services (cleaning/repair), no cart, no checkout — this is an affiliate tool
- `anthropic_api_key` is optional until AI features are wired up
- In-memory stores are placeholders — DB layer coming next
- Do not add abstraction layers unless clearly needed
- Always use `uv run` inside containers, never bare `python` or `pip`
- Do not commit `.env` files

---

## Security & Guardrails

### Forbidden Patterns

| Pattern | Why forbidden |
|---------|---------------|
| Raw SQL strings with f-strings or `.format()` from user input | SQL injection. Never construct SQL strings from user input. Use SQLAlchemy ORM or `text(...).bindparams(...)` only. |
| `dangerouslySetInnerHTML` with unsanitized data | XSS. Use text content or DOMPurify if HTML rendering is ever needed. |
| `CORS_ORIGINS = ["*"]` in production | Opens all cross-origin requests. Always set explicit origin list. |
| Raw user strings interpolated directly into Claude system prompt | Prompt injection. User text must go through `sanitize_user_input()` and be wrapped in `<user_request>…</user_request>`. |
| Logging `anthropic_api_key`, `database_url`, or any secret value | Secret leakage. Use `SecretStr` — access via `.get_secret_value()` only in the code that needs it, never in logs. |
| Catching `Exception` without re-raising a clean HTTP response | Information leakage. Always log the full traceback server-side and return only `{"detail": "Internal server error"}` to the client. |

### Guardrails Architecture

Every POST /api/v1/build request flows through three guardrail layers:

```
Request
  │
  ▼
[InputGuardrail]  ← backend/app/security/guardrails.py
  │  • Scope check: hardware keyword allowlist
  │  • Toxicity/abuse blocklist
  │  • Budget sanity (€50–€100,000)
  │  • Duplicate flooding (SHA-256 hash + TTLCache)
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
  │  • Price sanity (strip ≤0 or >€50k; warn if >150% budget)
  │  • PII strip from text (phone, email, external URLs)
  │
  ▼ (clean)
Client
```

All guardrail events are emitted via `backend/app/security/events.py` as
structured JSON at WARNING level to the `security.events` logger.

### Affiliate URL Allowlist

Only URLs from these hosts are permitted (backend + frontend):

| Store | Allowed hosts |
|-------|--------------|
| Amazon.de | `amazon.de`, `www.amazon.de` |
| ComputerUniverse | `computeruniverse.net`, `www.computeruniverse.net` |
| Caseking | `caseking.de`, `www.caseking.de` |

Backend: `backend/app/models/builder.py:_ALLOWED_AFFILIATE_HOSTS`
Backend output guard: `backend/app/security/output_guard.py:_AFFILIATE_ALLOWED_HOSTS`
Frontend: `frontend/src/lib/url.ts:ALLOWED_AFFILIATE_HOSTS`

All three lists must be kept in sync when stores change.

### Guardrail Event Log Format

Every block/warn/strip emits a JSON line at `WARNING` level:

```json
{
  "timestamp": "2026-03-13T12:00:00.000000+00:00",
  "ip": "1.2.3.4",
  "guardrail": "InputGuardrail",
  "action": "blocked",
  "reason": "Duplicate request detected. Please wait before resubmitting."
}
```

`action` values: `"blocked"` | `"warned"` | `"stripped"`

### How to Run Security Tools

```bash
# Dependency vulnerability scan (run after every uv lock)
cd backend && uv run pip-audit

# Linter + formatter
cd backend && uv run ruff check app/
cd backend && uv run ruff format --check app/

# Full test suite
cd backend && uv run pytest
```

### Rate Limits (configurable via env vars)

| Endpoint | Default | Env var |
|----------|---------|---------|
| POST /api/v1/build | 10/minute | `RATE_LIMIT_BUILD` |
| GET /api/v1/build/{id} | 60/minute | `RATE_LIMIT_READ` |
| POST /api/v1/search | 20/minute | `RATE_LIMIT_SEARCH` |

Format: `"N/period"` where period is `second`, `minute`, `hour`, or `day`.

### Secrets

- `ANTHROPIC_API_KEY` and `DATABASE_URL` are `SecretStr` in `config.py`
- Never log these values — log `"set"` / `"unset"` as a boolean indicator
- Never commit `.env` files — only `.env.example` with placeholders

---

## Code Review

The PR review skill lives at `.claude/skills/pccoach-pr-reviewer/SKILL.md`.
Claude Code loads it automatically when assigned as a GitHub reviewer or asked to review a PR.
Do not freeform review without loading the skill first.
