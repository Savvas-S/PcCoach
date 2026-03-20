import asyncio
import logging

import anthropic
from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.limiter import check_ai_rate_limit, limiter
from app.models.builder import ComponentSearchRequest, ComponentSearchResult
from app.security import events as guardrail_events
from app.security.guardrails import hash_search_request, input_guardrail
from app.services.claude import get_claude_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

# In-memory cache for search results (TTL 30 min, max 128 entries)
_search_cache: TTLCache[str, dict] = TTLCache(maxsize=128, ttl=1800)


def clear_search_cache() -> int:
    """Clear the search cache. Returns the number of evicted entries."""
    n = len(_search_cache)
    _search_cache.clear()
    return n


@router.post("", response_model=ComponentSearchResult, status_code=200)
async def search_component(
    request: Request,
    payload: ComponentSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> ComponentSearchResult:
    client_ip = request.client.host if request.client else "unknown"
    body_hash = hash_search_request(payload)

    # ------------------------------------------------------------------
    # Content guardrails (blocklist) — always run, even for cache hits
    # ------------------------------------------------------------------
    content_result = input_guardrail.check_search_content(
        description=payload.description,
    )
    if not content_result.allowed:
        guardrail_events.emit(
            ip=client_ip,
            guardrail_name="InputGuardrail.search",
            action_taken="blocked",
            reason=content_result.reason,
        )
        raise HTTPException(status_code=400, detail=content_result.reason)

    # ------------------------------------------------------------------
    # Cache check — cached results are free, skip duplicate detection
    # ------------------------------------------------------------------
    cached = _search_cache.get(body_hash)
    if cached:
        log.info("Search cache hit: hash=%s", body_hash[:8])
        return ComponentSearchResult.model_validate(cached)

    # ------------------------------------------------------------------
    # Duplicate detection — only for uncached requests that hit Claude
    # ------------------------------------------------------------------
    guard_result = input_guardrail.check_search_duplicate(
        client_ip=client_ip,
        body_hash=body_hash,
    )
    if not guard_result.allowed:
        guardrail_events.emit(
            ip=client_ip,
            guardrail_name="InputGuardrail.search",
            action_taken="blocked",
            reason=guard_result.reason,
        )
        status = 429 if "Duplicate" in guard_result.reason else 400
        raise HTTPException(status_code=status, detail=guard_result.reason)

    # Rate limit only uncached requests that will call Claude
    check_ai_rate_limit(request)

    # ------------------------------------------------------------------
    # Claude agentic tool loop
    # ------------------------------------------------------------------
    try:
        claude = get_claude_service()
        result = await claude.search_component(payload, db=db, client_ip=client_ip)
    except TimeoutError as e:
        log.warning("Tool loop timeout: category=%s error=%s", payload.category, e)
        raise HTTPException(
            status_code=504, detail="The AI took too long to respond. Please try again."
        )
    except anthropic.APITimeoutError as e:
        log.warning("Claude API timed out: category=%s error=%s", payload.category, e)
        raise HTTPException(
            status_code=504, detail="The AI took too long to respond. Please try again."
        )
    except anthropic.APIConnectionError as e:
        log.warning("Claude API unreachable: category=%s error=%s", payload.category, e)
        raise HTTPException(
            status_code=502, detail="Could not reach the AI service. Please try again."
        )
    except anthropic.AuthenticationError as e:
        log.error(
            "Claude API auth error (key invalid or balance exhausted): category=%s error=%s",
            payload.category,
            e,
        )
        await asyncio.sleep(3)
        raise HTTPException(
            status_code=503,
            detail=(
                "Due to high demand, our AI service is temporarily unavailable. "
                "We apologise for the inconvenience — please try again later."
            ),
        )
    except anthropic.RateLimitError as e:
        log.warning(
            "Claude API rate limit hit: category=%s error=%s", payload.category, e
        )
        raise HTTPException(
            status_code=503,
            detail="The AI service is busy. Please try again in a few minutes.",
        )
    except anthropic.InternalServerError as e:
        log.warning("Claude API overloaded: category=%s error=%s", payload.category, e)
        raise HTTPException(
            status_code=503,
            detail=(
                "The AI service is temporarily overloaded. "
                "Please try again in a moment."
            ),
        )
    except (ValidationError, ValueError) as e:
        log.error(
            "Invalid Claude response structure: category=%s error=%s",
            payload.category,
            e,
        )
        raise HTTPException(
            status_code=500,
            detail="Could not generate a valid recommendation. Please try again.",
        )
    except Exception:
        log.exception(
            "Unexpected error searching component: category=%s", payload.category
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    log.info(
        "Component found: category=%s name=%s", payload.category.value, result.name
    )
    _search_cache[body_hash] = result.model_dump(mode="json")
    return result
