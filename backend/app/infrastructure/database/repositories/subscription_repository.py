import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.subscriptions.entities import Subscription, PlanAlternative, BillingCadence, SubscriptionStatus
from app.domain.subscriptions.repositories import SubscriptionRepository
from app.infrastructure.database.models.subscription import SubscriptionModel


class SqlAlchemySubscriptionRepository(SubscriptionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_entity(self, model: SubscriptionModel) -> Subscription:
        plan_alts = [
            PlanAlternative(
                name=alt["name"],
                price=alt["price"],
                currency=alt["currency"],
                billing_cadence=BillingCadence(alt["billing_cadence"]),
                notes=alt.get("notes"),
            )
            for alt in (model.plan_alternatives or [])
        ]
        return Subscription(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            price=model.price,
            currency=model.currency,
            billing_cadence=BillingCadence(model.billing_cadence),
            renewal_date=model.renewal_date,
            status=SubscriptionStatus(model.status),
            plan_alternatives=plan_alts,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    def _to_model(self, entity: Subscription) -> SubscriptionModel:
        plan_alts = [
            {
                "name": alt.name,
                "price": alt.price,
                "currency": alt.currency,
                "billing_cadence": alt.billing_cadence.value,
                "notes": alt.notes,
            }
            for alt in entity.plan_alternatives
        ]
        return SubscriptionModel(
            id=entity.id,
            user_id=entity.user_id,
            name=entity.name,
            price=entity.price,
            currency=entity.currency,
            billing_cadence=entity.billing_cadence.value,
            renewal_date=entity.renewal_date,
            status=entity.status.value,
            plan_alternatives=plan_alts,
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

    async def get_by_id(self, subscription_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Subscription]:
        query = select(SubscriptionModel).where(
            and_(
                SubscriptionModel.id == subscription_id,
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
        status: Optional[SubscriptionStatus] = None,
    ) -> tuple[list[Subscription], int]:
        conditions = [
            SubscriptionModel.user_id == user_id,
            SubscriptionModel.deleted_at.is_(None),
        ]
        if status:
            conditions.append(SubscriptionModel.status == status.value)

        # Count total items
        count_stmt = select(func.count()).select_from(SubscriptionModel).where(and_(*conditions))
        count_res = await self.session.execute(count_stmt)
        total_count = count_res.scalar_one()

        # Fetch page items
        query = (
            select(SubscriptionModel)
            .where(and_(*conditions))
            .offset(skip)
            .limit(limit)
            .order_by(SubscriptionModel.created_at.desc())
        )
        results = await self.session.execute(query)
        models = results.scalars().all()

        return [self._to_entity(m) for m in models], total_count

    async def update(self, subscription: Subscription) -> Subscription:
        query = select(SubscriptionModel).where(
            and_(
                SubscriptionModel.id == subscription.id,
                SubscriptionModel.user_id == subscription.user_id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )
        res = await self.session.execute(query)
        model = res.scalar_one_or_none()

        if not model:
            return await self.save(subscription)

        model.name = subscription.name
        model.price = subscription.price
        model.currency = subscription.currency
        model.billing_cadence = subscription.billing_cadence.value
        model.renewal_date = subscription.renewal_date
        model.status = subscription.status.value
        model.plan_alternatives = [
            {
                "name": alt.name,
                "price": alt.price,
                "currency": alt.currency,
                "billing_cadence": alt.billing_cadence.value,
                "notes": alt.notes,
            }
            for alt in subscription.plan_alternatives
        ]
        model.updated_at = subscription.updated_at

        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def soft_delete(self, subscription_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        query = select(SubscriptionModel).where(
            and_(
                SubscriptionModel.id == subscription_id,
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.deleted_at.is_(None),
            )
        )
        res = await self.session.execute(query)
        model = res.scalar_one_or_none()

        if not model:
            return False

        model.deleted_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True 