from fastapi import APIRouter

from app.api.v1.endpoints.analyses import router as analyses_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.consents import router as consents_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.recommendations import router as recommendations_router
from app.api.v1.endpoints.subscriptions import router as subscriptions_router

# First, define the main API router.
router = APIRouter()

# Next, register each endpoint router.
router.include_router(health_router, prefix="/health", tags=["health"])
router.include_router(auth_router, tags=["auth"])
router.include_router(subscriptions_router)

# No prefix here: recommendations_router defines its own /recommendations routes internally
router.include_router(recommendations_router)

router.include_router(consents_router)

router.include_router(analyses_router)
