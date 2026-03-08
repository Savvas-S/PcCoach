.PHONY: help build up down dev dev-build dev-down logs logs-backend logs-frontend \
        shell-backend shell-frontend test lint lock deploy init

help:
	@echo "PcCoach - Available commands:"
	@echo ""
	@echo "  make build            Build production Docker images"
	@echo "  make up               Start production containers (detached)"
	@echo "  make down             Stop and remove containers"
	@echo ""
	@echo "  make dev              Start dev environment with hot reload"
	@echo "  make dev-build        Rebuild dev Docker images"
	@echo "  make dev-down         Stop dev containers"
	@echo ""
	@echo "  make logs             Tail logs from all containers"
	@echo "  make logs-backend     Tail backend logs only"
	@echo "  make logs-frontend    Tail frontend logs only"
	@echo ""
	@echo "  make shell-backend    Open shell in backend container"
	@echo "  make shell-frontend   Open shell in frontend container"
	@echo ""
	@echo "  make init             Copy .env.example to .env (skips if .env already exists)"
	@echo "  make deploy           Pull latest changes and restart production containers"
	@echo "  make test             Run backend tests"
	@echo "  make lint             Run backend linters"
	@echo "  make lock             Generate/update uv.lock and package-lock.json"

# --- Production ---

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

# --- Development ---

dev:
	docker compose -f docker-compose.dev.yml up

dev-build:
	docker compose -f docker-compose.dev.yml build

dev-down:
	docker compose -f docker-compose.dev.yml down

# --- Logs ---

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

# --- Shells ---

shell-backend:
	docker compose exec backend /bin/bash

shell-frontend:
	docker compose exec frontend /bin/sh

# --- Quality ---

test:
	docker compose -f docker-compose.dev.yml exec backend uv run pytest

lint:
	docker compose -f docker-compose.dev.yml exec backend uv run ruff check .
	docker compose -f docker-compose.dev.yml exec backend uv run ruff format --check .

# --- Init ---

init:
	@[ -f backend/.env ] || (cp backend/.env.example backend/.env && echo "created backend/.env")
	@[ -f frontend/.env ] || (cp frontend/.env.example frontend/.env && echo "created frontend/.env")
	@[ -f telegram_bot/.env ] || (cp telegram_bot/.env.example telegram_bot/.env && echo "created telegram_bot/.env")

# --- Deploy ---

deploy:
	git pull --rebase origin master
	docker compose build
	docker compose up -d

# --- Dependencies ---

lock:
	cd backend && uv lock
	cd telegram_bot && uv lock
	docker run --rm -v $(CURDIR)/frontend:/app -w /app node:20-alpine npm install --package-lock-only
