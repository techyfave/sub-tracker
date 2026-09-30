import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.subscriptions.entities import Subscription, SubscriptionStatus
from app.domain.subscriptions.repositories import SubscriptionRepository
from app.infrastructure.database.models.core import (
    SubscriptionModel,
)
from app.infrastructure.database.models.core import (
    SubscriptionStatus as SubscriptionModelStatus,
)


class SqlAlchemySubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: SubscriptionModel) -> Subscription:
        return Subscription(
            id=model.id,
            user_id=model.user_id,
            plan_id=model.plan_id,
            name=model.name,
            status=SubscriptionStatus(model.status),
            provider_connection_id=model.provider_connection_id,
            started_at=model.started_at,
            renewal_at=model.renewal_at,
            ended_at=model.ended_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Subscription) -> SubscriptionModel:
        return SubscriptionModel(
            id=entity.id,
            user_id=entity.user_id,
            plan_id=entity.plan_id,
            provider_connection_id=entity.provider_connection_id,
            name=entity.name,
            status=entity.status,
            started_at=entity.started_at,
            renewal_at=entity.renewal_at,
            ended_at=entity.ended_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    async def save(self, subscription: Subscription) -> Subscription:
        model = self._to_model(subscription)

        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)

        return self._to_entity(model)

    async def get_by_id(
        self,
        subscription_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Subscription | None:
        query = select(SubscriptionModel).where(
            and_(
                SubscriptionModel.id == subscription_id,
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_entity(model)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        status: SubscriptionStatus | None = None,
    ) -> tuple[list[Subscription], int]:
        conditions = [
            SubscriptionModel.user_id == user_id,
            SubscriptionModel.deleted_at.is_(None),
        ]

        if status is not None:
            conditions.append(SubscriptionModel.status == status)

        count_stmt = select(func.count()).select_from(SubscriptionModel).where(and_(*conditions))

        count_result = await self.session.execute(count_stmt)
        total_count = count_result.scalar_one()

        query = (
            select(SubscriptionModel)
            .where(and_(*conditions))
            .order_by(SubscriptionModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        subscriptions = [self._to_entity(model) for model in models]

        return subscriptions, total_count

    async def update(self, subscription: Subscription) -> Subscription:
        query = select(SubscriptionModel).where(
            and_(
                SubscriptionModel.id == subscription.id,
                SubscriptionModel.user_id == subscription.user_id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return await self.save(subscription)

        model.plan_id = subscription.plan_id
        model.provider_connection_id = subscription.provider_connection_id
        model.name = subscription.name
        model.status = SubscriptionModelStatus(subscription.status.value)
        model.started_at = subscription.started_at
        model.renewal_at = subscription.renewal_at
        model.ended_at = subscription.ended_at
        model.updated_at = subscription.updated_at

        await self.session.commit()
        await self.session.refresh(model)

        return self._to_entity(model)

    async def soft_delete(
        self,
        subscription_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        query = select(SubscriptionModel).where(
            and_(
                SubscriptionModel.id == subscription_id,
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )

        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model is None:
            return False

        now = datetime.now(UTC)

        model.deleted_at = now
        model.updated_at = now

        await self.session.commit()

        return True
