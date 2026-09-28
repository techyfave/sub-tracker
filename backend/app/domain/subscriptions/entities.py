from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
import uuid

from app.domain.subscriptions.exceptions import InvalidLifecycleTransitionError, InvalidMoneyError


class BillingCadence(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    QUARTERLY = "quarterly"
    WEEKLY = "weekly"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class PlanAlternative:
    name: str
    price: float
    currency: str
    billing_cadence: BillingCadence
    notes: Optional[str] = None


@dataclass
class Subscription:
    user_id: uuid.UUID
    name: str
    price: float
    currency: str
    billing_cadence: BillingCadence
    renewal_date: date
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    plan_alternatives: list[PlanAlternative] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None

    def __post_init__(self):
        if self.price < 0:
            raise InvalidMoneyError("Subscription price cannot be negative.")
        if len(self.currency) != 3:
            raise InvalidMoneyError("Currency code must be a 3-letter ISO code (e.g. USD, EUR).")
        self.currency = self.currency.upper()

    def transition_status(self, new_status: SubscriptionStatus) -> None:
        """Validates and applies status transitions."""
        if self.status == SubscriptionStatus.CANCELLED and new_status == SubscriptionStatus.PAUSED:
            raise InvalidLifecycleTransitionError(self.status.value, new_status.value)
        
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def mark_deleted(self) -> None:
        """Soft deletes the subscription."""
        self.deleted_at = datetime.now(timezone.utc)