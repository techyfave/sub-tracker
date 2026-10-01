import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.subscriptions.entities import BillingCadence, Plan, Subscription, SubscriptionStatus
from app.domain.subscriptions.exceptions import (
    InvalidSubscriptionReferenceError,
    SubscriptionNotFoundError,
)
from app.domain.subscriptions.repositories import SubscriptionRepository
from app.infrastructure.database.models.core import (
    PlanModel,
    ProviderConnectionModel,
    ProviderModel,
    SubscriptionAlternativeModel,
    SubscriptionModel,
)
from app.infrastructure.database.models.core import (
    SubscriptionStatus as SubscriptionModelStatus,
)


class SqlAlchemySubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _plan_entity(model: PlanModel) -> Plan:
        return Plan(
            id=model.id,
            provider_id=model.provider_id,
            name=model.name,
            amount=model.amount,
            currency=model.currency,
            billing_interval=BillingCadence(model.billing_interval),
        )

    async def _to_entity(self, model: SubscriptionModel) -> Subscription:
        plan = await self.session.get(PlanModel, model.plan_id)
        if plan is None:
            raise InvalidSubscriptionReferenceError("Plan is unavailable")
        alternatives = (
            await self.session.scalars(
                select(PlanModel)
                .join(
                    SubscriptionAlternativeModel,
                    SubscriptionAlternativeModel.plan_id == PlanModel.id,
                )
                .where(SubscriptionAlternativeModel.subscription_id == model.id)
                .order_by(PlanModel.id)
            )
        ).all()
        return Subscription(
            plan=self._plan_entity(plan),
            plan_alternatives=[self._plan_entity(alt) for alt in alternatives],
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

    async def _persist_plan(self, plan: Plan) -> None:
        if await self.session.get(PlanModel, plan.id) is None:
            self.session.add(
                PlanModel(
                    id=plan.id,
                    provider_id=plan.provider_id,
                    external_reference=f"manual:{plan.id}",
                    name=plan.name,
                    amount=plan.amount,
                    currency=plan.currency,
                    billing_interval=plan.billing_interval.value,
                )
            )
            await self.session.flush()

    async def _validate_references(self, subscription: Subscription) -> None:
        # Validate everything before writing any plan or association.
        plan = await self.session.get(PlanModel, subscription.plan_id)
        if subscription.plan is None and plan is None:
            raise InvalidSubscriptionReferenceError("Plan is unavailable")
        provider_id = subscription.plan.provider_id if subscription.plan else None
        if plan is not None:
            provider_id = plan.provider_id
            try:
                BillingCadence(plan.billing_interval)
            except ValueError as exc:
                raise InvalidSubscriptionReferenceError("Plan cadence is unsupported") from exc
        for candidate in (
            [subscription.plan] if subscription.plan else []
        ) + subscription.plan_alternatives:
            if await self.session.get(ProviderModel, candidate.provider_id) is None:
                raise InvalidSubscriptionReferenceError("Provider is unavailable")
        if subscription.provider_connection_id is not None:
            connection = await self.session.scalar(
                select(ProviderConnectionModel).where(
                    ProviderConnectionModel.id == subscription.provider_connection_id,
                    ProviderConnectionModel.user_id == subscription.user_id,
                )
            )
            if connection is None or connection.provider_id != provider_id:
                raise InvalidSubscriptionReferenceError("Provider connection is unavailable")

    async def _persist_plans(self, subscription: Subscription) -> None:
        if subscription.plan is not None:
            await self._persist_plan(subscription.plan)
        for plan in subscription.plan_alternatives:
            await self._persist_plan(plan)

    async def _replace_alternatives(self, subscription: Subscription) -> None:
        await self.session.execute(
            delete(SubscriptionAlternativeModel).where(
                SubscriptionAlternativeModel.subscription_id == subscription.id
            )
        )
        for plan in subscription.plan_alternatives:
            self.session.add(
                SubscriptionAlternativeModel(subscription_id=subscription.id, plan_id=plan.id)
            )

    async def save(self, subscription: Subscription) -> Subscription:
        await self._validate_references(subscription)
        await self._persist_plans(subscription)
        model = self._to_model(subscription)

        self.session.add(model)
        await self.session.flush()
        await self._replace_alternatives(subscription)
        await self.session.commit()
        await self.session.refresh(model)

        return await self._to_entity(model)

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

        return await self._to_entity(model)

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
            .order_by(SubscriptionModel.created_at.desc(), SubscriptionModel.id.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        subscriptions = [await self._to_entity(model) for model in models]

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
            raise SubscriptionNotFoundError(str(subscription.id))

        await self._validate_references(subscription)
        await self._persist_plans(subscription)
        await self._replace_alternatives(subscription)
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

        return await self._to_entity(model)

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
