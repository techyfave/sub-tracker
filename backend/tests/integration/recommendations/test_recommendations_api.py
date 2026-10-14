from __future__ import annotations  # allow modern type hints

import uuid  # unique ids
from datetime import UTC, datetime  # timestamps
from decimal import Decimal  # exact numbers

from httpx import AsyncClient  # test client
from sqlalchemy import select  # query builder
from sqlalchemy.ext.asyncio import AsyncSession  # async DB session

from app.infrastructure.database.models import (  # DB models and enums
    AnalysisModel,  # analyses table
    PlanModel,  # plans table
    PromptVersionModel,  # prompt versions table
    ProviderModel,  # providers table
    RecommendationAction,  # action enum
    RecommendationEvidenceModel,  # evidence table
    RecommendationModel,  # recommendations table
    SubscriptionModel,  # subscriptions table
    SubscriptionStatus,  # subscription status enum
    UserModel,  # users table
    WorkStatus,  # analysis status enum
)

REGISTER_PATH = "/api/v1/auth/register"  # register route
LOGIN_PATH = "/api/v1/auth/login"  # login route
RECOMMENDATIONS_PATH = "/api/v1/recommendations"  # route under test
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)  # fixed timestamp for test rows


async def _register_and_login(client: AsyncClient, *, email: str) -> dict[str, str]:
    # register a new user
    registered = await client.post(
        REGISTER_PATH, json={"email": email, "password": "correct-horse"}
    )
    # registration must succeed
    assert registered.status_code == 201, registered.text
    # log in
    login = await client.post(LOGIN_PATH, json={"email": email, "password": "correct-horse"})
    # login must succeed
    assert login.status_code == 200, login.text
    # return ready-to-use auth headers
    return {"Authorization": f"Bearer {login.json()['tokens']['access_token']}"}


async def _user_id(db_session: AsyncSession, email: str) -> uuid.UUID:
    # look the user up by email
    result = await db_session.execute(select(UserModel.id).where(UserModel.email == email))
    # return the id
    return result.scalar_one()


