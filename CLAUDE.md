# PcCoach — Claude Code Guide

## Project Overview

PcCoach is an AI-powered PC building assistant. Users describe their needs and budget; the app recommends components. It is built from scratch and actively in development.

## Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| Backend   | Python 3.12, FastAPI, Anthropic SDK             |
| Frontend  | Next.js 15, React 19, TypeScript, Tailwind CSS  |
| AI        | Claude (`claude-sonnet-4-6`) via `ClaudeService`|
| Dev tools | uv (package manager), ruff (lint/format), pytest|
| Runtime   | Docker + Docker Compose                         |

## Project Structure

```
PcCoach/
├── backend/
│   ├── app/
│   │   ├── api/v1/router.py      # API routes
│   │   ├── services/claude.py    # Claude integration
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   └── main.py               # FastAPI app + CORS
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   └── src/app/                  # Next.js App Router
├── docker-compose.yml            # Production
├── docker-compose.dev.yml        # Development (hot reload)
└── Makefile                      # Common commands
```

## Common Commands

```bash
make dev          # Start dev environment (hot reload)
make dev-build    # Rebuild dev images
make lock         # Regenerate uv.lock  (requires uv installed locally)
make test         # Run pytest in backend container
make lint         # Run ruff check + format check
make logs         # Tail all container logs
```

## Backend Conventions

- **Package manager**: `uv` only — never use pip directly
- **Linter/formatter**: `ruff` (line length 88, Python 3.12 target)
- **Settings**: all config via environment variables, loaded through `app/config.py` (`pydantic-settings`)
- **API versioning**: routes live under `/api/v1/`
- **Claude model**: `claude-sonnet-4-6` — do not downgrade without discussion
- **Async**: use `async def` for all route handlers and service methods

## Frontend Conventions

- Next.js App Router (no Pages Router)
- TypeScript strict mode
- Tailwind CSS for styling — no CSS-in-JS

## Environment Variables

Backend (`.env` in `backend/`):
```
ANTHROPIC_API_KEY=...
CORS_ORIGINS=["http://localhost:3000"]
ENVIRONMENT=development
```

Frontend (`.env` in `frontend/`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Key Files

- `backend/app/services/claude.py` — Claude client, `chat()` method, singleton via `lru_cache`
- `backend/app/config.py` — all settings, app fails to start without `ANTHROPIC_API_KEY`
- `backend/app/main.py` — CORS is tighter in production (`environment=production`)

## Notes for Claude Code

- This project is early-stage; the API surface is minimal by design
- Do not add abstraction layers unless clearly needed
- Prefer editing existing files over creating new ones
- Always use `uv run` inside containers, never bare `python` or `pip`
- Do not commit `.env` files
