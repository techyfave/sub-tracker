from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.core.config import get_settings
from app.infrastructure.database.session import close_database
from app.infrastructure.rate_limit.limiter import limiter


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_database()


def _rate_limit_handler(request: Request, exc: Exception) -> Response:
    # slowapi's own handler is typed against `RateLimitExceeded` specifically;
    # Starlette's `add_exception_handler` wants `Exception`. This adapter just
    # narrows back down so both sides type-check.
    assert isinstance(exc, RateLimitExceeded)
    return _rate_limit_exceeded_handler(request, exc)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
