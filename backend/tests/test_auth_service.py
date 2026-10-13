from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.service import AuthService
from app.domain.users.entities import RefreshToken
from app.domain.users.exceptions import (
    InvalidCredentialsError,
    RefreshTokenInvalidError,
    RefreshTokenReusedError,
)
from app.infrastructure.database.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from app.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from app.infrastructure.security.access_tokens import JwtAccessTokenIssuer
from app.infrastructure.security.password_hasher import Argon2Hasher
from app.infrastructure.security.refresh_tokens import OpaqueRefreshTokenGenerator


class _FakeClock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now


def _build_service(
    session: AsyncSession, *, clock: _FakeClock, refresh_ttl: timedelta
) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        password_hasher=Argon2Hasher(),
        access_tokens=JwtAccessTokenIssuer(
            secret_key="test-secret-at-least-32-bytes-long-for-hs256",
            algorithm="HS256",
            ttl=timedelta(minutes=15),
            now=clock,
        ),
        refresh_token_generator=OpaqueRefreshTokenGenerator(),
        refresh_token_ttl=refresh_ttl,
        now=clock,
    )


async def test_expired_refresh_token_is_rejected(db_session: AsyncSession) -> None:
    clock = _FakeClock(datetime(2026, 1, 1, tzinfo=UTC))
    service = _build_service(db_session, clock=clock, refresh_ttl=timedelta(days=30))

    await service.register(email="expiry@example.com", password="correct-horse")
    result = await service.login(email="expiry@example.com", password="correct-horse")

    # Move the clock past the refresh token's expiry.
    clock.now = clock.now + timedelta(days=31)

    with pytest.raises(RefreshTokenInvalidError):
        await service.refresh(raw_refresh_token=result.tokens.refresh_token)


async def test_refresh_still_within_ttl_succeeds(db_session: AsyncSession) -> None:
    clock = _FakeClock(datetime(2026, 1, 1, tzinfo=UTC))
    service = _build_service(db_session, clock=clock, refresh_ttl=timedelta(days=30))

    await service.register(email="valid@example.com", password="correct-horse")
    result = await service.login(email="valid@example.com", password="correct-horse")

    clock.now = clock.now + timedelta(days=29)

    refreshed = await service.refresh(raw_refresh_token=result.tokens.refresh_token)
    assert refreshed.user.email == "valid@example.com"


async def test_login_deactivated_user_is_invalid_credentials(db_session: AsyncSession) -> None:
    clock = _FakeClock(datetime(2026, 1, 1, tzinfo=UTC))
    service = _build_service(db_session, clock=clock, refresh_ttl=timedelta(days=30))

    await service.register(email="disabled@example.com", password="correct-horse")

    # Simulate deactivation directly at the persistence layer (no "disable
    # user" use case exists yet — that's outside issue #5's scope).
    from sqlalchemy import update

    from app.infrastructure.database.models.user import UserModel

    await db_session.execute(
        update(UserModel).where(UserModel.email == "disabled@example.com").values(is_active=False)
    )
    await db_session.commit()

    with pytest.raises(InvalidCredentialsError):
        await service.login(email="disabled@example.com", password="correct-horse")


class _RacedRefreshTokenRepository(SqlAlchemyRefreshTokenRepository):
    """Simulates losing a race: a competing request consumes the credential in
    the window between this request's read and its write. The read still returns
    the (now stale) unrevoked snapshot, exactly as it would under concurrency."""

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        stale = await super().get_by_token_hash(token_hash)
        if stale is not None:
            await self.revoke(stale.id, revoked_at=datetime(2026, 1, 1, tzinfo=UTC))
        return stale


async def test_refresh_that_loses_a_race_is_rejected_and_revokes_the_family(
    db_session: AsyncSession,
) -> None:
    from sqlalchemy import func, select

    from app.infrastructure.database.models.refresh_token import RefreshTokenModel

    clock = _FakeClock(datetime(2026, 1, 1, tzinfo=UTC))
    service = _build_service(db_session, clock=clock, refresh_ttl=timedelta(days=30))
    await service.register(email="race@example.com", password="correct-horse")
    result = await service.login(email="race@example.com", password="correct-horse")

    racing = _build_service(db_session, clock=clock, refresh_ttl=timedelta(days=30))
    racing._refresh_tokens = _RacedRefreshTokenRepository(db_session)  # noqa: SLF001

    with pytest.raises(RefreshTokenReusedError):
        await racing.refresh(raw_refresh_token=result.tokens.refresh_token)

    # No replacement was minted and nothing from the family remains usable.
    total = await db_session.scalar(select(func.count()).select_from(RefreshTokenModel))
    usable = await db_session.scalar(
        select(func.count())
        .select_from(RefreshTokenModel)
        .where(RefreshTokenModel.revoked_at.is_(None))
    )
    assert total == 1
    assert usable == 0
