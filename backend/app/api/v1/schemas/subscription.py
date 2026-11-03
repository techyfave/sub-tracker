import uuid
from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.api.v1.schemas.common import MoneySchema, PaginatedResponse
from app.domain.subscriptions.entities import BillingCadence, SubscriptionStatus


class PlanInput(MoneySchema):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "provider_id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "Monthly Premium",
                    "amount": "5000.00",
                    "currency": "NGN",
                    "billing_interval": "monthly",
                }
            ]
        },
    )

    provider_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(
        ge=0,
        max_digits=18,
        decimal_places=4,
        allow_inf_nan=False,
    )
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    billing_interval: BillingCadence


class PlanResponse(PlanInput):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174002",
                    "provider_id": "123e4567-e89b-12d3-a456-426614174001",
                    "name": "Monthly Premium",
                    "amount": "5000.00",
                    "currency": "NGN",
                    "billing_interval": "monthly",
                }
            ]
        },
    )

    id: uuid.UUID


class SubscriptionCreateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "plan_id": "123e4567-e89b-12d3-a456-426614174002",
                    "name": "Music Subscription",
                    "status": "active",
                    "provider_connection_id": None,
                    "started_at": "2026-10-01T10:00:00Z",
                    "renewal_at": "2026-11-01T10:00:00Z",
                    "ended_at": None,
                },
                {
                    "plan": {
                        "provider_id": "123e4567-e89b-12d3-a456-426614174001",
                        "name": "Monthly Premium",
                        "amount": "5000.00",
                        "currency": "NGN",
                        "billing_interval": "monthly",
                    },
                    "name": "Video Subscription",
                    "status": "active",
                },
            ]
        },
    )

    plan_id: uuid.UUID | None = None
    plan: PlanInput | None = None
    plan_alternatives: list[PlanInput] = Field(
        default_factory=list,
        max_length=50,
    )
    name: str = Field(min_length=1, max_length=200)
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    provider_connection_id: uuid.UUID | None = None
    started_at: AwareDatetime | None = None
    renewal_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def one_plan(self) -> Self:
        if (self.plan_id is None) == (self.plan is None):
            raise ValueError("provide exactly one of plan_id or plan")
        return self


class SubscriptionUpdateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "Updated Music Subscription",
                    "status": "paused",
                }
            ]
        },
    )

    plan_id: uuid.UUID | None = None
    plan: PlanInput | None = None
    plan_alternatives: list[PlanInput] | None = Field(
        default=None,
        max_length=50,
    )
    provider_connection_id: uuid.UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=200)
    status: SubscriptionStatus | None = None
    started_at: AwareDatetime | None = None
    renewal_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def valid_patch(self) -> Self:
        for key in ("plan_id", "plan", "plan_alternatives", "name", "status"):
            if key in self.model_fields_set and getattr(self, key) is None:
                raise ValueError(f"{key} cannot be null")
        if self.plan_id is not None and self.plan is not None:
            raise ValueError("provide only one of plan_id or plan")
        return self


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174003",
                    "user_id": "123e4567-e89b-12d3-a456-426614174004",
                    "plan_id": "123e4567-e89b-12d3-a456-426614174002",
                    "plan": {
                        "id": "123e4567-e89b-12d3-a456-426614174002",
                        "provider_id": "123e4567-e89b-12d3-a456-426614174001",
                        "name": "Monthly Premium",
                        "amount": "5000.00",
                        "currency": "NGN",
                        "billing_interval": "monthly",
                    },
                    "plan_alternatives": [],
                    "provider_connection_id": None,
                    "name": "Music Subscription",
                    "status": "active",
                    "started_at": "2026-10-01T10:00:00Z",
                    "renewal_at": "2026-11-01T10:00:00Z",
                    "ended_at": None,
                    "created_at": "2026-10-01T10:00:00Z",
                    "updated_at": "2026-10-01T10:00:00Z",
                    "deleted_at": None,
                }
            ]
        },
    )

    id: uuid.UUID
    user_id: uuid.UUID
    plan_id: uuid.UUID
    plan: PlanResponse
    plan_alternatives: list[PlanResponse]
    provider_connection_id: uuid.UUID | None
    name: str
    status: SubscriptionStatus
    started_at: datetime | None
    renewal_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


SubscriptionListResponse = PaginatedResponse[SubscriptionResponse]
