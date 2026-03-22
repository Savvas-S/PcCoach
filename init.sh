#!/usr/bin/env bash
# init.sh — Startup health check for PcCoach dev environment.
# Run this at the start of every Claude session.
# Exits with code 1 if anything fails so Claude knows not to proceed.

set -euo pipefail

BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:3000"
HEALTH_ENDPOINT="$BACKEND_URL/health"
MAX_WAIT=90  # seconds to wait for services

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

fail() { echo -e "${RED}FAIL: $1${NC}"; exit 1; }
pass() { echo -e "${GREEN}PASS: $1${NC}"; }
info() { echo -e "${YELLOW}INFO: $1${NC}"; }

# ------------------------------------------------------------------
# Step 1: Ensure Docker is running
# ------------------------------------------------------------------
if ! docker info > /dev/null 2>&1; then
  fail "Docker is not running"
fi

# ------------------------------------------------------------------
# Step 2: Start dev containers if not already running
# ------------------------------------------------------------------
BACKEND_RUNNING=$(docker compose -f docker-compose.dev.yml ps --status running --format json 2>/dev/null | grep -c '"backend"' || true)
if [ "$BACKEND_RUNNING" -eq 0 ]; then
  info "Dev containers not running — starting with docker compose..."
  make sync-config 2>/dev/null || true
  docker compose -f docker-compose.dev.yml up -d --build
  info "Waiting for containers to start..."
  sleep 5
fi

# ------------------------------------------------------------------
# Step 3: Wait for backend health endpoint
# ------------------------------------------------------------------
info "Polling backend health at $HEALTH_ENDPOINT ..."
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_ENDPOINT" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    pass "Backend healthy (${ELAPSED}s)"
    break
  fi
  sleep 3
  ELAPSED=$((ELAPSED + 3))
done
if [ $ELAPSED -ge $MAX_WAIT ]; then
  fail "Backend did not become healthy within ${MAX_WAIT}s"
fi

# ------------------------------------------------------------------
# Step 4: Wait for frontend
# ------------------------------------------------------------------
info "Polling frontend at $FRONTEND_URL ..."
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    pass "Frontend healthy (${ELAPSED}s)"
    break
  fi
  sleep 3
  ELAPSED=$((ELAPSED + 3))
done
if [ $ELAPSED -ge $MAX_WAIT ]; then
  fail "Frontend did not become healthy within ${MAX_WAIT}s"
fi

# ------------------------------------------------------------------
# Step 5: Run database migration check
# ------------------------------------------------------------------
info "Checking database migrations..."
docker compose -f docker-compose.dev.yml exec -T backend uv run alembic upgrade head 2>/dev/null \
  && pass "Migrations up to date" \
  || fail "Migration check failed"

# ------------------------------------------------------------------
# Step 6: Smoke test — hit the build endpoint with a minimal request
# ------------------------------------------------------------------
info "Smoke test: POST /api/v1/build ..."
SMOKE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BACKEND_URL/api/v1/build" \
  -H "Content-Type: application/json" \
  -d '{"goal":"mid_range_gaming","budget_range":"1000_1500"}' \
  --max-time 10 2>/dev/null || echo -e "\n000")

SMOKE_BODY=$(echo "$SMOKE_RESPONSE" | head -n -1)
SMOKE_STATUS=$(echo "$SMOKE_RESPONSE" | tail -n 1)

# Accept 200 (SSE stream started) or 429 (rate limited) as valid — both mean the app is working
if [ "$SMOKE_STATUS" = "200" ] || [ "$SMOKE_STATUS" = "429" ]; then
  pass "Smoke test returned HTTP $SMOKE_STATUS — app is responding"
else
  # Also accept cached results or any 2xx
  case "$SMOKE_STATUS" in
    2*) pass "Smoke test returned HTTP $SMOKE_STATUS — app is responding" ;;
    *)  fail "Smoke test returned HTTP $SMOKE_STATUS (expected 200 or 429). Body: $SMOKE_BODY" ;;
  esac
fi

# ------------------------------------------------------------------
# Step 7: Run backend tests
# ------------------------------------------------------------------
info "Running backend tests..."
docker compose -f docker-compose.dev.yml exec -T backend uv run pytest -x --tb=short 2>&1 \
  && pass "All backend tests pass" \
  || fail "Backend tests failed"

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  PASS — PcCoach dev environment is healthy ${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Backend:  $BACKEND_URL"
echo "Frontend: $FRONTEND_URL"
echo "Health:   $HEALTH_ENDPOINT"
exit 0
