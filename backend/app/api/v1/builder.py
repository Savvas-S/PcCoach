import logging
import secrets

from fastapi import APIRouter, HTTPException, Request

from app.limiter import limiter
from app.models.builder import BuildRequest, BuildResult, BuildStatus
from app.services.claude import get_claude_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/build", tags=["build"])

# In-memory store — will be replaced with DB
_builds: dict[str, BuildResult] = {}
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
    except Exception:
        log.exception("Failed to generate build for request: goal=%s budget=%s", payload.goal, payload.budget_range)
        raise HTTPException(status_code=502, detail="Failed to generate build. Please try again.")

    _builds[build_id] = build
    if len(_builds) > _MAX_BUILDS:
        del _builds[next(iter(_builds))]
    return build


@router.get("/{build_id}", response_model=BuildResult)
async def get_build(build_id: str) -> BuildResult:
    build = _builds.get(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return build
