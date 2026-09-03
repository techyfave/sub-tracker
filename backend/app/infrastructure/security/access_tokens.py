from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt


def _default_now() -> datetime:
    return datetime.now(UTC)


class JwtAccessTokenIssuer:
    """Issues short-lived, stateless JWT access tokens.

    Access tokens are never persisted or revocable individually; they are
    kept short-lived (see ``Settings.access_token_expire_minutes``) so a
    compromised token has a small blast radius. Session-level revocation is
    handled by the refresh-token family instead (see RefreshTokenRepository).
    """

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        ttl: timedelta,
        now: Callable[[], datetime] = _default_now,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._ttl = ttl
        self._now = now

    def issue(self, *, user_id: UUID) -> str:
        issued_at = self._now()
        payload = {
            "sub": str(user_id),
            "iat": issued_at,
            "exp": issued_at + self._ttl,
            "type": "access",
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def subject(self, token: str) -> UUID | None:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except jwt.InvalidTokenError:
            return None

        if payload.get("type") != "access":
            return None

        try:
            return UUID(str(payload["sub"]))
        except (KeyError, ValueError):
            return None
