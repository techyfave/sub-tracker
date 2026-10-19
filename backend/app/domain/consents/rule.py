from __future__ import annotations

import re

_SCOPE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._:-][a-z0-9]+)*$")
_POLICY_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,49}$")


def validate_policy_version(value: str) -> str:
    """Validate a non-empty, bounded, opaque policy version identifier."""
    if not _POLICY_VERSION_PATTERN.fullmatch(value):
        raise ValueError(
            "policy_version must be 1-50 letters, numbers, dots,underscores or hyphens"
        )

    return value


def validate_scopes(scopes: list[str]) -> list[str]:
    """Require unique, syntactically valid scope names without assuming a team registry."""
    if not scopes:
        raise ValueError("At least one scope is required")
    if len(scopes) != len(set(scopes)):
        raise ValueError("Scopes must not contain duplicates")
    if any(not _SCOPE_PATTERN.fullmatch(scope) or len(scope) > 100 for scope in scopes):
        raise ValueError("Each scope must be a valid scope identifier of at most 100 characters")
    return scopes
