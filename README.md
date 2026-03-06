# PcCoach

AI-powered PC building assistant. Helps customers choose the right components based on their requirements and budget.

## Stack

- **Backend:** Python 3.12 + FastAPI
- **AI:** Claude (Anthropic)
- **Frontend:** Next.js 15 (React)
- **Database:** TBD
- **Hosting:** AWS / DigitalOcean

## Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- [uv](https://docs.astral.sh/uv/) (for local backend development without Docker)
- [Node.js 20+](https://nodejs.org/) (for local frontend development without Docker)

## Getting Started

### 1. Copy environment files

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Fill in your `ANTHROPIC_API_KEY` in `backend/.env`.

### 2. Development (hot reload)

```bash
make dev
```

### 3. Production

```bash
make build
make up
```

## Services

| Service  | URL                        |
|----------|----------------------------|
| Backend  | http://localhost:8000      |
| Frontend | http://localhost:3000      |
| API Docs | http://localhost:8000/docs |

## Common Commands

```bash
make help           # Show all available commands
make dev            # Start dev environment with hot reload
make up             # Start production containers
make down           # Stop containers
make logs           # Tail logs from all services
make shell-backend  # Open shell in backend container
make test           # Run backend tests
make lint           # Run linters
```
