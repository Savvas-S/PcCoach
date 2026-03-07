from fastapi import APIRouter

from app.api.v1 import builder

router = APIRouter()

router.include_router(builder.router)


@router.get("/ping")
async def ping():
    return {"message": "pong"}
