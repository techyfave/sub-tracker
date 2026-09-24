from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from app.domain.common.identifiers import new_identifier
from app.domain.common.money import Money
from app.domain.common.timestamps import ensure_utc, utc_now


def test_new_identifier_returns_uuid() -> None:
    identifier = new_identifier()

    assert isinstance(identifier, UUID)


def test_new_identifier_returns_unique_values() -> None:
    assert new_identifier() != new_identifier()


def test_utc_now_is_timezone_aware_utc() -> None:
    value = utc_now()

    assert value.tzinfo is not None
    assert value.utcoffset() == timedelta(0)


def test_ensure_utc_normalizes_aware_datetime() -> None:
    source_timezone = timezone(timedelta(hours=1))
    value = datetime(2026, 1, 1, 13, 0, tzinfo=source_timezone)

    result = ensure_utc(value)

    assert result == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_ensure_utc_rejects_naive_datetime() -> None:
    value = datetime(2026, 1, 1, 12, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        ensure_utc(value)


def test_money_normalizes_currency_and_amount() -> None:
    money = Money(
        amount=Decimal("19.999"),
        currency="usd",
    )

    assert money.amount == Decimal("20.00")
    assert money.currency == "USD"


def test_money_rejects_invalid_currency() -> None:
    with pytest.raises(ValueError, match="three-letter"):
        Money(
            amount=Decimal("10.00"),
            currency="US",
        )


def test_money_rejects_non_finite_amount() -> None:
    with pytest.raises(ValueError, match="finite"):
        Money(
            amount=Decimal("NaN"),
            currency="USD",
        )
