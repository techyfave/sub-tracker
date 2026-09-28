import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.domain.subscriptions.entities import BillingCadence, SubscriptionStatus


class PlanAlternativeSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    price: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    billing_cadence: BillingCadence
    notes: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.upper()


class SubscriptionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    price: float = Field(..., ge=0)
    currency: str = Field(..., min_length=3, max_length=3)
    billing_cadence: BillingCadence
    renewal_date: date
    plan_alternatives: list[PlanAlternativeSchema] = Field(default_factory=list)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.upper()


class SubscriptionUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    billing_cadence: Optional[BillingCadence] = None
    renewal_date: Optional[date] = None
    status: Optional[SubscriptionStatus] = None
    plan_alternatives: Optional[list[PlanAlternativeSchema]] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else None


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    price: float
    currency: str
    billing_cadence: BillingCadence
    renewal_date: date
    status: SubscriptionStatus
    plan_alternatives: list[PlanAlternativeSchema]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class PaginatedSubscriptionResponse(BaseModel):
    items: list[SubscriptionResponse]
    total: int
    page: int
    page_size: int