from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    """Core identity entity. Contains no framework or persistence concerns."""

    id: UUID
    email: str
    hashed_password: str
    is_active: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RefreshToken:
    """A single refresh-credential in a rotating token family.

    Only the hash of the presented token is ever stored or compared; the raw
    token is returned to the client once, at issuance time, and never again.
    """

    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, *, now: datetime) -> bool:
        return now >= self.expires_at
