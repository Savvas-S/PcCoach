import logging
import secrets
from collections import OrderedDict

import anthropic
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.config import settings
from app.limiter import limiter
from app.models.builder import BuildRequest, BuildResult
from app.security import events as guardrail_events
from app.security.guardrails import hash_request_body, input_guardrail
from app.services.claude import get_claude_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/build", tags=["build"])

# In-memory store with LRU eviction — will be replaced with DB.
# LRU ensures the least recently accessed build is evicted first, so shared links
# pointing to a build that was just visited are not the first to go.
_builds: OrderedDict[str, BuildResult] = OrderedDict()
_MAX_BUILDS = 500


@router.post("", response_model=BuildResult, status_code=201)
@limiter.limit(lambda: settings.rate_limit_build)
async def create_build(request: Request, payload: BuildRequest) -> BuildResult:
    # ------------------------------------------------------------------
    # Input guardrails — run before any Claude call
    # ------------------------------------------------------------------
    client_ip = request.client.host if request.client else "unknown"
    raw_body = await request.body()
    body_hash = hash_request_body(raw_body)

    guard_result = input_guardrail.check(
        notes=payload.notes,
        budget_range=payload.budget_range,
        client_ip=client_ip,
        body_hash=body_hash,
    )
    if not guard_result.allowed:
        guardrail_events.emit(
            ip=client_ip,
            guardrail_name="InputGuardrail",
            action_taken="blocked",
            reason=guard_result.reason,
        )
        status = 429 if "Duplicate" in guard_result.reason else 400
        raise HTTPException(status_code=status, detail=guard_result.reason)

    # ------------------------------------------------------------------
    # Claude call
    # ------------------------------------------------------------------
    build_id = secrets.token_urlsafe(8)

    try:
        claude = get_claude_service()
        build = await claude.generate_build(
            payload, build_id=build_id, client_ip=client_ip
        )
    except anthropic.APITimeoutError as e:
        log.warning("Claude API timed out: goal=%s budget=%s error=%s", payload.goal, payload.budget_range, e)
        raise HTTPException(status_code=504, detail="The AI took too long to respond. Please try again.")
    except anthropic.APIConnectionError as e:
        log.warning("Claude API unreachable: goal=%s budget=%s error=%s", payload.goal, payload.budget_range, e)
        raise HTTPException(status_code=502, detail="Could not reach the AI service. Please try again.")
    except anthropic.RateLimitError as e:
        log.warning("Claude API rate limit hit: goal=%s budget=%s error=%s", payload.goal, payload.budget_range, e)
        raise HTTPException(status_code=503, detail="The AI service is busy. Please try again in a few minutes.")
    except anthropic.InternalServerError as e:
        log.warning("Claude API overloaded (529): goal=%s budget=%s error=%s", payload.goal, payload.budget_range, e)
        raise HTTPException(status_code=503, detail="The AI service is temporarily overloaded. Please try again in a moment.")
    except (ValidationError, ValueError) as e:
        log.error("Invalid Claude response structure: goal=%s budget=%s error=%s", payload.goal, payload.budget_range, e)
        raise HTTPException(status_code=500, detail="Could not generate a valid recommendation. Please try again.")
    except Exception:
        log.exception("Unexpected error generating build: goal=%s budget=%s", payload.goal, payload.budget_range)
        raise HTTPException(status_code=500, detail="Internal server error")

    _builds[build_id] = build
    if len(_builds) > _MAX_BUILDS:
        _builds.popitem(last=False)  # evict least recently accessed

    log.info(
        "Build generated: id=%s goal=%s budget=%s components=%d",
        build_id, payload.goal.value, payload.budget_range.value, len(build.components),
    )
    return build


@router.get("/{build_id}", response_model=BuildResult)
@limiter.limit(lambda: settings.rate_limit_read)
async def get_build(request: Request, build_id: str) -> BuildResult:
    build = _builds.get(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    _builds.move_to_end(build_id)  # mark as recently accessed — defer eviction
    return build
