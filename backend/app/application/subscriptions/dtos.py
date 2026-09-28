from datetime import date, datetime
from typing import Optional
from dataclasses import dataclass
import uuid

from app.domain.subscriptions.entities import BillingCadence, SubscriptionStatus


@dataclass
class PlanAlternativeDTO:
    name: str
    price: float
    currency: str
    billing_cadence: BillingCadence
    notes: Optional[str] = None


@dataclass
class CreateSubscriptionDTO:
    user_id: uuid.UUID
    name: str
    price: float
    currency: str
    billing_cadence: BillingCadence
    renewal_date: date
    plan_alternatives: list[PlanAlternativeDTO] = None

    def __post_init__(self):
        if self.plan_alternatives is None:
            self.plan_alternatives = []


@dataclass
class UpdateSubscriptionDTO:
    name: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    billing_cadence: Optional[BillingCadence] = None
    renewal_date: Optional[date] = None
    status: Optional[SubscriptionStatus] = None
    plan_alternatives: Optional[list[PlanAlternativeDTO]] = None


@dataclass
class SubscriptionResponseDTO:
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    price: float
    currency: str
    billing_cadence: BillingCadence
    renewal_date: date
    status: SubscriptionStatus
    plan_alternatives: list[PlanAlternativeDTO]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None