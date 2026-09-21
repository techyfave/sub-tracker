from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""

    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Normalize a timezone-aware datetime to UTC.

    Naive datetimes are rejected because their timezone cannot
    be determined safely.
    """

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")

    return value.astimezone(UTC)