from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.infrastructure.database.health import database_is_ready

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    service: str
    version: str


@router.get("/live", response_model=HealthResponse)
async def liveness(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={
        503: {
            "description": "The database is unavailable or not ready.",
            "content": {
                "application/json": {
                    "schema": HealthResponse.model_json_schema(),
                    "example": {
                        "status": "unavailable",
                        "service": "Sub Tracker API",
                        "version": "0.1.0",
                    },
                }
            },
        }
    },
)
async def readiness(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    ready = await database_is_ready()

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if ready else "unavailable",
        service=settings.app_name,
        version=settings.app_version,
    )
