from fastapi import APIRouter

from app.api.v1 import builder, search

router = APIRouter()

router.include_router(builder.router)
router.include_router(search.router)
