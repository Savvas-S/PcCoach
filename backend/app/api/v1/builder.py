import logging
import secrets
from collections import OrderedDict

import anthropic
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.limiter import limiter
from app.models.builder import BuildRequest, BuildResult, BuildStatus
from app.services.claude import get_claude_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/build", tags=["build"])

# In-memory store with LRU eviction — will be replaced with DB.
# LRU ensures the least recently accessed build is evicted first, so shared links
# pointing to a build that was just visited are not the first to go.
_builds: OrderedDict[str, BuildResult] = OrderedDict()
_MAX_BUILDS = 500


@router.post("", response_model=BuildResult, status_code=201)
@limiter.limit("10/hour")
async def create_build(request: Request, payload: BuildRequest) -> BuildResult:
    build_id = secrets.token_urlsafe(8)

    try:
        claude = get_claude_service()
        components, summary, upgrade_suggestion, downgrade_suggestion = await claude.generate_build(payload)
        build = BuildResult(
            id=build_id,
            components=components,
            summary=summary,
            upgrade_suggestion=upgrade_suggestion,
            downgrade_suggestion=downgrade_suggestion,
            status=BuildStatus.completed,
        )
    except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
        log.warning("Claude API unavailable: goal=%s budget=%s error=%s", payload.goal, payload.budget_range, e)
        raise HTTPException(status_code=502, detail="Failed to generate build. Please try again.")
    except (ValidationError, ValueError) as e:
        log.error("Invalid Claude response structure: goal=%s budget=%s error=%s", payload.goal, payload.budget_range, e)
        raise HTTPException(status_code=502, detail="Failed to generate build. Please try again.")
    except Exception:
        log.exception("Unexpected error generating build: goal=%s budget=%s", payload.goal, payload.budget_range)
        raise HTTPException(status_code=502, detail="Failed to generate build. Please try again.")

    _builds[build_id] = build
    if len(_builds) > _MAX_BUILDS:
        _builds.popitem(last=False)  # evict least recently accessed

    log.info(
        "Build generated: id=%s goal=%s budget=%s components=%d",
        build_id, payload.goal.value, payload.budget_range.value, len(components),
    )
    return build


@router.get("/{build_id}", response_model=BuildResult)
@limiter.limit("120/minute")
async def get_build(request: Request, build_id: str) -> BuildResult:
    build = _builds.get(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    _builds.move_to_end(build_id)  # mark as recently accessed — defer eviction
    return build
