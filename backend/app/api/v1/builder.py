from fastapi import APIRouter, HTTPException

from app.models.builder import BuildRequest, BuildResult, BuildStatus
from app.services.claude import get_claude_service

router = APIRouter(prefix="/build", tags=["build"])

# In-memory store — will be replaced with DB
_builds: dict[int, BuildResult] = {}
_next_id = 1
_MAX_BUILDS = 500


@router.post("", response_model=BuildResult, status_code=201)
async def create_build(payload: BuildRequest) -> BuildResult:
    global _next_id
    build_id = _next_id
    _next_id += 1

    try:
        claude = get_claude_service()
        components, summary = await claude.generate_build(payload)
        build = BuildResult(
            id=build_id,
            components=components,
            summary=summary,
            status=BuildStatus.completed,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to generate build: {str(e)}")

    _builds[build_id] = build
    if len(_builds) > _MAX_BUILDS:
        del _builds[min(_builds)]
    return build


@router.get("", response_model=list[BuildResult])
async def list_builds() -> list[BuildResult]:
    return list(_builds.values())


@router.get("/{build_id}", response_model=BuildResult)
async def get_build(build_id: int) -> BuildResult:
    build = _builds.get(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return build
