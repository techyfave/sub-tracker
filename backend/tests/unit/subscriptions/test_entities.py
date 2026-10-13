import uuid
from datetime import UTC, datetime

import pytest

from app.domain.subscriptions.entities import (
    Subscription,
    SubscriptionStatus,
)
from app.domain.subscriptions.exceptions import (
    InvalidLifecycleTransitionError,
)


def test_subscription_creation():
    user_id = uuid.uuid4()
    plan_id = uuid.uuid4()

    subscription = Subscription(
        user_id=user_id,
        plan_id=plan_id,
        name="Netflix",
    )

    assert subscription.user_id == user_id
    assert subscription.plan_id == plan_id
    assert subscription.name == "Netflix"
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.provider_connection_id is None
    assert subscription.started_at is None
    assert subscription.renewal_at is None
    assert subscription.ended_at is None
    assert subscription.deleted_at is None


def test_subscription_can_have_dates_and_provider_connection():
    user_id = uuid.uuid4()
    plan_id = uuid.uuid4()
    provider_connection_id = uuid.uuid4()

    started_at = datetime.now(UTC)
    renewal_at = datetime.now(UTC)

    subscription = Subscription(
        user_id=user_id,
        plan_id=plan_id,
        name="Netflix",
        provider_connection_id=provider_connection_id,
        started_at=started_at,
        renewal_at=renewal_at,
    )

    assert subscription.provider_connection_id == provider_connection_id
    assert subscription.started_at == started_at
    assert subscription.renewal_at == renewal_at


def test_subscription_status_transition():
    subscription = Subscription(
        user_id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        name="Netflix",
    )

    subscription.transition_status(SubscriptionStatus.PAUSED)

    assert subscription.status == SubscriptionStatus.PAUSED


def test_cancelled_subscription_cannot_be_paused():
    subscription = Subscription(
        user_id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        name="Netflix",
        status=SubscriptionStatus.CANCELLED,
    )

    with pytest.raises(InvalidLifecycleTransitionError):
        subscription.transition_status(SubscriptionStatus.PAUSED)


def test_subscription_can_be_expired():
    subscription = Subscription(
        user_id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        name="Netflix",
    )

    subscription.transition_status(SubscriptionStatus.EXPIRED)

    assert subscription.status == SubscriptionStatus.EXPIRED


def test_mark_deleted():
    subscription = Subscription(
        user_id=uuid.uuid4(),
        plan_id=uuid.uuid4(),
        name="Netflix",
    )

    old_updated_at = subscription.updated_at

    assert subscription.deleted_at is None

    subscription.mark_deleted()

    assert subscription.deleted_at is not None
    assert subscription.updated_at > old_updated_at
