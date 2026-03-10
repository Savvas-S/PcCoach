import logging

from fastapi import APIRouter, HTTPException, Request

from app.limiter import limiter
from app.models.builder import ComponentSearchRequest, ComponentSearchResult
from app.services.claude import get_claude_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=ComponentSearchResult, status_code=200)
@limiter.limit("20/hour")
async def search_component(request: Request, payload: ComponentSearchRequest) -> ComponentSearchResult:
    try:
        claude = get_claude_service()
        return await claude.search_component(payload)
    except Exception:
        log.exception("Failed to search component: category=%s", payload.category)
        raise HTTPException(status_code=502, detail="Failed to find component. Please try again.")
