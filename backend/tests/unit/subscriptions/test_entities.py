from datetime import date
import uuid
import pytest
from app.domain.subscriptions.entities import Subscription, BillingCadence, SubscriptionStatus
from app.domain.subscriptions.exceptions import InvalidLifecycleTransitionError, InvalidMoneyError


def test_subscription_creation_validation():
    user_id = uuid.uuid4()
    
    # Negative price test
    with pytest.raises(InvalidMoneyError):
        Subscription(
            user_id=user_id,
            name="Netflix",
            price=-10.0,
            currency="USD",
            billing_cadence=BillingCadence.MONTHLY,
            renewal_date=date.today(),
        )

    # Invalid currency code length test
    with pytest.raises(InvalidMoneyError):
        Subscription(
            user_id=user_id,
            name="Netflix",
            price=15.0,
            currency="US",
            billing_cadence=BillingCadence.MONTHLY,
            renewal_date=date.today(),
        )


def test_invalid_lifecycle_transition():
    user_id = uuid.uuid4()
    sub = Subscription(
        user_id=user_id,
        name="Netflix",
        price=15.0,
        currency="USD",
        billing_cadence=BillingCadence.MONTHLY,
        renewal_date=date.today(),
        status=SubscriptionStatus.CANCELLED,
    )

    with pytest.raises(InvalidLifecycleTransitionError):
        sub.transition_status(SubscriptionStatus.PAUSED)