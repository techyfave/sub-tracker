from __future__ import annotations

import hashlib
import secrets


class OpaqueRefreshTokenGenerator:
    """Generates high-entropy opaque refresh tokens.

    Refresh tokens are deliberately *not* JWTs: they carry no client-readable
    claims, and only their SHA-256 hash is ever persisted, so a leaked
    database (unlike a leaked JWT secret) cannot be used to mint new
    sessions.
    """

    def generate(self) -> str:
        return secrets.token_urlsafe(48)

    def hash(self, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
