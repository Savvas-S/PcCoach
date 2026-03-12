import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import router as v1_router
from app.config import settings
from app.limiter import limiter

log = logging.getLogger(__name__)


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    retry_after = getattr(exc, "retry_after", None)
    detail = (
        f"Rate limit exceeded. Try again in {retry_after}s."
        if retry_after is not None
        else "Rate limit exceeded. Try again later."
    )
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}
    return JSONResponse({"detail": detail}, status_code=429, headers=headers)


# Known env var name typos — extra="ignore" silently drops these; warn at startup instead.
_ENV_VAR_TYPOS: dict[str, str] = {
    "CORS_ORIGIN": "CORS_ORIGINS",
    "ANTHROPIC_KEY": "ANTHROPIC_API_KEY",
    "ANTHROPIC_API_KEYS": "ANTHROPIC_API_KEY",
    "ENVIRONEMENT": "ENVIRONMENT",
    "ENVIROMENT": "ENVIRONMENT",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warn about likely env var name typos that pydantic-settings silently ignores.
    for typo, correct in _ENV_VAR_TYPOS.items():
        if typo in os.environ:
            log.warning(
                "Env var '%s' looks like a typo for '%s' — it is being ignored by config",
                typo, correct,
            )

    if settings.environment == "production":
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY must be set in production")
        if any("localhost" in o for o in settings.cors_origins):
            raise RuntimeError(
                "CORS_ORIGINS contains 'localhost' in production — "
                "likely a typo (e.g. CORS_ORIGIN instead of CORS_ORIGINS)"
            )
    log.info(
        "Starting PcCoach: environment=%s cors_origins=%s docs=%s",
        settings.environment,
        settings.cors_origins,
        "disabled" if settings.environment == "production" else "enabled",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"] if _is_production else ["*"],
    allow_headers=["Content-Type"] if _is_production else ["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
