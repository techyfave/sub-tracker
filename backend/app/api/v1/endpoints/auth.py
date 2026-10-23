from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.openapi_responses import (
    RATE_LIMIT_RESPONSE,
    REFRESH_VALIDATION_ERROR_EXAMPLE,
    VALIDATION_ERROR_EXAMPLE,
    problem_response,
)
from app.api.problem_details import raise_problem
from app.api.v1.dependencies.auth import CurrentUser, get_auth_service
from app.api.v1.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.application.auth.service import AuthService
from app.core.config import get_settings
from app.domain.users.entities import User
from app.domain.users.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    RefreshTokenInvalidError,
    RefreshTokenReusedError,
)
from app.infrastructure.rate_limit.limiter import limiter

router = APIRouter()

_auth_rate_limit = get_settings().auth_rate_limit


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, created_at=user.created_at)


def _validation_response(instance: str) -> dict[str, object]:
    return problem_response(
        "The request contains invalid data.",
        VALIDATION_ERROR_EXAMPLE,
        instance=instance,
    )


def _unauthorized_response(
    instance: str,
    detail: str,
    title: str = "HTTP Error",
) -> dict[str, object]:
    return problem_response(
        "Authentication failed.",
        {
            "type": "about:blank",
            "title": title,
            "status": 401,
            "detail": detail,
            "instance": instance,
        },
        instance=instance,
    )


@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: problem_response(
            "An account with this email already exists.",
            {
                "type": "about:blank",
                "title": "Email already registered",
                "status": 409,
                "detail": "An account with this email already exists.",
                "instance": "/api/v1/auth/register",
            },
            instance="/api/v1/auth/register",
        ),
        422: _validation_response("/api/v1/auth/register"),
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(_auth_rate_limit)
async def register(
    request: Request,
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    try:
        user = await auth_service.register(
            email=payload.email,
            password=payload.password,
        )
    except EmailAlreadyRegisteredError:
        raise_problem(
            status_code=status.HTTP_409_CONFLICT,
            title="Email already registered",
            detail="An account with this email already exists.",
        )

    return _user_response(user)


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    responses={
        401: _unauthorized_response(
            "/api/v1/auth/login",
            "Email or password is incorrect.",
            title="Invalid credentials",
        ),
        422: _validation_response("/api/v1/auth/login"),
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(_auth_rate_limit)
async def login(
    request: Request,
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    try:
        result = await auth_service.login(
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentialsError:
        raise_problem(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Invalid credentials",
            detail="Email or password is incorrect.",
        )

    return AuthResponse(
        user=_user_response(result.user),
        tokens=TokenResponse(
            access_token=result.tokens.access_token,
            refresh_token=result.tokens.refresh_token,
            token_type=result.tokens.token_type,
        ),
    )


@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    responses={
        401: problem_response(
            "The refresh token is invalid, expired, or has already been used.",
            {
                "type": "about:blank",
                "title": "Invalid refresh token",
                "status": 401,
                "detail": "Refresh token is invalid, expired, or unknown.",
                "instance": "/api/v1/auth/refresh",
            },
            instance="/api/v1/auth/refresh",
            examples={
                "invalid_or_expired": {
                    "type": "about:blank",
                    "title": "Invalid refresh token",
                    "status": 401,
                    "detail": "Refresh token is invalid, expired, or unknown.",
                    "instance": "/api/v1/auth/refresh",
                },
                "reused_token": {
                    "type": "about:blank",
                    "title": "Refresh token reused",
                    "status": 401,
                    "detail": (
                        "This refresh token was already used. All sessions "
                        "for this account have been revoked; please log in again."
                    ),
                    "instance": "/api/v1/auth/refresh",
                },
            },
        ),
        422: problem_response(
            "The request contains invalid data.",
            REFRESH_VALIDATION_ERROR_EXAMPLE,
            instance="/api/v1/auth/refresh",
        ),
        429: RATE_LIMIT_RESPONSE,
    },
)
async def refresh(
    request: Request,
    payload: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    try:
        result = await auth_service.refresh(raw_refresh_token=payload.refresh_token)
    except RefreshTokenReusedError:
        raise_problem(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Refresh token reused",
            detail=(
                "This refresh token was already used. All sessions for this "
                "account have been revoked; please log in again."
            ),
        )
    except RefreshTokenInvalidError:
        raise_problem(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Invalid refresh token",
            detail="Refresh token is invalid, expired, or unknown.",
        )

    return TokenResponse(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        token_type=result.tokens.token_type,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: _unauthorized_response(
            "/api/v1/me",
            "Authentication is required.",
        ),
    },
)
async def me(current_user: CurrentUser) -> UserResponse:
    return _user_response(current_user)
