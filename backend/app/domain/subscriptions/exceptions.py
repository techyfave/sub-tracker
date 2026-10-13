class SubscriptionDomainError(Exception):
    """Base exception for subscription domain errors."""

    # no extra behaviour needed
    pass


class SubscriptionNotFoundError(SubscriptionDomainError):
    """Raised when a subscription entity is not found."""

    # build a readable message from the id
    def __init__(self, subscription_id: str):
        # pass the message to the base Exception
        super().__init__(f"Subscription with ID '{subscription_id}' was not found.")


class InvalidLifecycleTransitionError(SubscriptionDomainError):
    """Raised when an invalid status transition is attempted."""

    # build a readable message from both statuses
    def __init__(self, current_status: str, new_status: str):
        # pass the message to the base Exception
        super().__init__(
            f"Cannot transition subscription from '{current_status}' to '{new_status}'."
        )


class InvalidMoneyError(SubscriptionDomainError):
    """Raised when amount or currency formatting is invalid."""

    # no extra behaviour needed
    pass


class InvalidSubscriptionReferenceError(SubscriptionDomainError):
    """A supplied plan, provider, or connection is unavailable."""


class InvalidSubscriptionDatesError(SubscriptionDomainError):
    """Raised when subscription dates contradict each other."""
