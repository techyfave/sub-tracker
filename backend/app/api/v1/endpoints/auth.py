from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

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


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(_auth_rate_limit)
async def register(
    request: Request,  # noqa: ARG001 - required by slowapi's limiter to key on caller IP
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    try:
        user = await auth_service.register(email=payload.email, password=payload.password)
    except EmailAlreadyRegisteredError:
        raise_problem(
            status_code=status.HTTP_409_CONFLICT,
            title="Email already registered",
            detail="An account with this email already exists.",
        )
    return _user_response(user)


@router.post("/auth/login", response_model=AuthResponse)
@limiter.limit(_auth_rate_limit)
async def login(
    request: Request,  # noqa: ARG001
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    try:
        result = await auth_service.login(email=payload.email, password=payload.password)
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


@router.post("/auth/refresh", response_model=TokenResponse)
@limiter.limit(_auth_rate_limit)
async def refresh(
    request: Request,  # noqa: ARG001
    payload: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    try:
        result = await auth_service.refresh(raw_refresh_token=payload.refresh_token)
    except RefreshTokenReusedError:
        raise_problem(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Refresh token reused",
            detail="This refresh token was already used. All sessions for this "
            "account have been revoked; please log in again.",
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


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return _user_response(current_user)
