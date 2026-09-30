from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.schemas.common import (
    MoneySchema,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
)


def test_money_schema_normalizes_currency() -> None:
    money = MoneySchema(
        amount=Decimal("19.99"),
        currency="usd",
    )

    assert money.amount == Decimal("19.99")
    assert money.currency == "USD"


def test_money_schema_rejects_invalid_currency() -> None:
    with pytest.raises(ValidationError):
        MoneySchema(
            amount=Decimal("10.00"),
            currency="US",
        )


def test_pagination_defaults() -> None:
    pagination = PaginationParams()

    assert pagination.page == 1
    assert pagination.page_size == 20


def test_pagination_rejects_page_zero() -> None:
    with pytest.raises(ValidationError):
        PaginationParams(page=0)


def test_pagination_rejects_page_size_over_limit() -> None:
    with pytest.raises(ValidationError):
        PaginationParams(page_size=101)


def test_pagination_meta_calculates_total_pages() -> None:
    pagination = PaginationMeta.create(
        page=1,
        page_size=20,
        total_items=45,
    )

    assert pagination.total_pages == 3


def test_pagination_meta_handles_empty_collection() -> None:
    pagination = PaginationMeta.create(
        page=1,
        page_size=20,
        total_items=0,
    )

    assert pagination.total_pages == 0


def test_paginated_response_is_generic() -> None:
    response = PaginatedResponse[str](
        items=["one", "two"],
        pagination=PaginationMeta.create(
            page=1,
            page_size=20,
            total_items=2,
        ),
    )

    assert response.items == ["one", "two"]
    assert response.pagination.total_items == 2
