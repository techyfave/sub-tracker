import uuid
from decimal import Decimal

from sqlalchemy import func, select

from app.infrastructure.database import seed
from app.infrastructure.database.base import Base
from app.infrastructure.database.models.core import (
    ActionModel,
    RecommendationAction,
    RecommendationEvidenceModel,
    RecommendationModel,
    SavingsKind,
    SavingsRecordModel,
    UsageEventModel,
    WorkStatus,
)


async def _count_recommendations(session) -> int:
    result = await session.execute(select(func.count(RecommendationModel.id)))
    return result.scalar_one()


async def _table_counts(session) -> dict[str, int]:
    counts = {}

    for table in Base.metadata.sorted_tables:
        result = await session.execute(select(func.count()).select_from(table))
        counts[table.name] = result.scalar_one()

    return counts


async def test_seed_loads_all_scenarios(db_session):
    await seed.seed_demo_data(db_session)

    result = await db_session.execute(
        select(RecommendationModel).order_by(RecommendationModel.id)
    )
    recommendations = result.scalars().all()

    assert len(recommendations) == 6

    recommendations_by_id = {
        recommendation.id: recommendation for recommendation in recommendations
    }

    keep = recommendations_by_id[seed.KEEP_RECOMMENDATION_ID]
    downgrade = recommendations_by_id[seed.DOWNGRADE_RECOMMENDATION_ID]
    cancel = recommendations_by_id[seed.CANCEL_RECOMMENDATION_ID]
    review = recommendations_by_id[seed.REVIEW_RECOMMENDATION_ID]
    missing_usage = recommendations_by_id[seed.MISSING_USAGE_RECOMMENDATION_ID]
    conflicting = recommendations_by_id[
        seed.CONFLICTING_EVIDENCE_RECOMMENDATION_ID
    ]

    assert keep.recommended_action == RecommendationAction.KEEP
    assert keep.monthly_savings_amount == Decimal("0")
    assert keep.annual_savings_amount == Decimal("0")
    assert keep.currency == "NGN"

    assert downgrade.recommended_action == RecommendationAction.DOWNGRADE
    assert downgrade.monthly_savings_amount == Decimal("4000")
    assert downgrade.annual_savings_amount == Decimal("48000")
    assert downgrade.currency == "NGN"

    assert cancel.recommended_action == RecommendationAction.CANCEL

    assert review.recommended_action == RecommendationAction.REVIEW
    assert review.monthly_savings_amount == Decimal("0")
    assert review.annual_savings_amount == Decimal("0")

    assert missing_usage.recommended_action == RecommendationAction.REVIEW
    assert missing_usage.monthly_savings_amount == Decimal("0")
    assert missing_usage.annual_savings_amount == Decimal("0")

    assert conflicting.recommended_action == RecommendationAction.REVIEW
    assert conflicting.monthly_savings_amount == Decimal("0")
    assert conflicting.annual_savings_amount == Decimal("0")


async def test_missing_usage_is_distinguished_from_confirmed_zero_usage(db_session):
    await seed.seed_demo_data(db_session)

    result = await db_session.execute(
        select(UsageEventModel).where(
            UsageEventModel.subscription_id == seed.CANCEL_SUBSCRIPTION_ID
        )
    )
    cancel_usage = result.scalar_one()

    result = await db_session.execute(
        select(UsageEventModel).where(
            UsageEventModel.subscription_id == seed.MISSING_USAGE_SUBSCRIPTION_ID
        )
    )
    missing_usage = result.scalar_one()

    assert cancel_usage.quantity == Decimal("0")
    assert cancel_usage.is_unknown is False

    assert missing_usage.quantity is None
    assert missing_usage.is_unknown is True

    assert cancel_usage.is_unknown != missing_usage.is_unknown


async def test_conflicting_evidence_requires_review(db_session):
    await seed.seed_demo_data(db_session)

    result = await db_session.execute(
        select(RecommendationModel).where(
            RecommendationModel.id == seed.CONFLICTING_EVIDENCE_RECOMMENDATION_ID
        )
    )
    recommendation = result.scalar_one()

    assert recommendation.recommended_action == RecommendationAction.REVIEW

    result = await db_session.execute(
        select(RecommendationEvidenceModel).where(
            RecommendationEvidenceModel.recommendation_id
            == seed.CONFLICTING_EVIDENCE_RECOMMENDATION_ID
        )
    )
    evidence = result.scalar_one()

    assert evidence.evidence_type == "conflict"
    assert evidence.snapshot_json["conflict"] is True
    assert evidence.snapshot_json["requires_review"] is True


async def test_downgrade_savings_remain_estimated_until_action_is_verified(
    db_session,
):
    await seed.seed_demo_data(db_session)

    result = await db_session.execute(
        select(ActionModel).where(
            ActionModel.id == uuid.UUID("63000000-0000-4000-8000-000000000002")
        )
    )
    downgrade_action = result.scalar_one()

    assert downgrade_action.status == WorkStatus.QUEUED
    assert downgrade_action.action_type == "downgrade"
    assert downgrade_action.attempt_count == 0

    result = await db_session.execute(
        select(SavingsRecordModel).where(
            SavingsRecordModel.recommendation_id
            == seed.DOWNGRADE_RECOMMENDATION_ID
        )
    )
    savings_records = result.scalars().all()

    assert len(savings_records) == 1

    savings = savings_records[0]

    assert savings.kind == SavingsKind.ESTIMATED
    assert savings.amount == Decimal("4000")
    assert savings.currency == "NGN"
    assert savings.period == "monthly"
    assert savings.action_id is None


async def test_seed_is_idempotent_across_all_tables(db_session):
    await seed.seed_demo_data(db_session)
    await db_session.commit()

    first_counts = await _table_counts(db_session)
    first_recommendation_count = await _count_recommendations(db_session)

    first_ids = {}
    for table in Base.metadata.sorted_tables:
        if "id" in table.c:
            result = await db_session.execute(select(table.c.id))
            first_ids[table.name] = set(result.scalars().all())

    await seed.seed_demo_data(db_session)
    await db_session.commit()

    second_counts = await _table_counts(db_session)
    second_recommendation_count = await _count_recommendations(db_session)

    second_ids = {}
    for table in Base.metadata.sorted_tables:
        if "id" in table.c:
            result = await db_session.execute(select(table.c.id))
            second_ids[table.name] = set(result.scalars().all())

    assert first_counts == second_counts
    assert first_ids == second_ids
    assert first_recommendation_count == 6
    assert second_recommendation_count == first_recommendation_count