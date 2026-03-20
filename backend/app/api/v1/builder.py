import asyncio
import json
import logging
import secrets
from collections.abc import AsyncGenerator

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.db.models import Build
from app.limiter import check_ai_rate_limit, limiter
from app.models.builder import BuildRequest, BuildResult
from app.security import events as guardrail_events
from app.security.guardrails import hash_build_request, input_guardrail
from app.services.build_validator import BuildValidationError
from app.services.claude import get_claude_service

log = logging.getLogger(__name__)
router = APIRouter(prefix="/build", tags=["build"])


_SSE_KEEPALIVE_INTERVAL = 15  # seconds between heartbeat comments


def _sse(event: str, data: str) -> str:
    """Format a single SSE frame."""
    return f"event: {event}\ndata: {data}\n\n"


def _map_error(exc: Exception, goal: str, budget: str) -> tuple[int, str]:
    """Map known exceptions to (status, detail) for the SSE error event."""
    ctx = "goal=%s budget=%s error=%s"
    if isinstance(exc, BuildValidationError):
        log.warning("Build validation failed: " + ctx, goal, budget, exc)
        return 400, (
            "The recommended build has compatibility issues that could "
            "not be resolved. Please try different requirements."
        )
    if isinstance(exc, TimeoutError):
        log.warning("Tool loop timeout: " + ctx, goal, budget, exc)
        return 504, "The AI took too long to respond. Please try again."
    if isinstance(exc, anthropic.APITimeoutError):
        log.warning("Claude API timed out: " + ctx, goal, budget, exc)
        return 504, "The AI took too long to respond. Please try again."
    if isinstance(exc, anthropic.APIConnectionError):
        log.warning("Claude unreachable: " + ctx, goal, budget, exc)
        return 502, "Could not reach the AI service. Please try again."
    if isinstance(exc, anthropic.AuthenticationError):
        log.error("Claude auth error: " + ctx, goal, budget, exc)
        return 503, (
            "Due to high demand, our AI service is temporarily "
            "unavailable. Please try again later."
        )
    if isinstance(exc, anthropic.RateLimitError):
        log.warning("Claude rate limit: " + ctx, goal, budget, exc)
        return 503, "The AI service is busy. Please try again."
    if isinstance(exc, anthropic.InternalServerError):
        log.warning("Claude overloaded: " + ctx, goal, budget, exc)
        return 503, (
            "The AI service is temporarily overloaded. Please try again in a moment."
        )
    if isinstance(exc, (ValidationError, ValueError)):
        log.error("Invalid Claude response: " + ctx, goal, budget, exc)
        return 500, ("Could not generate a valid recommendation. Please try again.")
    log.exception("Unexpected error: goal=%s budget=%s", goal, budget)
    return 500, "Internal server error"


@router.post(
    "",
    responses={
        200: {
            "description": (
                "SSE stream. Events: `progress` (phase updates), "
                "`result` (BuildResult JSON), `error` (status + detail)."
            ),
            "content": {"text/event-stream": {}},
        },
    },
)
async def create_build(
    request: Request,
    payload: BuildRequest,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    body_hash = hash_build_request(payload)

    # ---- Pre-stream checks (can still raise HTTPException) ----

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

    # Return cached result if the same inputs were seen before.
    # Cache hits bypass the rate limit since they don't call Claude.
    cached = await db.scalar(select(Build).where(Build.request_hash == body_hash))
    if cached:
        log.info("Build cache hit: hash=%s id=%s", body_hash[:8], cached.id)
        result = BuildResult.model_validate(cached.result)
        result_json = result.model_dump(mode="json")

        async def cached_stream() -> AsyncGenerator[str, None]:
            yield _sse("result", json.dumps(result_json))

        return StreamingResponse(
            cached_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Rate limit only uncached requests that will call Claude
    check_ai_rate_limit(request)

    # ---- Stream the build ----

    build_id = secrets.token_urlsafe(8)

    async def _build_events(queue: asyncio.Queue) -> None:
        """Producer: run the build and push SSE frames onto *queue*."""
        try:
            claude = get_claude_service()
            build: BuildResult | None = None
            async for event in claude.generate_build_stream(
                payload, build_id=build_id, client_ip=client_ip, db=db
            ):
                if event["type"] == "progress":
                    await queue.put(_sse("progress", json.dumps(event)))
                elif event["type"] == "result":
                    build = event["data"]

            if build is None:
                err = {"status": 500, "detail": "No result produced."}
                await queue.put(_sse("error", json.dumps(err)))
                return

            # Persist to DB
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
                await db.rollback()
                dup = await db.scalar(
                    select(Build).where(Build.request_hash == body_hash)
                )
                if dup:
                    build = BuildResult.model_validate(dup.result)
                else:
                    log.warning(
                        "IntegrityError but no duplicate found: build_id=%s hash=%s",
                        build_id,
                        body_hash[:8],
                    )

            log.info(
                "Build generated: id=%s goal=%s budget=%s components=%d",
                build_id,
                payload.goal.value,
                payload.budget_range.value,
                len(build.components),
            )
            await queue.put(_sse("result", json.dumps(build.model_dump(mode="json"))))

        except Exception as exc:
            if isinstance(exc, anthropic.AuthenticationError):
                await asyncio.sleep(3)
            status, detail = _map_error(
                exc, payload.goal.value, payload.budget_range.value
            )
            await queue.put(
                _sse("error", json.dumps({"status": status, "detail": detail}))
            )

    async def event_stream() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def producer() -> None:
            try:
                await _build_events(queue)
            finally:
                await queue.put(None)  # sentinel

        task = asyncio.create_task(producer())
        try:
            while True:
                try:
                    frame = await asyncio.wait_for(
                        queue.get(), timeout=_SSE_KEEPALIVE_INTERVAL
                    )
                except TimeoutError:
                    # No event within interval — send keepalive comment
                    yield ": keepalive\n\n"
                    continue
                if frame is None:
                    break
                yield frame
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
