"""Concurrency proof for refresh-token rotation (issue #5 review follow-up).

SQLite (used by the rest of the suite) cannot exercise real row-level locking,
so this test runs against PostgreSQL and is skipped unless TEST_DATABASE_URL is
set, exactly like ``test_postgres_migrations.py``.

It fires many simultaneous refreshes of the SAME refresh credential, each on its
own database session/connection, and asserts the rotation is atomic:

* exactly one request wins and receives a replacement credential;
* every other request is rejected as a replay;
* revocation is durable: after the replay is detected, no credential from the
  family is left usable.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.application.auth.service import AuthService
from app.domain.users.exceptions import RefreshTokenReusedError
from app.infrastructure.database.models.refresh_token import RefreshTokenModel
from app.infrastructure.database.repositories.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from app.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
from app.infrastructure.security.access_tokens import JwtAccessTokenIssuer
from app.infrastructure.security.password_hasher import Argon2Hasher
from app.infrastructure.security.refresh_tokens import OpaqueRefreshTokenGenerator

CONCURRENT_REQUESTS = 8


def _database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL concurrency tests")
    return url


@pytest.fixture
async def pg_engine() -> AsyncIterator[AsyncEngine]:
    url = _database_url()
    await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
    )
    # A real pool so concurrent sessions get distinct connections/transactions.
    engine = create_async_engine(url, pool_size=CONCURRENT_REQUESTS + 2)
    try:
        yield engine
    finally:
        await engine.dispose()


def _service(session_factory: async_sessionmaker) -> tuple[AuthService, object]:  # type: ignore[type-arg]
    session = session_factory()
    service = AuthService(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        password_hasher=Argon2Hasher(),
        access_tokens=JwtAccessTokenIssuer(
            secret_key="test-secret-at-least-32-bytes-long-for-hs256",
            algorithm="HS256",
            ttl=timedelta(minutes=15),
        ),
        refresh_token_generator=OpaqueRefreshTokenGenerator(),
        refresh_token_ttl=timedelta(days=30),
    )
    return service, session


async def test_concurrent_refresh_of_one_credential_succeeds_exactly_once(
    pg_engine: AsyncEngine,
) -> None:
    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    email = f"race-{uuid.uuid4().hex}@example.com"

    # Arrange: one user with one live refresh credential.
    setup_service, setup_session = _service(session_factory)
    await setup_service.register(email=email, password="correct-horse")
    await setup_session.commit()  # type: ignore[attr-defined]
    login = await setup_service.login(email=email, password="correct-horse")
    await setup_session.commit()  # type: ignore[attr-defined]
    await setup_session.close()  # type: ignore[attr-defined]
    stolen_or_duplicated_token = login.tokens.refresh_token
    user_id = login.user.id

    barrier = asyncio.Barrier(CONCURRENT_REQUESTS)

    async def attempt() -> object:
        service, session = _service(session_factory)
        try:
            await barrier.wait()  # release every request at the same instant
            return await service.refresh(raw_refresh_token=stolen_or_duplicated_token)
        except RefreshTokenReusedError as error:
            return error
        finally:
            await session.close()  # type: ignore[attr-defined]

    try:
        outcomes = await asyncio.gather(*(attempt() for _ in range(CONCURRENT_REQUESTS)))

        successes = [o for o in outcomes if not isinstance(o, Exception)]
        rejections = [o for o in outcomes if isinstance(o, RefreshTokenReusedError)]

        # The core guarantee: one credential can be consumed only once.
        assert len(successes) == 1, f"{len(successes)} concurrent refreshes succeeded"
        assert len(rejections) == CONCURRENT_REQUESTS - 1

        # Durable revocation on replay: the losers detected reuse, so the whole
        # family (including the winner's replacement) must now be revoked.
        async with session_factory() as check:
            usable = await check.scalar(
                select(func.count())
                .select_from(RefreshTokenModel)
                .where(RefreshTokenModel.user_id == user_id)
                .where(RefreshTokenModel.revoked_at.is_(None))
            )
        assert usable == 0
    finally:
        async with session_factory() as cleanup:
            from sqlalchemy import delete

            from app.infrastructure.database.models.user import UserModel

            await cleanup.execute(delete(UserModel).where(UserModel.id == user_id))
            await cleanup.commit()
