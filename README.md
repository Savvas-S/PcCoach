# PcCoach

AI-powered PC build recommendation tool for the Cyprus market. Users describe their needs and budget; Claude recommends the best components with affiliate links to buy them. Revenue is generated through affiliate commissions — no inventory, no orders, no fulfilment.

## Stack

- **Backend:** Python 3.12 + FastAPI
- **AI:** Claude `claude-sonnet-4-6` (Anthropic)
- **Frontend:** Next.js 15 (React 19, TypeScript, Tailwind CSS)
- **Hosting:** AWS / DigitalOcean

## How It Works

1. User selects their goal, budget, and preferences
2. Claude generates a tailored component list
3. Each component includes an affiliate link (Skroutz CY, Amazon)
4. User buys directly from the store — you earn the commission

## Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- [uv](https://docs.astral.sh/uv/) (for local backend development without Docker)

## Getting Started

### 1. Copy environment files

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Fill in your `ANTHROPIC_API_KEY` in `backend/.env` when ready to enable AI features.

### 2. Development (hot reload)

```bash
make dev-build   # first time only
make dev
```

### 3. Production

```bash
make build
make up
```

## Services

| Service    | URL                        |
|------------|----------------------------|
| Backend    | http://localhost:8000      |
| Frontend   | http://localhost:3000      |
| API Docs   | http://localhost:8000/docs |

## API

| Method | Endpoint            | Description                  |
|--------|---------------------|------------------------------|
| POST   | `/api/v1/build`     | Submit build requirements    |
| GET    | `/api/v1/build`     | List all builds              |
| GET    | `/api/v1/build/{id}`| Get a build by ID            |

## Common Commands

```bash
make help           # Show all available commands
make dev            # Start dev environment with hot reload
make dev-build      # Rebuild dev images
make up             # Start production containers
make down           # Stop containers
make logs           # Tail logs from all services
make shell-backend  # Open shell in backend container
make test           # Run backend tests
make lint           # Run linters
make lock           # Regenerate uv.lock and package-lock.json
```
