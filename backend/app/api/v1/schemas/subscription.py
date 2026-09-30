import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.api.v1.schemas.common import PaginatedResponse
from app.domain.subscriptions.entities import SubscriptionStatus


class SubscriptionCreateRequest(BaseModel):
    plan_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=200)
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    provider_connection_id: uuid.UUID | None = None
    started_at: datetime | None = None
    renewal_at: datetime | None = None
    ended_at: datetime | None = None


class SubscriptionUpdateRequest(BaseModel):
    plan_id: uuid.UUID | None = None
    provider_connection_id: uuid.UUID | None = None
    name: str | None = Field(None, min_length=1, max_length=200)
    status: SubscriptionStatus | None = None
    started_at: datetime | None = None
    renewal_at: datetime | None = None
    ended_at: datetime | None = None


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    plan_id: uuid.UUID
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
