from __future__ import annotations

from dataclasses import dataclass

from app.domain.users.entities import User


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: User
    tokens: TokenPair
