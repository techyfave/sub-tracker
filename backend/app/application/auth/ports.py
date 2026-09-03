from __future__ import annotations

from typing import Protocol
from uuid import UUID


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, *, password: str, hashed_password: str) -> bool: ...


class AccessTokenIssuer(Protocol):
    """Issues and decodes short-lived, stateless access tokens (JWTs)."""

    def issue(self, *, user_id: UUID) -> str: ...

    def subject(self, token: str) -> UUID | None:
        """Return the user id encoded in ``token``, or ``None`` if invalid/expired."""
        ...


class RefreshTokenGenerator(Protocol):
    """Generates opaque refresh credentials and hashes them for storage.

    The raw token is only ever held in memory and returned to the client once;
    only its hash is persisted, so a database read can never leak a usable
    credential.
    """

    def generate(self) -> str: ...

    def hash(self, raw_token: str) -> str: ...
