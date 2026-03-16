.PHONY: help build up down down-clean dev dev-build dev-deploy dev-down logs logs-backend logs-frontend logs-size \
        shell-backend shell-frontend test lint lock deploy init sync-config migrate seed

help:
	@echo "PcCoach - Available commands:"
	@echo ""
	@echo "  make build            Build production Docker images"
	@echo "  make up               Start production containers (detached)"
	@echo "  make down             Stop containers, keep volumes (data preserved)"
	@echo "  make down-clean       Stop containers AND delete volumes (data lost — irreversible)"
	@echo ""
	@echo "  make dev              Start dev environment with hot reload"
	@echo "  make dev-build        Rebuild dev Docker images"
	@echo "  make dev-deploy       Build, migrate, and start dev containers (detached)"
	@echo "  make dev-down         Stop dev containers (data preserved)"
	@echo ""
	@echo "  make logs             Tail logs from all containers"
	@echo "  make logs-backend     Tail backend logs only"
	@echo "  make logs-frontend    Tail frontend logs only"
	@echo "  make logs-size        Show Docker log file sizes per container"
	@echo ""
	@echo "  make shell-backend    Open shell in backend container"
	@echo "  make shell-frontend   Open shell in frontend container"
	@echo ""
	@echo "  make init             Copy .env.example to .env (skips if .env already exists)"
	@echo "  make sync-config      Copy shared/budget_goals.json to all service directories"
	@echo "  make deploy           Pull latest, migrate, seed, restart production containers"
	@echo "  make migrate          Run pending Alembic migrations (dev)"
	@echo "  make seed             Seed component catalog (dev)"
	@echo "  make seed-prod        Seed component catalog (production)"
	@echo "  make test             Run backend tests"
	@echo "  make lint             Run backend linters"
	@echo "  make lock             Generate/update uv.lock and package-lock.json"

# --- Production ---

build: sync-config
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

down-clean:
	@echo "WARNING: this will delete all volumes including the database. Press Ctrl+C to cancel."
	@python3 -c "import time; time.sleep(5)"
	docker compose down -v

# --- Development ---

dev: sync-config
	docker compose -f docker-compose.dev.yml up

dev-build: sync-config
	docker compose -f docker-compose.dev.yml build

dev-deploy: sync-config
	docker compose -f docker-compose.dev.yml build
	docker compose -f docker-compose.dev.yml run --rm backend uv run alembic upgrade head
	docker compose -f docker-compose.dev.yml up -d

dev-down:
	docker compose -f docker-compose.dev.yml down

# --- Logs ---

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

logs-size:
	@du -sh $$(docker inspect --format='{{.LogPath}}' pccoach-backend-1 pccoach-frontend-1 pccoach-db-1 pccoach-telegram-bot-1 2>/dev/null)

# --- Shells ---

shell-backend:
	docker compose exec backend /bin/bash

shell-frontend:
	docker compose exec frontend /bin/sh

# --- Database ---

migrate:
	docker compose -f docker-compose.dev.yml exec backend uv run alembic upgrade head

seed:
	docker compose -f docker-compose.dev.yml exec backend uv run python -m app.db.seed

seed-prod:
	docker compose exec backend uv run python -m app.db.seed

# --- Quality ---

test:
	docker compose -f docker-compose.dev.yml exec backend uv run pytest

lint:
	docker compose -f docker-compose.dev.yml exec backend uv run ruff check .
	docker compose -f docker-compose.dev.yml exec backend uv run ruff format --check .

# --- Config ---

sync-config:
	## Propagate shared/budget_goals.json to all service directories.
	## Run this after editing shared/budget_goals.json.
	@python3 -m json.tool shared/budget_goals.json > /dev/null \
		|| (echo "ERROR: shared/budget_goals.json is not valid JSON — aborting sync" && exit 1)
	cp shared/budget_goals.json backend/app/budget_goals.json
	cp shared/budget_goals.json frontend/src/lib/budget_goals.json
	cp shared/budget_goals.json telegram_bot/budget_goals.json

# --- Init ---

init:
	@[ -f backend/.env ] || (cp backend/.env.example backend/.env && echo "created backend/.env")
	@[ -f frontend/.env ] || (cp frontend/.env.example frontend/.env && echo "created frontend/.env")
	@[ -f telegram_bot/.env ] || (cp telegram_bot/.env.example telegram_bot/.env && echo "created telegram_bot/.env")

# --- Deploy ---

deploy:
	git pull --rebase origin master
	$(MAKE) sync-config
	docker compose build
	docker compose run --rm backend uv run alembic upgrade head
	docker compose up -d
	docker compose exec backend uv run python -m app.db.seed

# --- Dependencies ---

lock:
	cd backend && uv lock
	cd telegram_bot && uv lock
	docker run --rm -v $(CURDIR)/frontend:/app -w /app node:20-alpine npm install --package-lock-only
