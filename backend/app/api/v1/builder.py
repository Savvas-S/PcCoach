from fastapi import APIRouter, HTTPException

from app.models.builder import BuildRequest, BuildResult, BuildStatus

router = APIRouter(prefix="/build", tags=["build"])

# In-memory store — will be replaced with DB
_builds: dict[int, BuildResult] = {}
_next_id = 1


@router.post("", response_model=BuildResult, status_code=201)
async def create_build(payload: BuildRequest) -> BuildResult:
    """Submit build requirements — Claude will generate recommendations (coming soon)."""
    global _next_id
    build = BuildResult(id=_next_id, request=payload, status=BuildStatus.pending)
    _builds[_next_id] = build
    _next_id += 1
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
