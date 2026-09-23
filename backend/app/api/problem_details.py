from __future__ import annotations

from typing import Any, NoReturn

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

PROBLEM_TYPE_BASE = "https://api.subtracker.dev/problems"


class ProblemDetail(BaseModel):
    """Shared API error representation based on Problem Details."""

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
    errors: list[dict[str, Any]] | None = None


def problem_type(name: str) -> str:
    """Return the URI identifying a category of API problem."""

    return f"{PROBLEM_TYPE_BASE}/{name}"


def raise_problem(
    *,
    status_code: int,
    title: str,
    detail: str,
    type_name: str = "about:blank",
) -> NoReturn:
    """Raise an HTTP exception using the shared Problem Details convention."""

    type_uri = (
        type_name
        if type_name == "about:blank"
        else problem_type(type_name)
    )

    raise HTTPException(
        status_code=status_code,
        detail={
            "type": type_uri,
            "title": title,
            "status": status_code,
            "detail": detail,
        },
    )

async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert request validation failures to Problem Details."""

    assert isinstance(exc, RequestValidationError)

    problem = ProblemDetail(
        type=problem_type("validation-error"),
        title="Validation Error",
        status=422,
        detail="The request contains invalid data.",
        instance=request.url.path,
        errors=[
            {
                "location": list(error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ],
    )

    return JSONResponse(
        status_code=422,
        content=problem.model_dump(exclude_none=True),
        media_type="application/problem+json",
    )


async def http_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert application HTTP exceptions to Problem Details."""

    assert isinstance(exc, HTTPException)

    if isinstance(exc.detail, dict):
        problem = {
            **exc.detail,
            "instance": request.url.path,
        }
    else:
        problem = ProblemDetail(
            type="about:blank",
            title="HTTP Error",
            status=exc.status_code,
            detail=str(exc.detail),
            instance=request.url.path,
        ).model_dump(exclude_none=True)

    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        headers=exc.headers,
        media_type="application/problem+json",
    )