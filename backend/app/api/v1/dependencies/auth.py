from __future__ import annotations

from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.problem_details import raise_problem
from app.application.auth.service import AuthService
from app.core.config import Settings, get_settings
from app.domain.users.entities import User
from app.infrastructure.database.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from app.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from app.infrastructure.database.session import get_session
from app.infrastructure.security.access_tokens import JwtAccessTokenIssuer
from app.infrastructure.security.password_hasher import Argon2Hasher
from app.infrastructure.security.refresh_tokens import OpaqueRefreshTokenGenerator

_password_hasher = Argon2Hasher()
_refresh_token_generator = OpaqueRefreshTokenGenerator()
_bearer_scheme = HTTPBearer(auto_error=False)


def get_access_token_issuer(
    settings: Annotated[Settings, Depends(get_settings)],
) -> JwtAccessTokenIssuer:
    return JwtAccessTokenIssuer(
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        ttl=timedelta(minutes=settings.access_token_expire_minutes),
    )


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    access_tokens: Annotated[JwtAccessTokenIssuer, Depends(get_access_token_issuer)],
) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        password_hasher=_password_hasher,
        access_tokens=access_tokens,
        refresh_token_generator=_refresh_token_generator,
        refresh_token_ttl=timedelta(days=settings.refresh_token_expire_days),
    )


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    access_tokens: Annotated[JwtAccessTokenIssuer, Depends(get_access_token_issuer)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> User:
    """Reusable dependency: resolves the caller's User from a bearer access token.

    Any endpoint that needs "who is making this request" depends on this
    instead of re-implementing token parsing.
    """
    if credentials is None:
        raise_problem(status_code=401, title="Not authenticated", detail="Missing bearer token.")

    user_id = access_tokens.subject(credentials.credentials)
    if user_id is None:
        raise_problem(
            status_code=401, title="Not authenticated", detail="Invalid or expired access token."
        )

    user = await SqlAlchemyUserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise_problem(
            status_code=401, title="Not authenticated", detail="Invalid or expired access token."
        )

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def ensure_owner(*, resource_owner_id: UUID, current_user: User) -> None:
    """Reusable ownership check for any user-owned resource.

    Endpoints for owned resources (subscriptions, transactions, etc. — added
    in later issues) call this once they've loaded the resource, e.g.::

        ensure_owner(resource_owner_id=subscription.user_id, current_user=current_user)

    Raises 403 rather than 404 to be explicit about *why* access is denied;
    switch to 404 instead if the team decides not to reveal resource
    existence to non-owners.
    """
    if resource_owner_id != current_user.id:
        raise_problem(
            status_code=403,
            title="Forbidden",
            detail="You do not have access to this resource.",
        )
