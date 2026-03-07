from fastapi import APIRouter, HTTPException

from app.models.builder import Build, BuildRequest, BuildStatus

router = APIRouter(prefix="/builder", tags=["builder"])

# In-memory store for now
_builds: dict[int, Build] = {}
_next_id = 1


@router.get("/builds", response_model=list[Build])
async def list_builds() -> list[Build]:
    return list(_builds.values())


@router.post("/builds", response_model=Build, status_code=201)
async def create_build(payload: BuildRequest) -> Build:
    global _next_id
    build = Build(id=_next_id, **payload.model_dump())
    _builds[_next_id] = build
    _next_id += 1
    return build


@router.get("/builds/{build_id}", response_model=Build)
async def get_build(build_id: int) -> Build:
    build = _builds.get(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return build


@router.patch("/builds/{build_id}/status", response_model=Build)
async def update_build_status(build_id: int, status: BuildStatus) -> Build:
    build = _builds.get(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    _builds[build_id] = build.model_copy(update={"status": status})
    return _builds[build_id]