async def _seed_recommendation(
    db_session: AsyncSession,
    *,
    owner_id: uuid.UUID,  # who owns the rows
    action: RecommendationAction = RecommendationAction.KEEP,  # recommended action
    analysis_status: WorkStatus = WorkStatus.SUCCEEDED,  # analysis state
) -> uuid.UUID:
    # unique suffix so repeated calls never collide on unique columns
    suffix = uuid.uuid4().hex[:8]
    # provider
    provider = ProviderModel(
        id=uuid.uuid4(),
        slug=f"prov-{suffix}",
        display_name="Test Provider",
        created_at=NOW,
        updated_at=NOW,
    )
    # stage and write the provider first
    db_session.add(provider)
    await db_session.flush()
    # plan
    plan = PlanModel(
        id=uuid.uuid4(),
        provider_id=provider.id,
        external_reference=f"plan-{suffix}",
        name="Test Plan",
        amount=Decimal("6000.00"),
        currency="NGN",
        billing_interval="monthly",
        created_at=NOW,
        updated_at=NOW,
    )
    # stage and write the plan
    db_session.add(plan)
    await db_session.flush()
    # subscription
    subscription = SubscriptionModel(
        id=uuid.uuid4(),
        user_id=owner_id,
        plan_id=plan.id,
        name=f"Sub {suffix}",
        status=SubscriptionStatus.ACTIVE,
        started_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    # prompt version
    prompt = PromptVersionModel(
        id=uuid.uuid4(),
        name="test-prompt",
        version=suffix,
        schema_version="1.0",
        template="test template",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    # stage both and write them
    db_session.add_all([subscription, prompt])
    await db_session.flush()
    # analysis that carries internal fields which must never leak
    analysis = AnalysisModel(
        id=uuid.uuid4(),
        user_id=owner_id,
        subscription_id=subscription.id,
        prompt_version_id=prompt.id,
        status=analysis_status,
        idempotency_key=f"secret-key-{suffix}",
        attempt_count=3,
        failure_code="internal-code",
        started_at=NOW,
        completed_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    # stage and write the analysis
    db_session.add(analysis)
    await db_session.flush()
    # recommendation snapshot
    recommendation = RecommendationModel(
        id=uuid.uuid4(),
        user_id=owner_id,
        analysis_id=analysis.id,
        version=1,
        recommended_action=action,
        confidence=Decimal("0.9100"),
        rationale="Test rationale.",
        uncertainty_json={"level": "low"},
        monthly_savings_amount=Decimal("4000.00"),
        annual_savings_amount=Decimal("48000.00"),
        currency="NGN",
        prompt_version="1.0.0",
        schema_version="1.0",
        created_at=NOW,
    )
    # stage and write the recommendation
    db_session.add(recommendation)
    await db_session.flush()
    # one piece of evidence
    evidence = RecommendationEvidenceModel(
        id=uuid.uuid4(),
        user_id=owner_id,
        recommendation_id=recommendation.id,
        evidence_type="usage",
        source_table="usage_events",
        source_id=uuid.uuid4(),
        snapshot_json={"sessions": 4},
        created_at=NOW,
    )
    # stage the evidence and save everything
    db_session.add(evidence)
    await db_session.commit()
    # return the recommendation id
    return recommendation.id


async def test_requires_authentication(client: AsyncClient) -> None:
    # list without a token
    assert (await client.get(RECOMMENDATIONS_PATH)).status_code == 401
    # detail without a token
    assert (await client.get(f"{RECOMMENDATIONS_PATH}/{uuid.uuid4()}")).status_code == 401


async def test_list_contract_and_no_internal_fields(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # sign in and find the user id
    headers = await _register_and_login(client, email="rec-contract@example.com")
    owner_id = await _user_id(db_session, "rec-contract@example.com")
    # create one recommendation for them
    await _seed_recommendation(db_session, owner_id=owner_id)
    # call the list endpoint
    response = await client.get(RECOMMENDATIONS_PATH, headers=headers)
    # must succeed
    assert response.status_code == 200, response.text
    body = response.json()
    # pagination envelope
    assert body["pagination"]["total_items"] == 1
    assert body["pagination"]["page"] == 1
    # one item
    item = body["items"][0]
    # exact set of fields, so nothing internal can slip in
    assert set(item) == {
        "id",
        "recommended_action",
        "rationale",
        "versions",
        "analysis",
        "uncertainty",
        "savings",
        "evidence",
        "created_at",
    }
    # version information
    assert item["versions"] == {
        "recommendation_version": 1,
        "prompt_version": "1.0.0",
        "schema_version": "1.0",
    }
    # analysis state, without internal fields
    assert item["analysis"]["status"] == WorkStatus.SUCCEEDED.value
    assert set(item["analysis"]) == {"analysis_id", "subscription_id", "status", "completed_at"}
    # uncertainty
    assert Decimal(item["uncertainty"]["confidence"]) == Decimal("0.91")
    assert item["uncertainty"]["details"] == {"level": "low"}
    # deterministic savings
    assert Decimal(item["savings"]["monthly"]["amount"]) == Decimal("4000")
    assert Decimal(item["savings"]["annual"]["amount"]) == Decimal("48000")
    assert item["savings"]["monthly"]["currency"] == "NGN"
    # evidence provenance
    assert item["evidence"][0]["source_table"] == "usage_events"
    assert item["evidence"][0]["evidence_type"] == "usage"
    # internal values never appear anywhere in the response text
    assert "secret-key" not in response.text
    assert "internal-code" not in response.text
    assert "idempotency_key" not in response.text


async def test_detail_returns_recommendation(client: AsyncClient, db_session: AsyncSession) -> None:
    # sign in and create a recommendation
    headers = await _register_and_login(client, email="rec-detail@example.com")
    owner_id = await _user_id(db_session, "rec-detail@example.com")
    recommendation_id = await _seed_recommendation(db_session, owner_id=owner_id)
    # fetch it by id
    response = await client.get(f"{RECOMMENDATIONS_PATH}/{recommendation_id}", headers=headers)
    # must succeed
    assert response.status_code == 200, response.text
    # right record, with its evidence
    assert response.json()["id"] == str(recommendation_id)
    assert len(response.json()["evidence"]) == 1


async def test_user_cannot_see_another_users_recommendation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # two users
    await _register_and_login(client, email="rec-owner@example.com")
    other_headers = await _register_and_login(client, email="rec-other@example.com")
    owner_id = await _user_id(db_session, "rec-owner@example.com")
    # the owner has a recommendation
    recommendation_id = await _seed_recommendation(db_session, owner_id=owner_id)
    # the other user sees an empty list
    listed = await client.get(RECOMMENDATIONS_PATH, headers=other_headers)
    assert listed.json()["pagination"]["total_items"] == 0
    # the other user gets 404 on the owner's id
    detail = await client.get(f"{RECOMMENDATIONS_PATH}/{recommendation_id}", headers=other_headers)
    assert detail.status_code == 404, detail.text


async def test_unknown_id_returns_404(client: AsyncClient) -> None:
    # sign in
    headers = await _register_and_login(client, email="rec-unknown@example.com")
    # ask for an id that does not exist
    response = await client.get(f"{RECOMMENDATIONS_PATH}/{uuid.uuid4()}", headers=headers)
    # Problem Details 404
    assert response.status_code == 404, response.text
    assert response.json()["type"].endswith("not-found")


async def test_filters_by_action_and_analysis_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # sign in and create two different recommendations
    headers = await _register_and_login(client, email="rec-filter@example.com")
    owner_id = await _user_id(db_session, "rec-filter@example.com")
    await _seed_recommendation(
        db_session,
        owner_id=owner_id,
        action=RecommendationAction.KEEP,
        analysis_status=WorkStatus.SUCCEEDED,
    )
    await _seed_recommendation(
        db_session,
        owner_id=owner_id,
        action=RecommendationAction.CANCEL,
        analysis_status=WorkStatus.QUEUED,
    )
    # filter by action
    by_action = await client.get(
        RECOMMENDATIONS_PATH,
        headers=headers,
        params={"action": RecommendationAction.CANCEL.value},
    )
    assert by_action.json()["pagination"]["total_items"] == 1
    assert by_action.json()["items"][0]["recommended_action"] == RecommendationAction.CANCEL.value
    # filter by analysis status
    by_status = await client.get(
        RECOMMENDATIONS_PATH, headers=headers, params={"status": WorkStatus.SUCCEEDED.value}
    )
    assert by_status.json()["pagination"]["total_items"] == 1
    assert by_status.json()["items"][0]["analysis"]["status"] == WorkStatus.SUCCEEDED.value
    # filter by subscription id
    subscription_id = by_status.json()["items"][0]["analysis"]["subscription_id"]
    by_subscription = await client.get(
        RECOMMENDATIONS_PATH, headers=headers, params={"subscription_id": subscription_id}
    )
    assert by_subscription.json()["pagination"]["total_items"] == 1
    # an invalid filter value is a validation error
    invalid = await client.get(RECOMMENDATIONS_PATH, headers=headers, params={"action": "nonsense"})
    assert invalid.status_code == 422


async def test_pagination(client: AsyncClient, db_session: AsyncSession) -> None:
    # sign in and create three recommendations
    headers = await _register_and_login(client, email="rec-page@example.com")
    owner_id = await _user_id(db_session, "rec-page@example.com")
    for _ in range(3):
        await _seed_recommendation(db_session, owner_id=owner_id)
    # first page of two
    first = await client.get(RECOMMENDATIONS_PATH, headers=headers, params={"page_size": 2})
    assert len(first.json()["items"]) == 2
    assert first.json()["pagination"]["total_items"] == 3
    assert first.json()["pagination"]["total_pages"] == 2
    # second page of one
    second = await client.get(
        RECOMMENDATIONS_PATH, headers=headers, params={"page_size": 2, "page": 2}
    )
    assert len(second.json()["items"]) == 1
    # no recommendation appears on both pages
    first_ids = {item["id"] for item in first.json()["items"]}
    assert second.json()["items"][0]["id"] not in first_ids
