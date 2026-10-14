"""Version 1 API."""
from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.subscriptions import router as subscriptions_router

router = APIRouter()

router.include_router(auth_router, tags=["auth"])
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(subscriptions_router, prefix="/subscriptions", tags=["subscriptions"])
