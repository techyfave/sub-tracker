from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.users.entities import User
from app.infrastructure.database.models.user import UserModel


def _as_utc(value: datetime) -> datetime:
    """Coerce a possibly-naive datetime to UTC-aware.

    Postgres round-trips `DateTime(timezone=True)` as tz-aware, but some
    dialects (SQLite, used in tests) return naive datetimes. The app's own
    convention is "timestamps are stored in UTC" (see data-and-api.md), so a
    naive value read back is always assumed to already be UTC.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        hashed_password=model.hashed_password,
        is_active=model.is_active,
        created_at=_as_utc(model.created_at),
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return _to_entity(model) if model is not None else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return _to_entity(model) if model is not None else None

    async def add(self, *, email: str, hashed_password: str) -> User:
        model = UserModel(email=email, hashed_password=hashed_password)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)
