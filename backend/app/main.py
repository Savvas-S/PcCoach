from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import router as v1_router
from app.config import settings
from app.limiter import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment == "production" and not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY must be set in production")
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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
