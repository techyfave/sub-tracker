from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class TransactionCreate(BaseModel):
    amount: Decimal = Field(..., description="Exact monetary transaction value.")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code.")
    occurrence_time: datetime = Field(
        ..., description="Timezone-aware timestamp when charge occurred."
    )
    source: str = Field(
        ..., min_length=1, max_length=100, description="Provenance system tracking descriptor."
    )
    external_reference: str | None = Field(
        None, max_length=255, description="Unique idempotency string scoped to provider."
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Monetary amount must be non-negative.")
        if not v.is_finite():
            raise ValueError("Monetary amount must be a finite numerical representation.")
        if abs(v.as_tuple().exponent) > 4:
            raise ValueError("Precision cannot exceed 4 decimal places.")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if not v.isalpha():
            raise ValueError("Currency must consist of 3 alphabetic characters.")
        return v.upper()

    @field_validator("occurrence_time")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Occurrence time must be a timezone-aware timestamp.")
        return v


class UsageEventCreate(BaseModel):
    subscription_id: UUID
    occurrence_time: datetime = Field(..., description="Timezone-aware log tracking time.")
    quantity: Decimal | None = Field(None, description="Quantified units metric.")
    is_unknown: bool = Field(
        False, description="Explicit designation marking tracking as unknown vs zero."
    )
    source: str = Field(..., min_length=1, max_length=100, description="Origin logging identifier.")
    idempotency_key: str | None = Field(
        None, max_length=255, description="Tracking constraint reference."
    )

    @field_validator("occurrence_time")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Occurrence timestamp must be timezone-aware.")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal | None) -> Decimal | None:
        if v is not None:
            if v < 0:
                raise ValueError("Quantity cannot be negative.")
            if not v.is_finite():
                raise ValueError("Quantity must be a finite numerical representation.")
        return v

    @model_validator(mode="after")
    def verify_contradiction_contracts(self) -> "UsageEventCreate":
        if self.is_unknown and self.quantity is not None:
            raise ValueError(
                "Contradictory Input: Cannot define explicit quantity when marked as unknown."
            )
        if not self.is_unknown and self.quantity is None:
            raise ValueError(
                "Contradictory Input: Must specify quantity or explicitly mark as unknown."
            )
        return self
