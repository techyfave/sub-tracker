from __future__ import annotations

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class Argon2Hasher:
    """Argon2id password hashing.

    Chosen over bcrypt/PBKDF2 as the memory-hard, OWASP-recommended default
    for new designs. Encoded hashes are self-describing (algorithm, version,
    and cost parameters are embedded), so parameters can change later without
    invalidating already-stored hashes.
    """

    def __init__(self) -> None:
        self._impl = Argon2PasswordHasher()

    def hash(self, password: str) -> str:
        return self._impl.hash(password)

    def verify(self, *, password: str, hashed_password: str) -> bool:
        try:
            self._impl.verify(hashed_password, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
        return True
