class SubscriptionDomainError(Exception):
    """Base exception for subscription domain errors."""

    pass


class SubscriptionNotFoundError(SubscriptionDomainError):
    """Raised when a subscription entity is not found."""

    def __init__(self, subscription_id: str):
        super().__init__(f"Subscription with ID '{subscription_id}' was not found.")


class InvalidLifecycleTransitionError(SubscriptionDomainError):
    """Raised when an invalid status transition is attempted."""

    def __init__(self, current_status: str, new_status: str):
        super().__init__(
            f"Cannot transition subscription from '{current_status}' to '{new_status}'."
        )


class InvalidMoneyError(SubscriptionDomainError):
    """Raised when amount or currency formatting is invalid."""

    pass


class InvalidSubscriptionReferenceError(SubscriptionDomainError):
    """A supplied plan, provider, or connection is unavailable."""
