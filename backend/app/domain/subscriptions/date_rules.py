from datetime import UTC, datetime  # UTC-aware timestamps

from app.domain.subscriptions.exceptions import InvalidSubscriptionDatesError  # error raised below


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes, so treat those as UTC
    if value.tzinfo is None:
        # attach UTC to the naive value
        return value.replace(tzinfo=UTC)
    # already timezone-aware, use as is
    return value


def validate_subscription_dates(
    started_at: datetime | None,  # when the subscription began
    renewal_at: datetime | None,  # next renewal
    ended_at: datetime | None,  # when it ended
) -> None:
    # without a start date there is nothing to compare against
    if started_at is None:
        # nothing to validate
        return
    # renewal cannot be before the start
    if renewal_at is not None and _as_utc(renewal_at) < _as_utc(started_at):
        # refuse the impossible date
        raise InvalidSubscriptionDatesError("renewal_at must not be before started_at")
    # end cannot be before the start
    if ended_at is not None and _as_utc(ended_at) < _as_utc(started_at):
        # refuse the impossible date
        raise InvalidSubscriptionDatesError("ended_at must not be before started_at")
