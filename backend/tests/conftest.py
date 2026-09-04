from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.infrastructure.database import models  # noqa: F401 - registers tables on Base.metadata
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_session
from app.infrastructure.rate_limit.limiter import limiter
from app.main import app

# A single shared in-memory SQLite connection (StaticPool keeps it alive across
# the async engine's "connections") stands in for Postgres in tests. The app
# only uses cross-dialect SQLAlchemy features (Uuid, DateTime(timezone=True),
# func.now()), so this is a faithful enough substitute for exercising the auth
# flow without requiring a running Postgres instance.
test_engine: AsyncEngine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)


async def _override_get_session() -> AsyncIterator[AsyncSession]:
    async with _test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_session] = _override_get_session


@pytest.fixture(autouse=True)
async def _clean_database() -> AsyncIterator[None]:
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    limiter.reset()
    yield
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        yield test_client


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with _test_session_factory() as session:
        yield session
        await session.commit()
