# PcCoach — Database Guide

## Overview

PcCoach uses **PostgreSQL 16** as its database, running as a Docker service alongside
the backend. The database currently serves one purpose: **persisting generated builds**
so that identical requests are served from cache instead of calling Claude again.

The stack is:

| Layer | Technology |
|---|---|
| Database | PostgreSQL 16 (Alpine image) |
| ORM | SQLAlchemy 2 (async) |
| Driver | asyncpg |
| Migrations | Alembic |
| Session scope | Per-request (FastAPI `Depends`) |

---

## Architecture

### How the DB fits into a request

```
POST /api/v1/build
        │
        ▼
[InputGuardrail]          ← blocks bad/duplicate/off-topic requests
        │
        ▼
DB lookup by request_hash ← returns cached BuildResult instantly if found
        │ (cache miss)
        ▼
[ClaudeService]           ← calls Claude API (5–20s)
        │
        ▼
[OutputGuardrail]         ← validates and sanitises Claude's response
        │
        ▼
DB INSERT (id, hash, result)
        │
        ▼
Response to client
```

The `request_hash` is a SHA-256 of the raw request body. If two users submit
identical inputs, the second request returns the first result instantly without
calling Claude. If two identical requests arrive simultaneously (race condition),
the `UNIQUE` constraint on `request_hash` ensures only one result is stored —
the loser rolls back and re-reads the winner's row.

### Session lifecycle

