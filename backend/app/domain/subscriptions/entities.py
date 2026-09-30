import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from app.domain.subscriptions.exceptions import (
    InvalidLifecycleTransitionError,
)


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class Subscription:
    user_id: uuid.UUID
    plan_id: uuid.UUID
    name: str
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    provider_connection_id: uuid.UUID | None = None
    started_at: datetime | None = None
    renewal_at: datetime | None = None
    ended_at: datetime | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None

    def transition_status(self, new_status: SubscriptionStatus) -> None:
        if self.status == SubscriptionStatus.CANCELLED and new_status == SubscriptionStatus.PAUSED:
            raise InvalidLifecycleTransitionError(
                self.status.value,
                new_status.value,
            )

        self.status = new_status
        self.updated_at = datetime.now(UTC)

    def mark_deleted(self) -> None:
        self.deleted_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
