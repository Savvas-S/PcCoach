# PcCoach — Claude Code Guide

## Project Overview

PcCoach is an AI-powered PC build recommendation tool for the Cyprus market (Limassol).
Users describe their needs and budget; Claude recommends a full component list with affiliate links to buy each part.
Revenue model: affiliate commissions (Skroutz CY, Amazon) — no inventory, no ordering, no services.

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
               → User clicks affiliate link → buys on Skroutz/Amazon
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
NEXT_PUBLIC_API_URL=http://localhost:8000
```

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
