from decimal import Decimal

from sqlalchemy import func, select

from app.infrastructure.database import seed
from app.infrastructure.database.models.core import (
    RecommendationAction,
    RecommendationModel,
)


async def _count_recommendations(session) -> int:
    result = await session.execute(select(func.count(RecommendationModel.id)))
    return result.scalar_one()


async def test_seed_loads_all_scenarios(db_session):
    await seed.seed_demo_data(db_session)

    result = await db_session.execute(
        select(RecommendationModel).order_by(RecommendationModel.id)
    )
    recommendations = result.scalars().all()

    assert len(recommendations) == 6

    actions = {recommendation.recommended_action for recommendation in recommendations}

    assert actions == {
        RecommendationAction.KEEP,
        RecommendationAction.DOWNGRADE,
        RecommendationAction.CANCEL,
        RecommendationAction.REVIEW,
    }

    downgrade = next(
        recommendation
        for recommendation in recommendations
        if recommendation.recommended_action == RecommendationAction.DOWNGRADE
    )

    assert downgrade.monthly_savings_amount == Decimal("4000")
    assert downgrade.annual_savings_amount == Decimal("48000")
    assert downgrade.currency == "NGN"


async def test_seed_is_idempotent(db_session):
    await seed.seed_demo_data(db_session)
    await db_session.commit()

    first_count = await _count_recommendations(db_session)

    await seed.seed_demo_data(db_session)

    second_count = await _count_recommendations(db_session)

    assert first_count == 6
    assert second_count == first_count
