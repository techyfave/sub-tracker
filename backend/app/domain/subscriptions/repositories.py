import uuid
from typing import Protocol

from app.domain.subscriptions.entities import Subscription, SubscriptionStatus


class SubscriptionRepository(Protocol):
    async def save(self, subscription: Subscription) -> Subscription: ...

    async def get_by_id(
        self, subscription_id: uuid.UUID, user_id: uuid.UUID
    ) -> Subscription | None: ...

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        status: SubscriptionStatus | None = None,
    ) -> tuple[list[Subscription], int]: ...

    async def update(self, subscription: Subscription) -> Subscription: ...

    async def soft_delete(self, subscription_id: uuid.UUID, user_id: uuid.UUID) -> bool: ...
