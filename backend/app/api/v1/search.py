import logging

import anthropic
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.config import settings
from app.limiter import limiter
from app.models.builder import ComponentSearchRequest, ComponentSearchResult
from app.security import events as guardrail_events
from app.security.guardrails import hash_search_request, input_guardrail
from app.security.output_guard import GuardrailBlocked, output_guardrail
from app.services.claude import get_claude_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=ComponentSearchResult, status_code=200)
@limiter.shared_limit(lambda: settings.rate_limit_ai, scope="ai_calls")
async def search_component(
    request: Request, payload: ComponentSearchRequest
) -> ComponentSearchResult:
    # ------------------------------------------------------------------
    # Input guardrails — blocklist + duplicate detection
    # ------------------------------------------------------------------
    client_ip = request.client.host if request.client else "unknown"
    body_hash = hash_search_request(payload)

    guard_result = input_guardrail.check_search(
        description=payload.description,
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

    # ------------------------------------------------------------------
    # Claude call
    # ------------------------------------------------------------------
    try:
        claude = get_claude_service()
        result = await claude.search_component(payload)
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
            detail="The AI service is temporarily overloaded. Please try again in a moment.",
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

    # ------------------------------------------------------------------
    # Output guardrails — leak detection, off-topic, PII strip
    # ------------------------------------------------------------------
    checked = output_guardrail.check_search(result)
    if isinstance(checked, GuardrailBlocked):
        guardrail_events.emit(
            ip=client_ip,
            guardrail_name="OutputGuardrail.search",
            action_taken="blocked",
            reason=checked.reason,
        )
        if checked.reason == "off_topic_response":
            raise HTTPException(
                status_code=400,
                detail="The AI was unable to find a matching component. Please rephrase your description.",
            )
        raise HTTPException(
            status_code=500,
            detail="Could not generate a valid recommendation. Please try again.",
        )

    log.info(
        "Component found: category=%s name=%s", payload.category.value, checked.name
    )
    return checked
