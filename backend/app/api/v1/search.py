import logging

import anthropic
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

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
    except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
        log.warning("Claude API unavailable: category=%s error=%s", payload.category, e)
        raise HTTPException(status_code=502, detail="Failed to find component. Please try again.")
    except (ValidationError, ValueError) as e:
        log.error("Invalid Claude response structure: category=%s error=%s", payload.category, e)
        raise HTTPException(status_code=502, detail="Failed to find component. Please try again.")
    except Exception:
        log.exception("Unexpected error searching component: category=%s", payload.category)
        raise HTTPException(status_code=502, detail="Failed to find component. Please try again.")
