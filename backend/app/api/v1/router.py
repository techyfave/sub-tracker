from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router

router = APIRouter()
router.include_router(health_router, prefix="/health", tags=["health"])
# No prefix here: auth_router defines its own full paths (/auth/register,
# /auth/login, /auth/refresh, and top-level /me — see issue #5's acceptance criteria).
router.include_router(auth_router, tags=["auth"])
