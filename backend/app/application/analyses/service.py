"""Analysis creation and durable outbox, committed by the request session."""

from uuid import UUID, uuid4

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.jobs import IdempotencyConflict, JobRequest
from app.infrastructure.database.models.core import (
    AnalysisModel,
    PromptVersionModel,
    SubscriptionModel,
    TransactionModel,
    UsageEventModel,
    WorkStatus,
)
from app.infrastructure.database.repositories.jobs import PostgresJobRepository


class AnalysisInputError(ValueError):
    pass


async def create_analysis(
    session: AsyncSession,
    user_id: UUID,
    subscription_id: UUID,
    key: str,
) -> AnalysisModel:
    existing = await session.scalar(
        select(AnalysisModel).where(
            AnalysisModel.user_id == user_id,
            AnalysisModel.idempotency_key == key,
        )
    )
    if existing is not None:
        if existing.subscription_id != subscription_id:
            raise IdempotencyConflict("Key already used for another subscription")
        return existing
    subscription = await session.scalar(
        select(SubscriptionModel).where(
            SubscriptionModel.id == subscription_id,
            SubscriptionModel.user_id == user_id,
            SubscriptionModel.deleted_at.is_(None),
        )
    )
    if subscription is None:
        raise LookupError("Subscription not found")
    has_evidence = any(
        [
            await session.scalar(
                select(
                    exists().where(
                        model.subscription_id == subscription_id,
                        model.user_id == user_id,
                    )
                )
            )
            for model in (TransactionModel, UsageEventModel)
        ]
    )
    if not has_evidence:
        raise AnalysisInputError("Stored billing or usage evidence is required")
    prompt = await session.scalar(
        select(PromptVersionModel)
        .where(
            PromptVersionModel.is_active.is_(True),
            PromptVersionModel.name == "subscription-recommendation",
        )
        .order_by(PromptVersionModel.created_at.desc(), PromptVersionModel.id)
        .limit(1)
    )
    if prompt is None:
        raise AnalysisInputError("No active analysis prompt is configured")
    analysis = AnalysisModel(
        id=uuid4(),
        user_id=user_id,
        subscription_id=subscription_id,
        prompt_version_id=prompt.id,
        status=WorkStatus.QUEUED,
        idempotency_key=key,
    )
    try:
        async with session.begin_nested():
            session.add(analysis)
            await session.flush()
    except IntegrityError:
        existing = await session.scalar(
            select(AnalysisModel).where(
                AnalysisModel.user_id == user_id,
                AnalysisModel.idempotency_key == key,
            )
        )
        if existing is None:
            raise
        if existing.subscription_id != subscription_id:
            raise IdempotencyConflict("Key already used for another subscription") from None
        return existing
    await PostgresJobRepository(session).enqueue(
        JobRequest(
            user_id,
            "analysis.run",
            key,
            {"analysis_id": str(analysis.id)},
        )
    )
    return analysis
