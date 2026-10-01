import uuid
from datetime import UTC, datetime

from app.api.v1.dependencies.auth import ensure_owner
from app.application.subscriptions.dtos import (
    CreateSubscriptionDTO,
    SubscriptionResponseDTO,
    UpdateSubscriptionDTO,
)
from app.domain.subscriptions.entities import Subscription, SubscriptionStatus
from app.domain.subscriptions.exceptions import SubscriptionNotFoundError
from app.domain.subscriptions.repositories import SubscriptionRepository
from app.domain.users.entities import User


class SubscriptionService:
    def __init__(self, repository: SubscriptionRepository):
        self.repository = repository

    def _to_response_dto(
        self,
        subscription: Subscription,
    ) -> SubscriptionResponseDTO:
        return SubscriptionResponseDTO(
            id=subscription.id,
            user_id=subscription.user_id,
            plan_id=subscription.plan_id,
            provider_connection_id=subscription.provider_connection_id,
            name=subscription.name,
            status=subscription.status,
            started_at=subscription.started_at,
            renewal_at=subscription.renewal_at,
            ended_at=subscription.ended_at,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            deleted_at=subscription.deleted_at,
            plan=subscription.plan,
            plan_alternatives=subscription.plan_alternatives,
        )

    async def create_subscription(
        self,
        dto: CreateSubscriptionDTO,
        current_user: User,
    ) -> SubscriptionResponseDTO:
        ensure_owner(
            resource_owner_id=dto.user_id,
            current_user=current_user,
        )

        subscription = Subscription(
            user_id=dto.user_id,
            plan_id=dto.plan.id if dto.plan else dto.plan_id or uuid.uuid4(),
            plan=dto.plan,
            plan_alternatives=dto.plan_alternatives,
            name=dto.name,
            status=dto.status,
            provider_connection_id=dto.provider_connection_id,
            started_at=dto.started_at,
            renewal_at=dto.renewal_at,
            ended_at=dto.ended_at,
        )

        saved = await self.repository.save(subscription)

        return self._to_response_dto(saved)

    async def get_subscription(
        self,
        subscription_id: uuid.UUID,
        current_user: User,
    ) -> SubscriptionResponseDTO:
        subscription = await self.repository.get_by_id(
            subscription_id=subscription_id,
            user_id=current_user.id,
        )

        if not subscription:
            raise SubscriptionNotFoundError(str(subscription_id))

        ensure_owner(
            resource_owner_id=subscription.user_id,
            current_user=current_user,
        )

        return self._to_response_dto(subscription)

    async def list_subscriptions(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        status: SubscriptionStatus | None = None,
    ) -> tuple[list[SubscriptionResponseDTO], int]:
        subscriptions, total_count = await self.repository.list_by_user(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            status=status,
        )

        return (
            [self._to_response_dto(subscription) for subscription in subscriptions],
            total_count,
        )

    async def update_subscription(
        self,
        subscription_id: uuid.UUID,
        dto: UpdateSubscriptionDTO,
        current_user: User,
    ) -> SubscriptionResponseDTO:
        subscription = await self.repository.get_by_id(
            subscription_id=subscription_id,
            user_id=current_user.id,
        )

        if not subscription:
            raise SubscriptionNotFoundError(str(subscription_id))

        ensure_owner(
            resource_owner_id=subscription.user_id,
            current_user=current_user,
        )

        if dto.plan_id is not None:
            subscription.plan_id = dto.plan_id
            subscription.plan = None
        if dto.plan is not None:
            subscription.plan = dto.plan
            subscription.plan_id = dto.plan.id
        if dto.plan_alternatives is not None:
            subscription.plan_alternatives = dto.plan_alternatives

        if dto.provider_connection_id is not None or "provider_connection_id" in dto.fields_set:
            subscription.provider_connection_id = dto.provider_connection_id

        if dto.name is not None:
            subscription.name = dto.name

        if dto.started_at is not None or "started_at" in dto.fields_set:
            subscription.started_at = dto.started_at

        if dto.renewal_at is not None or "renewal_at" in dto.fields_set:
            subscription.renewal_at = dto.renewal_at

        if dto.ended_at is not None or "ended_at" in dto.fields_set:
            subscription.ended_at = dto.ended_at

        if dto.status is not None and dto.status != subscription.status:
            subscription.transition_status(dto.status)

        subscription.updated_at = datetime.now(UTC)
        updated = await self.repository.update(subscription)

        return self._to_response_dto(updated)

    async def delete_subscription(
        self,
        subscription_id: uuid.UUID,
        current_user: User,
    ) -> bool:
        subscription = await self.repository.get_by_id(
            subscription_id=subscription_id,
            user_id=current_user.id,
        )

        if not subscription:
            raise SubscriptionNotFoundError(str(subscription_id))

        ensure_owner(
            resource_owner_id=subscription.user_id,
            current_user=current_user,
        )

        return await self.repository.soft_delete(
            subscription_id=subscription_id,
            user_id=current_user.id,
        )
