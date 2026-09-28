import uuid
from typing import Optional

from app.api.v1.dependencies.auth import ensure_owner
from app.domain.subscriptions.entities import Subscription, PlanAlternative, SubscriptionStatus
from app.domain.subscriptions.exceptions import SubscriptionNotFoundError
from app.domain.subscriptions.repositories import SubscriptionRepository
from app.application.subscriptions.dtos import (
    CreateSubscriptionDTO,
    UpdateSubscriptionDTO,
    SubscriptionResponseDTO,
    PlanAlternativeDTO,
)


class SubscriptionService:
    def __init__(self, repository: SubscriptionRepository):
        self.repository = repository

    def _to_response_dto(self, sub: Subscription) -> SubscriptionResponseDTO:
        return SubscriptionResponseDTO(
            id=sub.id,
            user_id=sub.user_id,
            name=sub.name,
            price=sub.price,
            currency=sub.currency,
            billing_cadence=sub.billing_cadence,
            renewal_date=sub.renewal_date,
            status=sub.status,
            plan_alternatives=[
                PlanAlternativeDTO(
                    name=alt.name,
                    price=alt.price,
                    currency=alt.currency,
                    billing_cadence=alt.billing_cadence,
                    notes=alt.notes,
                )
                for alt in sub.plan_alternatives
            ],
            created_at=sub.created_at,
            updated_at=sub.updated_at,
            deleted_at=sub.deleted_at,
        )

    async def create_subscription(
        self, dto: CreateSubscriptionDTO, current_user
    ) -> SubscriptionResponseDTO:
        ensure_owner(resource_owner_id=dto.user_id, current_user=current_user)

        plan_alts = [
            PlanAlternative(
                name=alt.name,
                price=alt.price,
                currency=alt.currency,
                billing_cadence=alt.billing_cadence,
                notes=alt.notes,
            )
            for alt in dto.plan_alternatives
        ]

        subscription = Subscription(
            user_id=dto.user_id,
            name=dto.name,
            price=dto.price,
            currency=dto.currency,
            billing_cadence=dto.billing_cadence,
            renewal_date=dto.renewal_date,
            plan_alternatives=plan_alts,
        )

        saved = await self.repository.save(subscription)
        return self._to_response_dto(saved)

    async def get_subscription(
        self, subscription_id: uuid.UUID, current_user
    ) -> SubscriptionResponseDTO:
        sub = await self.repository.get_by_id(subscription_id=subscription_id, user_id=current_user.id)
        if not sub:
            raise SubscriptionNotFoundError(str(subscription_id))

        ensure_owner(resource_owner_id=sub.user_id, current_user=current_user)
        return self._to_response_dto(sub)

    async def list_subscriptions(
        self,
        current_user,
        skip: int = 0,
        limit: int = 20,
        status: Optional[SubscriptionStatus] = None,
    ) -> tuple[list[SubscriptionResponseDTO], int]:
        subs, total_count = await self.repository.list_by_user(
            user_id=current_user.id, skip=skip, limit=limit, status=status
        )
        return [self._to_response_dto(s) for s in subs], total_count

    async def update_subscription(
        self, subscription_id: uuid.UUID, dto: UpdateSubscriptionDTO, current_user
    ) -> SubscriptionResponseDTO:
        sub = await self.repository.get_by_id(subscription_id=subscription_id, user_id=current_user.id)
        if not sub:
            raise SubscriptionNotFoundError(str(subscription_id))

        ensure_owner(resource_owner_id=sub.user_id, current_user=current_user)

        if dto.name is not None:
            sub.name = dto.name
        if dto.price is not None:
            sub.price = dto.price
            sub.__post_init__()
        if dto.currency is not None:
            sub.currency = dto.currency
            sub.__post_init__()
        if dto.billing_cadence is not None:
            sub.billing_cadence = dto.billing_cadence
        if dto.renewal_date is not None:
            sub.renewal_date = dto.renewal_date
        if dto.status is not None and dto.status != sub.status:
            sub.transition_status(dto.status)
        if dto.plan_alternatives is not None:
            sub.plan_alternatives = [
                PlanAlternative(
                    name=alt.name,
                    price=alt.price,
                    currency=alt.currency,
                    billing_cadence=alt.billing_cadence,
                    notes=alt.notes,
                )
                for alt in dto.plan_alternatives
            ]

        updated = await self.repository.update(sub)
        return self._to_response_dto(updated)

    async def delete_subscription(
        self, subscription_id: uuid.UUID, current_user
    ) -> bool:
        sub = await self.repository.get_by_id(subscription_id=subscription_id, user_id=current_user.id)
        if not sub:
            raise SubscriptionNotFoundError(str(subscription_id))

        ensure_owner(resource_owner_id=sub.user_id, current_user=current_user)
        return await self.repository.soft_delete(subscription_id=subscription_id, user_id=current_user.id)