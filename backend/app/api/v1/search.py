from fastapi import APIRouter, HTTPException

from app.models.builder import ComponentSearchRequest, ComponentSearchResult
from app.services.claude import get_claude_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=ComponentSearchResult, status_code=200)
async def search_component(payload: ComponentSearchRequest) -> ComponentSearchResult:
    try:
        claude = get_claude_service()
        return await claude.search_component(payload)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to find component. Please try again.")