`get_db()` in `app/database.py` is a FastAPI dependency that opens an
`AsyncSession` for the duration of a single request and closes it automatically
when the response is sent. Sessions are never shared between requests.

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        yield session
```

The engine is created once at startup via `init_db()`, called from
`app/main.py`'s lifespan handler. If `DATABASE_URL` is not set, startup fails
immediately with a clear error — the app never reaches a broken state.

---

## Schema

### Table: `builds`

```sql
CREATE TABLE builds (
    id           VARCHAR(16)               PRIMARY KEY,
    request_hash VARCHAR(64)  NOT NULL UNIQUE,
    result       JSONB        NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

| Column | Type | Description |
|---|---|---|
| `id` | `VARCHAR(16)` | URL-safe random ID (`secrets.token_urlsafe(8)` → 11 chars max). Used in share links: `/build/{id}` |
| `request_hash` | `VARCHAR(64)` | SHA-256 hex of the raw request body. Uniquely identifies a set of build inputs. Used as cache key. |
| `result` | `JSONB` | Full serialised `BuildResult` Pydantic model (`model_dump(mode="json")`). Deserialised on read via `BuildResult.model_validate()`. |
| `created_at` | `TIMESTAMPTZ` | Set by PostgreSQL at INSERT time via `DEFAULT now()`. |

**Indexes:**
- `PRIMARY KEY` on `id` — used by `GET /api/v1/build/{id}`
- `UNIQUE` on `request_hash` — enforces deduplication and implicitly creates a B-tree index used by the cache lookup

---

## Files

```
backend/
├── app/
│   ├── database.py              # Engine, session factory, Base, get_db(), init_db()
│   └── db/
│       └── models.py            # SQLAlchemy ORM model: Build
├── alembic.ini                  # Alembic config (URL is set programmatically)
└── alembic/
    ├── env.py                   # Async migration runner, reads DATABASE_URL from env
    ├── script.py.mako           # Template for new migration files
    └── versions/
        └── 0001_initial.py      # Creates the builds table
```

### `app/database.py`
Owns the engine and session factory. Both are module-level globals initialised
lazily by `init_db()` so that importing the module never fails even if
`DATABASE_URL` is not yet available (e.g. during test collection).

### `app/db/models.py`
Contains the `Build` SQLAlchemy ORM model. This is separate from
`app/models/builder.py` which contains the Pydantic models (`BuildResult`,
`BuildRequest`, etc.). Keep them separate — ORM models describe the DB schema,
Pydantic models describe API shapes.

### `alembic/env.py`
Reads `DATABASE_URL` from `app/config.settings` and sets it on the Alembic
config at runtime. Uses an async engine (`async_engine_from_config`) with
`NullPool` so that migrations don't hold idle connections open.

---

## Environment Variables

| Variable | Where set | Description |
|---|---|---|
| `DATABASE_URL` | `backend/.env` | Full asyncpg connection string. **Required** — startup fails without it. |
| `POSTGRES_PASSWORD` | Shell / droplet environment | Password for the `db` Docker service. Must match the password in `DATABASE_URL`. |

### Development (docker-compose.dev.yml)
The dev compose hardcodes `POSTGRES_PASSWORD=pccoach`, so your local
`backend/.env` should use:
```
DATABASE_URL=postgresql+asyncpg://pccoach:pccoach@db:5432/pccoach
```

### Production (docker-compose.yml)
The prod compose requires `POSTGRES_PASSWORD` to be set in the shell
environment on the droplet (never in a committed file):
```bash
export POSTGRES_PASSWORD=<strong-random-password>
```
Your `backend/.env` on the droplet should use the same password:
```
DATABASE_URL=postgresql+asyncpg://pccoach:<strong-random-password>@db:5432/pccoach
```

---

## Migrations

Migrations are managed with **Alembic**. Every schema change must go through a
migration file — never edit the DB schema manually.

### How migrations work

1. You change `app/db/models.py` (add a column, new table, etc.)
2. You generate a migration file with `alembic revision --autogenerate`
3. Alembic compares the ORM metadata against the live DB and writes the diff
4. You review the generated file in `alembic/versions/`
5. You apply it with `alembic upgrade head`

Alembic tracks applied migrations in a `alembic_version` table it manages
automatically.

---

## Command Reference

### First-time setup

```bash
# 1. Copy env file and fill in your values
make init

# 2. Start the dev environment (brings up db + backend + frontend)
make dev

# 3. In a second terminal, run the initial migration to create the builds table
make migrate
```

---

### Running migrations

```bash
# Apply all pending migrations (run this after every pull that adds migration files)
make migrate

# Same command manually (inside backend container)
docker compose -f docker-compose.dev.yml exec backend uv run alembic upgrade head

# Check current migration state
docker compose -f docker-compose.dev.yml exec backend uv run alembic current

# View migration history
docker compose -f docker-compose.dev.yml exec backend uv run alembic history --verbose
```

---

### Creating a new migration

```bash
# 1. Edit app/db/models.py to reflect your schema change

# 2. Generate the migration (autogenerate compares models vs live DB)
docker compose -f docker-compose.dev.yml exec backend \
    uv run alembic revision --autogenerate -m "your description here"

# 3. Review the generated file in backend/alembic/versions/ before applying

# 4. Apply it
make migrate
```

> Always review autogenerated files before applying. Alembic cannot detect
> all changes (e.g. renamed columns, changed constraints) — check the diff
> manually.

---

### Rolling back a migration

```bash
# Roll back the last applied migration
docker compose -f docker-compose.dev.yml exec backend uv run alembic downgrade -1

# Roll back to a specific revision
docker compose -f docker-compose.dev.yml exec backend uv run alembic downgrade <revision_id>

# Roll back everything (empty DB — use with caution)
docker compose -f docker-compose.dev.yml exec backend uv run alembic downgrade base
```

---

### Inspecting the database directly

```bash
# Open a psql shell (dev only — port 5432 is exposed)
docker compose -f docker-compose.dev.yml exec db psql -U pccoach -d pccoach

# Or connect from your host machine with any PostgreSQL client:
# host: localhost, port: 5432, user: pccoach, password: pccoach, db: pccoach
```

Useful psql commands once inside:
```sql
-- List tables
\dt

-- Inspect the builds table
\d builds

-- Count stored builds
SELECT COUNT(*) FROM builds;

-- View the 5 most recent builds
SELECT id, request_hash, created_at FROM builds ORDER BY created_at DESC LIMIT 5;

-- View a build's full result JSON
SELECT result FROM builds WHERE id = '<build_id>';

-- Clear all cached builds (useful during development)
TRUNCATE builds;
```

---

### Production migrations

On the droplet, just run:

```bash
make deploy
```

This pulls latest code, rebuilds images, runs migrations in a temporary
container (`docker compose run --rm`), then starts everything. The migration
step automatically waits for the `db` service to be healthy before executing.

If you need to run migrations manually outside of `make deploy`:

```bash
docker compose run --rm backend uv run alembic upgrade head
```

Use `run --rm` (not `exec`) — `exec` requires a running backend container,
which may not exist during a fresh deploy or after `docker compose down`.

---

## Health Check

The `/health` endpoint verifies DB connectivity on every call:

```python
@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
```

Docker Compose uses this to determine if the backend is ready. If the DB is
down or unreachable, `/health` will return 500 and dependent services
(frontend, telegram-bot) will not start.

---

## Adding a New Table

1. Create the ORM model in `app/db/models.py` (or a new file in `app/db/`)
2. Import it in `alembic/env.py` so Alembic sees it:
   ```python
   from app.db import models  # noqa: F401
   ```
   If you add a second file, import it here too:
   ```python
   from app.db import models, my_new_models  # noqa: F401
   ```
3. Generate and apply the migration (see above)
4. Update this document if the new table changes the data architecture

---

## Decisions & Rationale

| Decision | Reason |
|---|---|
| PostgreSQL in Docker (not managed) | PcCoach is early-stage — no need for managed DB cost/complexity yet. Migrate to DigitalOcean Managed PostgreSQL when uptime SLAs matter. |
| JSONB for `result` | The `BuildResult` shape evolves frequently. JSONB avoids schema migrations for every Pydantic model change while still allowing indexed queries on nested fields if needed later. |
| SHA-256 of raw request body as cache key | Stable, collision-resistant, and reuses the hash already computed by `InputGuardrail` for flood detection. |
| `asyncpg` driver | Required for SQLAlchemy async support. Significantly faster than `psycopg2` for I/O-bound workloads. |
| `NullPool` in Alembic | Migrations are short-lived CLI processes. `NullPool` ensures connections are closed immediately after the migration completes. |
