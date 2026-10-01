import uuid
from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.api.v1.schemas.common import MoneySchema, PaginatedResponse
from app.domain.subscriptions.entities import BillingCadence, SubscriptionStatus


class PlanInput(MoneySchema):
    model_config = ConfigDict(extra="forbid")
    provider_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    billing_interval: BillingCadence


class PlanResponse(PlanInput):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class SubscriptionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: uuid.UUID | None = None
    plan: PlanInput | None = None
    plan_alternatives: list[PlanInput] = Field(default_factory=list, max_length=50)
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
    model_config = ConfigDict(extra="forbid")
    plan_id: uuid.UUID | None = None
    plan: PlanInput | None = None
    plan_alternatives: list[PlanInput] | None = Field(default=None, max_length=50)
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
    model_config = ConfigDict(from_attributes=True)
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
