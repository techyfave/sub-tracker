import uuid
from dataclasses import dataclass
from datetime import datetime

from app.domain.subscriptions.entities import SubscriptionStatus


@dataclass
class CreateSubscriptionDTO:
    user_id: uuid.UUID
    plan_id: uuid.UUID
    name: str
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    provider_connection_id: uuid.UUID | None = None
    started_at: datetime | None = None
    renewal_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass
class UpdateSubscriptionDTO:
    plan_id: uuid.UUID | None = None
    provider_connection_id: uuid.UUID | None = None
    name: str | None = None
    status: SubscriptionStatus | None = None
    started_at: datetime | None = None
    renewal_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass
class SubscriptionResponseDTO:
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
