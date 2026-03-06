from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings

app = FastAPI(
    title="PcCoach API",
    description="AI-powered PC building assistant",
    version="0.1.0",
)

_is_production = settings.environment == "production"

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"] if _is_production else ["*"],
    allow_headers=["Content-Type", "Authorization"] if _is_production else ["*"],
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
