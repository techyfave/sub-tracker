from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.application.auth.dtos import AuthResult, TokenPair
from app.application.auth.ports import AccessTokenIssuer, PasswordHasher, RefreshTokenGenerator
from app.domain.users.entities import User
from app.domain.users.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    RefreshTokenInvalidError,
    RefreshTokenReusedError,
)
from app.domain.users.repositories import RefreshTokenRepository, UserRepository


def _default_now() -> datetime:
    return datetime.now(UTC)


class AuthService:
    """Coordinates registration, login, and refresh-token rotation.

    Depends only on abstractions (repositories + ports), never on FastAPI,
    SQLAlchemy, or a specific token/hash implementation.
    """

    def __init__(
        self,
        *,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        password_hasher: PasswordHasher,
        access_tokens: AccessTokenIssuer,
        refresh_token_generator: RefreshTokenGenerator,
        refresh_token_ttl: timedelta,
        now: Callable[[], datetime] = _default_now,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._password_hasher = password_hasher
        self._access_tokens = access_tokens
        self._refresh_token_generator = refresh_token_generator
        self._refresh_token_ttl = refresh_token_ttl
        self._now = now

    async def register(self, *, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        if await self._users.get_by_email(normalized_email) is not None:
            raise EmailAlreadyRegisteredError(normalized_email)

        hashed_password = self._password_hasher.hash(password)
        return await self._users.add(email=normalized_email, hashed_password=hashed_password)

    async def login(self, *, email: str, password: str) -> AuthResult:
        normalized_email = email.strip().lower()
        user = await self._users.get_by_email(normalized_email)

        if user is None or not user.is_active:
            # Run verify anyway against a dummy hash so unknown-email and
            # wrong-password responses take a comparable amount of time.
            self._password_hasher.verify(password=password, hashed_password=_DUMMY_HASH)
            raise InvalidCredentialsError(normalized_email)

        if not self._password_hasher.verify(
            password=password, hashed_password=user.hashed_password
        ):
            raise InvalidCredentialsError(normalized_email)

        tokens = await self._issue_tokens(user)
        return AuthResult(user=user, tokens=tokens)

    async def refresh(self, *, raw_refresh_token: str) -> AuthResult:
        token_hash = self._refresh_token_generator.hash(raw_refresh_token)
        stored = await self._refresh_tokens.get_by_token_hash(token_hash)
        now = self._now()

        if stored is None:
            raise RefreshTokenInvalidError

        if stored.is_revoked:
            # A token that was already rotated away is being replayed: treat
            # the whole family as compromised and force re-authentication.
            await self._refresh_tokens.revoke_all_for_user(stored.user_id, revoked_at=now)
            raise RefreshTokenReusedError

        if stored.is_expired(now=now):
            await self._refresh_tokens.revoke(stored.id, revoked_at=now)
            raise RefreshTokenInvalidError

        user = await self._users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            await self._refresh_tokens.revoke(stored.id, revoked_at=now)
            raise RefreshTokenInvalidError

        await self._refresh_tokens.revoke(stored.id, revoked_at=now)
        tokens = await self._issue_tokens(user)
        return AuthResult(user=user, tokens=tokens)

    async def _issue_tokens(self, user: User) -> TokenPair:
        access_token = self._access_tokens.issue(user_id=user.id)

        raw_refresh_token = self._refresh_token_generator.generate()
        token_hash = self._refresh_token_generator.hash(raw_refresh_token)
        await self._refresh_tokens.add(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=self._now() + self._refresh_token_ttl,
        )

        return TokenPair(access_token=access_token, refresh_token=raw_refresh_token)


# A syntactically valid-looking but unusable Argon2 hash, used only to equalize
# timing between "unknown email" and "wrong password" login failures.
_DUMMY_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
)
