from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.users.entities import RefreshToken, User


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def add(self, *, email: str, hashed_password: str) -> User: ...


class RefreshTokenRepository(Protocol):
    async def add(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken: ...

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None: ...

    async def rotate(
        self,
        *,
        consumed_token_id: UUID,
        revoked_at: datetime,
        user_id: UUID,
        new_token_hash: str,
        new_expires_at: datetime,
    ) -> RefreshToken | None:
        """Atomically consume one credential and issue its replacement.

        Must revoke ``consumed_token_id`` only if it is still unrevoked and, in
        the same transaction, persist the replacement. Returns the replacement,
        or ``None`` if the credential had already been consumed (lost a race
        or replayed) - in which case nothing is written. Implementations must
        guarantee that of any number of concurrent calls for the same
        credential, at most one returns a replacement.
        """
        ...

    async def revoke(self, token_id: UUID, *, revoked_at: datetime) -> None: ...

    async def revoke_all_for_user(self, user_id: UUID, *, revoked_at: datetime) -> None: ...
