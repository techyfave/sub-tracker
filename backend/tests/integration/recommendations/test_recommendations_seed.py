import uuid  # unique ids
from decimal import Decimal  # exact numbers

from sqlalchemy.ext.asyncio import AsyncSession  # async DB session

from app.application.recommendations.service import RecommendationService  # business logic
from app.infrastructure.database import seed  # deterministic demo data and its ids
from app.infrastructure.database.repositories.recommendation_read_repository import (
    SqlAlchemyRecommendationReadRepository,  # read-only storage under test
)

# the recommendations each seeded user owns, taken from the seed module
KEEP_USER_IDS = {
    seed.KEEP_RECOMMENDATION_ID,  # keep scenario
    seed.DOWNGRADE_RECOMMENDATION_ID,  # downgrade scenario
    seed.CANCEL_RECOMMENDATION_ID,  # cancel scenario
}
REVIEW_USER_IDS = {
    seed.REVIEW_RECOMMENDATION_ID,  # review scenario
    seed.MISSING_USAGE_RECOMMENDATION_ID,  # missing usage scenario
    seed.CONFLICTING_EVIDENCE_RECOMMENDATION_ID,  # conflicting evidence scenario
}


async def _repository(db_session: AsyncSession) -> SqlAlchemyRecommendationReadRepository:
    # load the demo data into the test database
    await seed.seed_demo_data(db_session)
    # build the repository on the same session
    return SqlAlchemyRecommendationReadRepository(db_session)


async def test_each_seeded_user_sees_exactly_their_own_recommendations(
    db_session: AsyncSession,
) -> None:
    # load the seed and build the repository
    repository = await _repository(db_session)
    # first seeded user
    keep_items, keep_total = await repository.list_by_user(user_id=seed.KEEP_USER_ID)
    # second seeded user
    review_items, review_total = await repository.list_by_user(user_id=seed.REVIEW_USER_ID)
    # each user sees exactly three
    assert keep_total == 3
    assert review_total == 3
    # and exactly their own records, with no overlap
    assert {item.id for item in keep_items} == KEEP_USER_IDS
    assert {item.id for item in review_items} == REVIEW_USER_IDS
    # a user with no data sees nothing
    _, stranger_total = await repository.list_by_user(user_id=uuid.uuid4())
    assert stranger_total == 0


async def test_seeded_recommendation_is_not_visible_to_another_user(
    db_session: AsyncSession,
) -> None:
    # load the seed and build the repository
    repository = await _repository(db_session)
    # the owner can read their own recommendation
    own = await repository.get_by_id(seed.KEEP_RECOMMENDATION_ID, seed.KEEP_USER_ID)
    assert own is not None
    # the other seeded user cannot read it
    foreign = await repository.get_by_id(seed.KEEP_RECOMMENDATION_ID, seed.REVIEW_USER_ID)
    assert foreign is None


async def test_downgrade_detail_has_versions_savings_and_evidence(
    db_session: AsyncSession,
) -> None:
    # load the seed and build the repository
    repository = await _repository(db_session)
    # fetch the downgrade scenario as its owner
    item = await repository.get_by_id(seed.DOWNGRADE_RECOMMENDATION_ID, seed.KEEP_USER_ID)
    # it must exist
    assert item is not None
    # action and version information
    assert item.recommended_action == "downgrade"
    assert item.version == 1
    assert item.prompt_version == "1.0.0"
    assert item.schema_version == "1.0"
    # analysis state
    assert item.analysis_status == "succeeded"
    # deterministic savings
    assert item.monthly_savings_amount == Decimal("4000")
    assert item.annual_savings_amount == Decimal("48000")
    assert item.currency == "NGN"
    # evidence provenance points back to the usage event
    assert len(item.evidence) == 1
    assert item.evidence[0].source_table == "usage_events"
    assert item.evidence[0].evidence_type == "usage"
    assert item.evidence[0].snapshot["lower_tier_suitable"] is True


async def test_uncertain_scenarios_expose_their_uncertainty(db_session: AsyncSession) -> None:
    # load the seed and build the repository
    repository = await _repository(db_session)
    # missing usage must be reported as uncertain, not as proof of non-use
    missing = await repository.get_by_id(seed.MISSING_USAGE_RECOMMENDATION_ID, seed.REVIEW_USER_ID)
    assert missing is not None
    assert missing.recommended_action == "review"
    assert missing.uncertainty["reason"] == "missing_usage"
    # conflicting evidence must be flagged in the evidence snapshot
    conflicting = await repository.get_by_id(
        seed.CONFLICTING_EVIDENCE_RECOMMENDATION_ID, seed.REVIEW_USER_ID
    )
    assert conflicting is not None
    assert conflicting.uncertainty["reason"] == "conflicting_evidence"
    assert conflicting.evidence[0].evidence_type == "conflict"
    assert conflicting.evidence[0].snapshot["conflict"] is True


async def test_seed_filters_by_action_and_status(db_session: AsyncSession) -> None:
    # load the seed and build the repository
    repository = await _repository(db_session)
    # the review user has three "review" recommendations
    _, review_count = await repository.list_by_user(seed.REVIEW_USER_ID, action="review")
    assert review_count == 3
    # and no "cancel" ones
    _, cancel_count = await repository.list_by_user(seed.REVIEW_USER_ID, action="cancel")
    assert cancel_count == 0
    # the keep user has exactly one "cancel"
    cancel_items, _ = await repository.list_by_user(seed.KEEP_USER_ID, action="cancel")
    assert [item.id for item in cancel_items] == [seed.CANCEL_RECOMMENDATION_ID]
    # every seeded analysis succeeded
    _, succeeded = await repository.list_by_user(seed.KEEP_USER_ID, status="succeeded")
    assert succeeded == 3
    # and none are queued
    _, queued = await repository.list_by_user(seed.KEEP_USER_ID, status="queued")
    assert queued == 0


async def test_service_scopes_the_list_to_the_current_user(db_session: AsyncSession) -> None:
    # load the seed and build the service on the real repository
    repository = await _repository(db_session)
    service = RecommendationService(repository)

    # a minimal stand-in for the logged-in user; the service only reads its id
    class _CurrentUser:
        id = seed.REVIEW_USER_ID

    # list through the service
    items, total = await service.list_recommendations(current_user=_CurrentUser())  # type: ignore[arg-type]
    # only the review user's records come back
    assert total == 3
    assert {item.id for item in items} == REVIEW_USER_IDS
