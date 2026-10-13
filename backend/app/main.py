from collections.abc import AsyncIterator  # type for the lifespan function
from contextlib import asynccontextmanager  # turns lifespan into a context manager

from fastapi import FastAPI, HTTPException, Request, Response  # web framework pieces
from fastapi.exceptions import RequestValidationError  # raised on invalid request bodies
from fastapi.responses import JSONResponse  # used by the invalid reference handler
from slowapi import _rate_limit_exceeded_handler  # slowapi's own rate limit handler
from slowapi.errors import RateLimitExceeded  # raised when a rate limit is hit

# keep BOTH sides of the import conflict: your branch needs ProblemDetail and problem_type,
# main needs http_exception_handler
from app.api.problem_details import (
    ProblemDetail,  # problem response model (from your branch)
    http_exception_handler,  # flat problem+json for HTTPException (from main)
    problem_type,  # builds the problem type URI (from your branch)
    validation_exception_handler,  # problem+json for validation errors
)
from app.api.router import api_router  # all API routes
from app.core.config import get_settings  # app settings
from app.domain.subscriptions.exceptions import InvalidSubscriptionReferenceError  # bad plan or connection
from app.infrastructure.database.session import close_database  # closes DB connections on shutdown
from app.infrastructure.rate_limit.limiter import limiter  # shared rate limiter


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # run the app
    yield
    # close the database when the app stops
    await close_database()


def _rate_limit_handler(request: Request, exc: Exception) -> Response:
    # narrow the type so slowapi's handler type-checks
    assert isinstance(exc, RateLimitExceeded)
    # delegate to slowapi
    return _rate_limit_exceeded_handler(request, exc)


def create_app() -> FastAPI:
    # load settings
    settings = get_settings()

    # build the application
    application = FastAPI(
        title=settings.app_name,  # docs title
        version=settings.app_version,  # docs version
        lifespan=lifespan,  # startup and shutdown behaviour
    )

    # attach the rate limiter
    application.state.limiter = limiter

    # rate limit errors
    application.add_exception_handler(
        RateLimitExceeded,
        _rate_limit_handler,
    )

    # validation errors become problem+json
    application.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )

    # from main: HTTPException(detail={...}) becomes a flat application/problem+json response
    application.add_exception_handler(
        HTTPException,
        http_exception_handler,
    )

    # from your branch: bad plan or provider connection becomes a 422 problem response
    @application.exception_handler(InvalidSubscriptionReferenceError)
    async def invalid_reference(
        request: Request, exc: InvalidSubscriptionReferenceError
    ) -> Response:
        # build the problem body
        problem = ProblemDetail(
            type=problem_type("invalid-subscription-reference"),  # problem type URI
            title="Invalid subscription reference",  # short title
            status=422,  # HTTP status
            detail=str(exc),  # explanation
            instance=request.url.path,  # request path
        )
        # return it as problem+json
        return JSONResponse(
            status_code=422,
            content=problem.model_dump(exclude_none=True),
            media_type="application/problem+json",
        )

    # mount all routes under the API prefix
    application.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

    # hand back the finished app
    return application


# the app object the server runs
app = create_app()