from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException


def raise_problem(*, status_code: int, title: str, detail: str) -> NoReturn:
    """Raise an HTTPException whose body follows a minimal RFC 7807 shape.

    Scoped to what issue #5 needs. The full shared problem-details convention
    (a common ``type`` URI scheme, exception handlers wired at app level,
    etc.) belongs to issue #2.
    """
    raise HTTPException(
        status_code=status_code,
        detail={"title": title, "status": status_code, "detail": detail},
    )
