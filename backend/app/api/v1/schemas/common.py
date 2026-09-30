from __future__ import annotations

from decimal import Decimal
from math import ceil

from pydantic import BaseModel, Field, field_validator


class MoneySchema(BaseModel):
    """Reusable API representation of a monetary value."""

    amount: Decimal
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        currency = value.strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("currency must be a three-letter code")

        return currency


class PaginationParams(BaseModel):
    """Validated pagination input."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginationMeta(BaseModel):
    """Metadata returned with paginated resources."""

    page: int
    page_size: int
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)

    @classmethod
    def create(
        cls,
        *,
        page: int,
        page_size: int,
        total_items: int,
    ) -> PaginationMeta:
        total_pages = ceil(total_items / page_size) if total_items else 0

        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )


class PaginatedResponse[T](BaseModel):
    """Reusable response envelope for paginated API resources."""

    items: list[T]
    pagination: PaginationMeta
