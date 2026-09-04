from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.users.entities import RefreshToken
from app.infrastructure.database.models.refresh_token import RefreshTokenModel


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _to_entity(model: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=model.id,
        user_id=model.user_id,
        token_hash=model.token_hash,
        expires_at=_as_utc(model.expires_at),
        created_at=_as_utc(model.created_at),
        revoked_at=_as_utc(model.revoked_at) if model.revoked_at is not None else None,
    )


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        model = RefreshTokenModel(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model is not None else None

    async def revoke(self, token_id: UUID, *, revoked_at: datetime) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.id == token_id)
            .values(revoked_at=revoked_at)
        )
        # Commit (not just flush): revocation must survive even if the caller
        # goes on to raise an error for this request, which would otherwise
        # roll this back via the get_session dependency's exception handling.
        await self._session.commit()

    async def revoke_all_for_user(self, user_id: UUID, *, revoked_at: datetime) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id)
            .where(RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        await self._session.commit()
