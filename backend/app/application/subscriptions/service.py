import uuid  # unique ids
from datetime import UTC, datetime  # UTC-aware timestamps

from app.api.v1.dependencies.auth import ensure_owner  # ownership check
from app.application.subscriptions.dtos import (  # data carriers
    CreateSubscriptionDTO,  # create input
    SubscriptionResponseDTO,  # response output
    UpdateSubscriptionDTO,  # update input
)
from app.domain.subscriptions.date_rules import validate_subscription_dates  # NEW: date check
from app.domain.subscriptions.entities import Subscription, SubscriptionStatus  # domain types
from app.domain.subscriptions.exceptions import SubscriptionNotFoundError  # missing subscription
from app.domain.subscriptions.repositories import SubscriptionRepository  # storage interface
from app.domain.users.entities import User  # current user type


class SubscriptionService:
    def __init__(self, repository: SubscriptionRepository):
        # keep the repository for every operation
        self.repository = repository

    def _to_response_dto(
        self,
        subscription: Subscription,
    ) -> SubscriptionResponseDTO:
        # copy entity fields into the response object
        return SubscriptionResponseDTO(
            id=subscription.id,  # id
            user_id=subscription.user_id,  # owner
            plan_id=subscription.plan_id,  # plan id
            provider_connection_id=subscription.provider_connection_id,  # provider link
            name=subscription.name,  # display name
            status=subscription.status,  # lifecycle state
            started_at=subscription.started_at,  # start time
            renewal_at=subscription.renewal_at,  # renewal time
            ended_at=subscription.ended_at,  # end time
            created_at=subscription.created_at,  # creation time
            updated_at=subscription.updated_at,  # last change time
            deleted_at=subscription.deleted_at,  # soft-delete marker
            plan=subscription.plan,  # current plan data
            plan_alternatives=subscription.plan_alternatives,  # alternative plans
        )

    async def create_subscription(
        self,
        dto: CreateSubscriptionDTO,
        current_user: User,
    ) -> SubscriptionResponseDTO:
        # caller must own what they create
        ensure_owner(
            resource_owner_id=dto.user_id,  # owner in the request
            current_user=current_user,  # who is calling
        )

        # NEW: reject impossible dates BEFORE anything is saved
        validate_subscription_dates(dto.started_at, dto.renewal_at, dto.ended_at)

        # build the entity
        subscription = Subscription(
            user_id=dto.user_id,  # owner
            plan_id=dto.plan.id if dto.plan else dto.plan_id or uuid.uuid4(),  # plan id
            plan=dto.plan,  # inline plan, if any
            plan_alternatives=dto.plan_alternatives,  # alternative plans
            name=dto.name,  # display name
            status=dto.status,  # lifecycle state
            provider_connection_id=dto.provider_connection_id,  # provider link
            started_at=dto.started_at,  # start time
            renewal_at=dto.renewal_at,  # renewal time
            ended_at=dto.ended_at,  # end time
        )

        # store it
        saved = await self.repository.save(subscription)

        # return the response object
        return self._to_response_dto(saved)

    async def get_subscription(
        self,
        subscription_id: uuid.UUID,
        current_user: User,
    ) -> SubscriptionResponseDTO:
        # fetch only this user's subscription
        subscription = await self.repository.get_by_id(
            subscription_id=subscription_id,  # which one
            user_id=current_user.id,  # whose
        )

        # missing or not theirs
        if not subscription:
            # same 404 for both
            raise SubscriptionNotFoundError(str(subscription_id))

        # second ownership safety check
        ensure_owner(
            resource_owner_id=subscription.user_id,  # actual owner
            current_user=current_user,  # who is calling
        )

        # return the response object
        return self._to_response_dto(subscription)

    async def list_subscriptions(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
        status: SubscriptionStatus | None = None,
    ) -> tuple[list[SubscriptionResponseDTO], int]:
        # fetch one page for this user
        subscriptions, total_count = await self.repository.list_by_user(
            user_id=current_user.id,  # whose
            skip=skip,  # offset
            limit=limit,  # page size
            status=status,  # optional filter
        )

        # convert entities to response objects
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
        # fetch only this user's subscription
        subscription = await self.repository.get_by_id(
            subscription_id=subscription_id,  # which one
            user_id=current_user.id,  # whose
        )

        # missing or not theirs
        if not subscription:
            # same 404 for both
            raise SubscriptionNotFoundError(str(subscription_id))

        # second ownership safety check
        ensure_owner(
            resource_owner_id=subscription.user_id,  # actual owner
            current_user=current_user,  # who is calling
        )

        # switch to an existing plan
        if dto.plan_id is not None:
            # point at that plan
            subscription.plan_id = dto.plan_id
            # drop any inline plan data
            subscription.plan = None
        # replace with an inline plan
        if dto.plan is not None:
            # use the new plan data
            subscription.plan = dto.plan
            # point at the new plan
            subscription.plan_id = dto.plan.id
        # replace alternative plans
        if dto.plan_alternatives is not None:
            # use the new list
            subscription.plan_alternatives = dto.plan_alternatives

        # set or clear the provider connection when it was sent
        if dto.provider_connection_id is not None or "provider_connection_id" in dto.fields_set:
            # apply the sent value, which may be None to clear it
            subscription.provider_connection_id = dto.provider_connection_id

        # change the name if sent
        if dto.name is not None:
            # apply it
            subscription.name = dto.name

        # set or clear the start date when it was sent
        if dto.started_at is not None or "started_at" in dto.fields_set:
            # apply the sent value
            subscription.started_at = dto.started_at

        # set or clear the renewal date when it was sent
        if dto.renewal_at is not None or "renewal_at" in dto.fields_set:
            # apply the sent value
            subscription.renewal_at = dto.renewal_at

        # set or clear the end date when it was sent
        if dto.ended_at is not None or "ended_at" in dto.fields_set:
            # apply the sent value
            subscription.ended_at = dto.ended_at

        # apply the status move, which the entity validates
        if dto.status is not None and dto.status != subscription.status:
            # raises if the move is illegal
            subscription.transition_status(dto.status)

        # NEW: check the FINAL combined dates BEFORE saving, so a rejected update changes nothing
        validate_subscription_dates(
            subscription.started_at,  # stored or new start
            subscription.renewal_at,  # stored or new renewal
            subscription.ended_at,  # stored or new end
        )

        # record the change time
        subscription.updated_at = datetime.now(UTC)
        # store the changes
        updated = await self.repository.update(subscription)

        # return the response object
        return self._to_response_dto(updated)

    async def delete_subscription(
        self,
        subscription_id: uuid.UUID,
        current_user: User,
    ) -> bool:
        # fetch only this user's subscription
        subscription = await self.repository.get_by_id(
            subscription_id=subscription_id,  # which one
            user_id=current_user.id,  # whose
        )

        # missing or not theirs
        if not subscription:
            # same 404 for both
            raise SubscriptionNotFoundError(str(subscription_id))

        # second ownership safety check
        ensure_owner(
            resource_owner_id=subscription.user_id,  # actual owner
            current_user=current_user,  # who is calling
        )

        # soft delete so downstream history is kept
        return await self.repository.soft_delete(
            subscription_id=subscription_id,  # which one
            user_id=current_user.id,  # whose
        )
