from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_NUMERIC_18_4 = Decimal("99999999999999.9999")


class TransactionCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "occurrence_time": "2026-10-01T10:00:00Z",
                    "source": "manual",
                    "amount": "5000.00",
                    "currency": "NGN",
                    "external_reference": "charge-001",
                }
            ]
        }
    )

    amount: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=MAX_NUMERIC_18_4,
        max_digits=18,
        decimal_places=4,
        allow_inf_nan=False,
        description="Exact monetary transaction value.",
    )
    currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Three-letter ASCII currency code.",
    )
    occurrence_time: datetime = Field(
        ...,
        description="Timezone-aware timestamp when the charge occurred.",
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Source system tracking descriptor.",
    )
    external_reference: str | None = Field(
        None,
        max_length=255,
        description="Provider reference used for transaction deduplication.",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        if re.fullmatch(r"[A-Za-z]{3}", value) is None:
            raise ValueError("Currency must contain exactly three ASCII letters.")
        return value.upper()

    @field_validator("occurrence_time")
    @classmethod
    def validate_occurrence_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Occurrence time must be timezone-aware.")
        return value


class UsageEventCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "occurrence_time": "2026-10-01T10:00:00Z",
                    "source": "manual",
                    "subscription_id": "40000000-0000-4000-8000-000000000001",
                    "quantity": "0",
                    "is_unknown": False,
                    "idempotency_key": "usage-001",
                },
                {
                    "occurrence_time": "2026-10-01T10:00:00Z",
                    "source": "manual",
                    "subscription_id": "40000000-0000-4000-8000-000000000001",
                    "quantity": None,
                    "is_unknown": True,
                    "idempotency_key": "unknown-001",
                },
            ]
        }
    )

    subscription_id: UUID
    occurrence_time: datetime = Field(
        ...,
        description="Timezone-aware usage event timestamp.",
    )
    quantity: Decimal | None = Field(
        None,
        ge=Decimal("0"),
        le=MAX_NUMERIC_18_4,
        max_digits=18,
        decimal_places=4,
        allow_inf_nan=False,
        description="Non-negative usage quantity with up to four decimal places.",
    )
    is_unknown: bool = Field(
        False,
        description="Distinguishes unknown usage from a measured zero.",
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Source system identifier.",
    )
    idempotency_key: str | None = Field(
        None,
        max_length=255,
        description="Client-provided retry/deduplication key.",
    )

    @field_validator("occurrence_time")
    @classmethod
    def validate_occurrence_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Occurrence time must be timezone-aware.")
        return value

    @model_validator(mode="after")
    def verify_unknown_quantity_contract(self) -> UsageEventCreate:
        if self.is_unknown and self.quantity is not None:
            raise ValueError("Cannot provide a quantity when usage is marked as unknown.")

        if not self.is_unknown and self.quantity is None:
            raise ValueError("Provide a quantity or explicitly mark usage as unknown.")

        return self
