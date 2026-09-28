from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.subscriptions import router as subscriptions_router

router = APIRouter()
router.include_router(health_router, prefix="/health", tags=["health"])
# No prefix here: auth_router defines its own full paths (/auth/register,
# /auth/login, /auth/refresh, and top-level /me per docs/architecture/data-and-api.md).
router.include_router(auth_router, tags=["auth"])
# No prefix here: subscriptions_router defines its own /subscriptions routes internally
router.include_router(subscriptions_router)