import logging
import os
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s — %(message)s")

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.database import get_db, init_db
from app.limiter import limiter

log = logging.getLogger(__name__)


async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return clean 422s without leaking internal field names in production."""
    if settings.environment == "production":
        return JSONResponse({"detail": "Invalid request."}, status_code=422)
    # In development, pass through the full Pydantic error detail for debugging.
    return JSONResponse({"detail": exc.errors()}, status_code=422)


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Ensure all HTTPExceptions return JSON."""
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'",
    "Server": "pccoach",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response.

    Exceptions raised inside the route handler propagate through
    BaseHTTPMiddleware.call_next() and bypass app.add_exception_handler().
    We catch them here so the global Exception handler is always effective
    and unhandled errors always return JSON (not Starlette's default HTML/text).
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            log.exception(
                "Unhandled exception: %s %s", request.method, request.url.path
            )
            response = JSONResponse(
                {"detail": "Internal server error"}, status_code=500
            )
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        return response


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    retry_after = getattr(exc, "retry_after", None)
    detail = (
        f"Rate limit exceeded. Try again in {retry_after}s."
        if retry_after is not None
        else "Rate limit exceeded. Try again later."
    )
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}
    return JSONResponse({"detail": detail}, status_code=429, headers=headers)


# Known env var name typos — extra="ignore" silently drops these;
# warn at startup instead.
_ENV_VAR_TYPOS: dict[str, str] = {
    "CORS_ORIGIN": "CORS_ORIGINS",
    "ANTHROPIC_KEY": "ANTHROPIC_API_KEY",
    "ANTHROPIC_API_KEYS": "ANTHROPIC_API_KEY",
    "ENVIRONEMENT": "ENVIRONMENT",
    "ENVIROMENT": "ENVIRONMENT",
}


def _init_tracing() -> None:
    """Instrument the Anthropic SDK with Arize AX tracing (if configured)."""
    if not settings.arize_api_key or not settings.arize_space_id:
        log.info("Arize tracing: disabled (ARIZE_API_KEY or ARIZE_SPACE_ID not set)")
        return
    try:
        from arize.otel import register
        from openinference.instrumentation.anthropic import AnthropicInstrumentor

        tracer_provider = register(
            space_id=settings.arize_space_id,
            api_key=settings.arize_api_key.get_secret_value(),
            project_name="pccoach",
        )
        AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)
        log.info("Arize tracing: enabled (project=pccoach)")
    except Exception:
        log.exception("Arize tracing: failed to initialize — continuing without tracing")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize LLM tracing (Arize AX)
    _init_tracing()

    # Warn about likely env var name typos that pydantic-settings silently ignores.
    for typo, correct in _ENV_VAR_TYPOS.items():
        if typo in os.environ:
            log.warning(
                "Env var '%s' looks like a typo for '%s' "
                "— it is being ignored by config",
                typo,
                correct,
            )

    if settings.environment == "production":
        if (
            not settings.anthropic_api_key
            or not settings.anthropic_api_key.get_secret_value()
        ):
            raise RuntimeError("ANTHROPIC_API_KEY must be set in production")
        if not settings.database_url or not settings.database_url.get_secret_value():
            raise RuntimeError("DATABASE_URL must be set in production")
        if any("localhost" in o for o in settings.cors_origins):
            raise RuntimeError(
                "CORS_ORIGINS contains 'localhost' in production — "
                "likely a typo (e.g. CORS_ORIGIN instead of CORS_ORIGINS)"
            )
        # CORS wildcard is never acceptable in production
        if "*" in settings.cors_origins:
            raise RuntimeError(
                "CORS_ORIGINS must not contain '*' in production. "
                "Set explicit allowed origins."
            )
    init_db()
    log.info(
        "Starting PcCoach: environment=%s cors_origins=%s docs=%s api_key=%s db=%s",
        settings.environment,
        settings.cors_origins,
        "disabled" if settings.environment == "production" else "enabled",
        "set" if settings.anthropic_api_key else "unset",
        "set" if settings.database_url else "unset",
    )
    yield


_is_production = settings.environment == "production"

app = FastAPI(
    title="PcCoach API",
    description="AI-powered PC building assistant",
    version="0.1.0",
    lifespan=lifespan,
    # Disable interactive docs in production — they expose the full API schema publicly
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_exception_handler(RequestValidationError, _validation_error_handler)
app.add_exception_handler(StarletteHTTPException, _http_exception_handler)

# Security headers on every response (applied before CORS to avoid conflicts)
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"] if _is_production else ["*"],
    allow_headers=["Content-Type"] if _is_production else ["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
