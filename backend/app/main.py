from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.problem_details import http_exception_handler, validation_exception_handler
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

    application.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_handler,
    )

    application.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )

    # Without this, HTTPException(detail={...}) raised via raise_problem()
    # (used throughout app/api/v1/endpoints/auth.py) falls back to FastAPI's
    # default handler, which nests the problem body under a "detail" key and
    # serves it as application/json — silently breaking the flat
    # application/problem+json contract issue #2 established. Registering
    # http_exception_handler here is what makes raise_problem() actually
    # produce Problem Details on the wire, not just in source.
    application.add_exception_handler(
        HTTPException,
        http_exception_handler,
    )

    application.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

    return application


app = create_app()
