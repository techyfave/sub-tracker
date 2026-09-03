class DomainError(Exception):
    """Base class for errors raised by the users domain."""


class EmailAlreadyRegisteredError(DomainError):
    """Raised when registration is attempted with an email already in use."""


class InvalidCredentialsError(DomainError):
    """Raised when login credentials do not match a known, active user.

    Deliberately used for both 'unknown email' and 'wrong password' so callers
    cannot distinguish account existence from a timing or error-shape signal.
    """


class RefreshTokenInvalidError(DomainError):
    """Raised when a presented refresh token is unknown, expired, or malformed."""


class RefreshTokenReusedError(DomainError):
    """Raised when an already-rotated (revoked) refresh token is presented again.

    This is a signal of possible theft: the caller should revoke the entire
    token family for the affected user.
    """
