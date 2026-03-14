import logging
import secrets

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.db.models import Build
from app.limiter import limiter
from app.models.builder import BuildRequest, BuildResult
from app.security import events as guardrail_events
from app.security.guardrails import hash_build_request, input_guardrail
from app.services.catalog import CatalogService
from app.services.claude import get_claude_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/build", tags=["build"])


@router.post("", response_model=BuildResult, status_code=201)
@limiter.shared_limit(lambda: settings.rate_limit_ai, scope="ai_calls")
async def create_build(
    request: Request,
    payload: BuildRequest,
    db: AsyncSession = Depends(get_db),
) -> BuildResult:
    client_ip = request.client.host if request.client else "unknown"
    body_hash = hash_build_request(payload)

    guard_result = input_guardrail.check(
        notes=payload.notes,
        budget_range=payload.budget_range,
        client_ip=client_ip,
        body_hash=body_hash,
    )
    if not guard_result.allowed:
        guardrail_events.emit(
            ip=client_ip,
            guardrail_name="InputGuardrail",
            action_taken="blocked",
            reason=guard_result.reason,
        )
        status = 429 if "Duplicate" in guard_result.reason else 400
        raise HTTPException(status_code=status, detail=guard_result.reason)

    # Return cached result if the same inputs were seen before
    cached = await db.scalar(select(Build).where(Build.request_hash == body_hash))
    if cached:
        log.info("Build cache hit: hash=%s id=%s", body_hash[:8], cached.id)
        return BuildResult.model_validate(cached.result)

    # Cache miss — call Claude
    build_id = secrets.token_urlsafe(8)

    try:
        # Query catalog for candidate components
        catalog = CatalogService()
        candidates = await catalog.get_candidates(db, payload)

        claude = get_claude_service()
        build = await claude.generate_build(
            payload, build_id=build_id, client_ip=client_ip, candidates=candidates
        )
    except anthropic.APITimeoutError as e:
        log.warning(
            "Claude API timed out: goal=%s budget=%s error=%s",
            payload.goal,
            payload.budget_range,
            e,
        )
        raise HTTPException(
            status_code=504, detail="The AI took too long to respond. Please try again."
        )
    except anthropic.APIConnectionError as e:
        log.warning(
            "Claude API unreachable: goal=%s budget=%s error=%s",
            payload.goal,
            payload.budget_range,
            e,
        )
        raise HTTPException(
            status_code=502, detail="Could not reach the AI service. Please try again."
        )
    except anthropic.RateLimitError as e:
        log.warning(
            "Claude API rate limit hit: goal=%s budget=%s error=%s",
            payload.goal,
            payload.budget_range,
            e,
        )
        raise HTTPException(
            status_code=503,
            detail="The AI service is busy. Please try again in a few minutes.",
        )
    except anthropic.InternalServerError as e:
        log.warning(
            "Claude API overloaded (529): goal=%s budget=%s error=%s",
            payload.goal,
            payload.budget_range,
            e,
        )
        raise HTTPException(
            status_code=503,
            detail="The AI service is temporarily overloaded. Please try again in a moment.",
        )
    except (ValidationError, ValueError) as e:
        log.error(
            "Invalid Claude response structure: goal=%s budget=%s error=%s",
            payload.goal,
            payload.budget_range,
            e,
        )
        raise HTTPException(
            status_code=500,
            detail="Could not generate a valid recommendation. Please try again.",
        )
    except Exception:
        log.exception(
            "Unexpected error generating build: goal=%s budget=%s",
            payload.goal,
            payload.budget_range,
        )
        raise HTTPException(status_code=500, detail="Internal server error")

    try:
        db.add(
            Build(
                id=build_id,
                request_hash=body_hash,
                request=payload.model_dump(mode="json"),
                result=build.model_dump(mode="json"),
            )
        )
        await db.commit()
    except IntegrityError:
        # Another concurrent request committed the same hash first — return that result.
        await db.rollback()
        cached = await db.scalar(select(Build).where(Build.request_hash == body_hash))
        if cached:
            return BuildResult.model_validate(cached.result)
        raise HTTPException(status_code=500, detail="Internal server error")

    log.info(
        "Build generated: id=%s goal=%s budget=%s components=%d",
        build_id,
        payload.goal.value,
        payload.budget_range.value,
        len(build.components),
    )
    return build


@router.get("/{build_id}", response_model=BuildResult)
@limiter.limit(lambda: settings.rate_limit_read)
async def get_build(
    request: Request,
    build_id: str,
    db: AsyncSession = Depends(get_db),
) -> BuildResult:
    build = await db.scalar(select(Build).where(Build.id == build_id))
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return BuildResult.model_validate(build.result)
