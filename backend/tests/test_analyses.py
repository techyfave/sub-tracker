"""API, output validation and atomic worker regression tests for issue #13."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.v1.dependencies.auth import get_current_user
from app.application.analyses.pipeline import RecommendationDraft
from app.application.analyses.worker import run_analysis
from app.application.jobs import PermanentJobError, RetryableJobError
from app.domain.users.entities import User
from app.infrastructure.database import seed
from app.infrastructure.database.models.core import (
    RecommendationEvidenceModel,
    RecommendationModel,
    TransactionModel,
    UsageEventModel,
)
from app.infrastructure.database.models.job import JobModel
from app.infrastructure.jobs.runner import JobRunner
from app.main import app

PATH = "/api/v1/analyses"


@pytest.fixture
async def prepared(db_session):
    await seed.seed_demo_data(db_session)
    await db_session.commit()
    user = User(
        id=seed.KEEP_USER_ID,
        email="demo.keep@example.test",
        hashed_password="unused",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


async def create(client, key="request-13", subscription_id=seed.KEEP_SUBSCRIPTION_ID):
    return await client.post(
        PATH, json={"subscription_id": str(subscription_id)}, headers={"Idempotency-Key": key}
    )


async def test_create_poll_and_duplicate(client, db_session, prepared):
    first = await create(client)
    assert first.status_code == 202, first.text
    assert first.json()["status"] == "queued"
    assert (await client.get(first.headers["location"])).json() == first.json()
    assert (await create(client)).json()["id"] == first.json()["id"]
    assert await db_session.scalar(select(func.count()).select_from(JobModel)) == 1
    conflict = await create(client, subscription_id=seed.CANCEL_SUBSCRIPTION_ID)
    assert conflict.status_code == 409


async def test_ownership_and_missing_ids(client, prepared):
    assert (await create(client, subscription_id=uuid4())).status_code == 404
    first = await create(client)
    foreign = replace(prepared, id=seed.REVIEW_USER_ID)
    app.dependency_overrides[get_current_user] = lambda: foreign
    assert (await create(client, key="foreign")).status_code == 404
    assert (await client.get(first.headers["location"])).status_code == 404
    assert (await client.get(f"{PATH}/{uuid4()}")).status_code == 404


async def test_missing_evidence_and_input_validation(client, db_session, prepared):
    for model in (TransactionModel, UsageEventModel):
        await db_session.execute(
            delete(model).where(model.subscription_id == seed.KEEP_SUBSCRIPTION_ID)
        )
    await db_session.commit()
    assert (await create(client)).status_code == 422
    assert (
        await client.post(PATH, json={"subscription_id": str(seed.KEEP_SUBSCRIPTION_ID)})
    ).status_code == 422
    assert (await create(client, key="   ")).status_code == 422
    assert await db_session.scalar(select(func.count()).select_from(JobModel)) == 0


class FakePipeline:
    def __init__(self, action="keep", foreign_citation=False):
        self.action = action
        self.foreign_citation = foreign_citation
        self.context = None

    async def recommend(self, context):
        self.context = context
        return RecommendationDraft(
            action=self.action,
            confidence=Decimal("0.8"),
            rationale="Based on stored evidence",
            evidence_ids=[uuid4() if self.foreign_citation else context["evidence"][0]["id"]],
        )


async def test_worker_success_and_redelivery(client, db_session, prepared):
    created = await create(client)
    job = await db_session.scalar(select(JobModel))
    sessions = async_sessionmaker(db_session.bind, expire_on_commit=False)
    fake = FakePipeline()

    async def handler(session, job):
        await run_analysis(session, job, fake)

    runner = JobRunner(sessions, {"analysis.run": handler})
    await runner.execute(job.id)
    poll = await client.get(created.headers["location"])
    assert poll.json()["status"] == "completed", poll.text
    assert poll.json()["attempt_count"] == 1
    assert fake.context["features"]["monthly_cost"] is not None
    # Count only the newly created analysis, excluding the deterministic seed rows.
    analysis_id = UUID(created.json()["id"])
    recommendations = select(RecommendationModel).where(
        RecommendationModel.analysis_id == analysis_id
    )
    recommendation = await db_session.scalar(recommendations)
    assert recommendation.monthly_savings_amount == 0
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(RecommendationEvidenceModel)
            .where(RecommendationEvidenceModel.recommendation_id == recommendation.id)
        )
        > 0
    )
    await runner.execute(job.id)
    assert len((await db_session.scalars(recommendations)).all()) == 1


@pytest.mark.parametrize("failure", ["permanent", "retry", "unexpected", "bad_citation"])
async def test_failure_rolls_back_results(client, db_session, prepared, failure):
    created = await create(client)
    job = await db_session.scalar(select(JobModel))
    sessions = async_sessionmaker(db_session.bind, expire_on_commit=False)

    async def handler(session, job):
        await run_analysis(session, job, FakePipeline(foreign_citation=failure == "bad_citation"))
        if failure == "retry":
            raise RetryableJobError("secret-provider-detail")
        if failure == "unexpected":
            raise RuntimeError("secret-provider-detail")
        raise PermanentJobError("secret-provider-detail")

    await JobRunner(sessions, {"analysis.run": handler}).execute(job.id)
    poll = await client.get(created.headers["location"])
    assert poll.json()["status"] == ("queued" if failure == "retry" else "failed")
    assert poll.json()["failure_code"] is not None
    assert "secret-provider-detail" not in poll.text
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(RecommendationModel)
            .where(RecommendationModel.analysis_id == UUID(created.json()["id"]))
        )
        == 0
    )


async def test_worker_rejects_unsafe_cancel(client, db_session, prepared):
    await db_session.execute(
        delete(UsageEventModel).where(UsageEventModel.subscription_id == seed.KEEP_SUBSCRIPTION_ID)
    )
    await db_session.commit()
    created = await create(client)
    job = await db_session.scalar(select(JobModel))

    async def handler(session, job):
        await run_analysis(session, job, FakePipeline(action="cancel"))

    await JobRunner(
        async_sessionmaker(db_session.bind, expire_on_commit=False), {"analysis.run": handler}
    ).execute(job.id)
    assert (await client.get(created.headers["location"])).json()["status"] == "failed"


async def test_unauthenticated(client):
    assert (await create(client)).status_code == 401
    assert (await client.get(f"{PATH}/{uuid4()}")).status_code == 401


@pytest.mark.parametrize(
    "output",
    [
        {
            "action": "invented",
            "confidence": "0.8",
            "rationale": "Reason",
            "evidence_ids": [str(uuid4())],
        },
        {
            "action": "keep",
            "confidence": "1.1",
            "rationale": "Reason",
            "evidence_ids": [str(uuid4())],
        },
        {"action": "keep", "confidence": "0.8", "rationale": "Reason", "evidence_ids": []},
        {
            "action": "keep",
            "confidence": "0.8",
            "rationale": "Reason",
            "evidence_ids": [str(uuid4())],
            "monthly_savings": "9999",
        },
    ],
)
def test_output_schema_rejects_untrusted_fields(output):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RecommendationDraft.model_validate(output)


async def test_provider_configuration_failure(client, db_session, prepared, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "analysis_provider_url", "")
    created = await create(client)
    job = await db_session.scalar(select(JobModel))
    await JobRunner(
        async_sessionmaker(db_session.bind, expire_on_commit=False), {"analysis.run": run_analysis}
    ).execute(job.id)
    poll = await client.get(created.headers["location"])
    assert poll.json()["status"] == "failed"
    assert poll.json()["failure_code"] == "permanent"


async def test_exhausted_recovery_updates_analysis(client, db_session, prepared):
    from app.application.jobs import JobStatus

    created = await create(client)
    job = await db_session.scalar(select(JobModel))
    job.attempt_count = job.max_attempts
    job.status = JobStatus.QUEUED
    await db_session.commit()
    await JobRunner(async_sessionmaker(db_session.bind, expire_on_commit=False), {}).execute(job.id)
    poll = await client.get(created.headers["location"])
    assert poll.json()["status"] == "failed"
    assert poll.json()["failure_code"] == "attempts_exhausted"


@pytest.mark.parametrize("action", ["cancel", "downgrade", "review"])
async def test_worker_actions_and_deterministic_savings(client, db_session, prepared, action):
    from sqlalchemy import update

    from app.infrastructure.database.models.core import (
        SubscriptionAlternativeModel,
    )

    now = datetime.now(UTC)
    await db_session.execute(
        update(UsageEventModel)
        .where(
            UsageEventModel.subscription_id == seed.KEEP_SUBSCRIPTION_ID,
        )
        .values(occurred_at=now, quantity=0 if action == "cancel" else 2, is_unknown=False)
    )
    if action == "downgrade":
        db_session.add(
            SubscriptionAlternativeModel(
                subscription_id=seed.KEEP_SUBSCRIPTION_ID,
                plan_id=seed.BASIC_PLAN_ID,
            )
        )
    await db_session.commit()
    created = await create(client)
    job = await db_session.scalar(select(JobModel))

    class Pipeline(FakePipeline):
        async def recommend(self, context):
            draft = await super().recommend(context)
            if action == "downgrade":
                return draft.model_copy(update={"alternative_plan_id": seed.BASIC_PLAN_ID})
            return draft

    async def handler(session, job):
        await run_analysis(session, job, Pipeline(action=action))

    await JobRunner(
        async_sessionmaker(db_session.bind, expire_on_commit=False), {"analysis.run": handler}
    ).execute(job.id)
    poll = await client.get(created.headers["location"])
    assert poll.json()["status"] == "completed", poll.text
    row = await db_session.scalar(
        select(RecommendationModel).where(
            RecommendationModel.analysis_id == UUID(created.json()["id"])
        )
    )
    assert row.recommended_action.value == action
    targets = list(
        (
            await db_session.scalars(
                select(RecommendationEvidenceModel).where(
                    RecommendationEvidenceModel.recommendation_id == row.id,
                    RecommendationEvidenceModel.evidence_type == "selected_downgrade_target",
                )
            )
        ).all()
    )
    assert len(targets) == (1 if action == "downgrade" else 0)
    if targets:
        assert targets[0].source_id == seed.BASIC_PLAN_ID
    if action == "review":
        assert row.monthly_savings_amount == 0
    elif action == "cancel":
        assert row.monthly_savings_amount == Decimal("6000.00")
        assert row.annual_savings_amount == Decimal("72000.00")
    else:
        assert row.monthly_savings_amount == Decimal("3000.00")
        assert row.annual_savings_amount == Decimal("36000.00")


@pytest.mark.parametrize(
    "failure,expected",
    [
        (429, RetryableJobError),
        (500, RetryableJobError),
        (401, PermanentJobError),
        ("invalid", PermanentJobError),
        ("oversized", PermanentJobError),
    ],
)
async def test_http_provider_error_classification(monkeypatch, failure, expected):
    from urllib.error import HTTPError

    from app.application.analyses import pipeline
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "analysis_provider_url", "https://ai.example.test/analyse")
    monkeypatch.setattr(settings, "analysis_provider_token", "test-token")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return b"x" * 65537 if failure == "oversized" else b"{}"

    def send(*args, **kwargs):
        if isinstance(failure, int):
            raise HTTPError(settings.analysis_provider_url, failure, "private details", None, None)
        return Response()

    monkeypatch.setattr(pipeline, "urlopen", send)
    with pytest.raises(expected):
        await pipeline.HttpAnalysisPipeline().recommend({})


@pytest.mark.parametrize(
    "current_price,current_cadence,alternative_price,alternative_cadence,monthly,annual",
    [
        ("120.07", "yearly", "100.01", "yearly", "1.67", "20.06"),
        ("10.005", "monthly", "100.01", "yearly", "1.67", "20.05"),
        ("2.31", "weekly", "100.01", "yearly", "1.68", "20.11"),
        ("0.3333", "daily", "10.001", "monthly", "0.14", "1.64"),
        ("100.02", "yearly", "100.01", "yearly", "0.00", "0.01"),
        ("100.01", "yearly", "100.01", "yearly", None, None),
        ("100.00", "yearly", "100.01", "yearly", None, None),
        ("1.0001", "yearly", "1.0000", "yearly", None, None),
        ("120.07", "quarterly", "100.01", "yearly", None, None),
        ("120.07", "yearly", "100.01", "quarterly", None, None),
    ],
)
async def test_downgrade_rounds_exact_difference_once(
    client,
    db_session,
    prepared,
    current_price,
    current_cadence,
    alternative_price,
    alternative_cadence,
    monthly,
    annual,
):
    from sqlalchemy import update

    from app.infrastructure.database.models.core import PlanModel, SubscriptionAlternativeModel

    await db_session.execute(
        update(PlanModel)
        .where(PlanModel.id == seed.STANDARD_PLAN_ID)
        .values(
            amount=Decimal(current_price),
            billing_interval=current_cadence,
        )
    )
    await db_session.execute(
        update(PlanModel)
        .where(PlanModel.id == seed.BASIC_PLAN_ID)
        .values(
            amount=Decimal(alternative_price),
            billing_interval=alternative_cadence,
        )
    )
    await db_session.execute(
        update(UsageEventModel)
        .where(
            UsageEventModel.subscription_id == seed.KEEP_SUBSCRIPTION_ID,
        )
        .values(occurred_at=datetime.now(UTC), quantity=2, is_unknown=False)
    )
    db_session.add(
        SubscriptionAlternativeModel(
            subscription_id=seed.KEEP_SUBSCRIPTION_ID,
            plan_id=seed.BASIC_PLAN_ID,
        )
    )
    await db_session.commit()
    created = await create(client)
    assert created.status_code == 202, created.text
    job = await db_session.scalar(select(JobModel))

    class Pipeline(FakePipeline):
        async def recommend(self, context):
            draft = await super().recommend(context)
            return draft.model_copy(update={"alternative_plan_id": seed.BASIC_PLAN_ID})

    async def handler(session, job):
        await run_analysis(session, job, Pipeline(action="downgrade"))

    await JobRunner(
        async_sessionmaker(db_session.bind, expire_on_commit=False), {"analysis.run": handler}
    ).execute(job.id)
    poll = await client.get(created.headers["location"])
    if monthly is None:
        assert poll.json()["status"] == "failed", poll.text
        assert (
            await db_session.scalar(
                select(RecommendationModel).where(
                    RecommendationModel.analysis_id == UUID(created.json()["id"]),
                )
            )
            is None
        )
        return
    assert poll.json()["status"] == "completed", poll.text
    row = await db_session.scalar(
        select(RecommendationModel).where(
            RecommendationModel.analysis_id == UUID(created.json()["id"]),
        )
    )
    assert row.monthly_savings_amount == Decimal(monthly)
    assert row.annual_savings_amount == Decimal(annual)


async def test_generated_evidence_survives_public_list_and_detail(client, db_session, prepared):
    from sqlalchemy import event, update

    now = datetime.now(UTC)
    await db_session.execute(
        update(TransactionModel)
        .where(
            TransactionModel.subscription_id == seed.KEEP_SUBSCRIPTION_ID,
        )
        .values(amount=Decimal("12.3456"), occurred_at=now)
    )
    await db_session.execute(
        update(UsageEventModel)
        .where(
            UsageEventModel.subscription_id == seed.KEEP_SUBSCRIPTION_ID,
        )
        .values(is_unknown=True, quantity=None, occurred_at=now)
    )
    await db_session.commit()
    created = await create(client)
    job = await db_session.scalar(select(JobModel))

    def add_internal_values(mapper, connection, target):
        target.snapshot_json = {
            **target.snapshot_json,
            "provider_api_key": "private-provider-secret",
            "model_trace": "private-model-trace",
            "metadata": {"access_token": "nested-secret"},
            "reason": {"access_token": "nested-secret"},
        }

    async def handler(session, job):
        await run_analysis(session, job, FakePipeline(action="review"))

    event.listen(RecommendationEvidenceModel, "before_insert", add_internal_values)
    try:
        await JobRunner(
            async_sessionmaker(db_session.bind, expire_on_commit=False), {"analysis.run": handler}
        ).execute(job.id)
    finally:
        event.remove(RecommendationEvidenceModel, "before_insert", add_internal_values)
    poll = await client.get(created.headers["location"])
    assert poll.json()["status"] == "completed", poll.text
    listing = await client.get(
        "/api/v1/recommendations",
        params={
            "subscription_id": str(seed.KEEP_SUBSCRIPTION_ID),
        },
    )
    assert listing.status_code == 200, listing.text
    item = next(
        row
        for row in listing.json()["items"]
        if row["analysis"]["analysis_id"] == created.json()["id"]
    )
    detail = await client.get(f"/api/v1/recommendations/{item['id']}")
    assert detail.status_code == 200, detail.text
    assert detail.json() == item
    for response in (listing, detail):
        for marker in (
            "provider_api_key",
            "private-provider-secret",
            "model_trace",
            "private-model-trace",
            "access_token",
            "nested-secret",
            "metadata",
        ):
            assert marker not in response.text
    by_table = {}
    for evidence in item["evidence"]:
        assert evidence["snapshot"], evidence
        assert evidence["source_id"] is not None
        assert "reason" not in evidence["snapshot"]
        by_table[evidence["source_table"]] = evidence["snapshot"]
    assert Decimal(by_table["transactions"]["amount"]) == Decimal("12.3456")
    assert by_table["transactions"]["currency"] == "NGN"
    assert datetime.fromisoformat(by_table["transactions"]["occurred_at"]).tzinfo is not None
    assert by_table["usage_events"]["is_unknown"] is True
    assert by_table["usage_events"]["quantity"] is None
    assert by_table["usage_events"]["kind"]
    assert Decimal(by_table["plans"]["amount"]) > 0
    assert by_table["plans"]["billing_interval"] == "monthly"


async def test_selected_downgrade_target_survives_catalog_changes(client, db_session, prepared):
    from sqlalchemy import update

    from app.infrastructure.database.models.core import PlanModel, SubscriptionAlternativeModel

    selected_id = UUID("30000000-0000-4000-8000-000000000004")
    db_session.add(
        PlanModel(
            id=selected_id,
            provider_id=seed.STREAMING_PROVIDER_ID,
            name="Selected equal-price plan",
            external_reference="selected-equal-price",
            amount=Decimal("3000.0000"),
            currency="NGN",
            billing_interval="monthly",
        )
    )
    await db_session.flush()
    for plan_id in (seed.BASIC_PLAN_ID, selected_id):
        db_session.add(
            SubscriptionAlternativeModel(
                subscription_id=seed.KEEP_SUBSCRIPTION_ID,
                plan_id=plan_id,
            )
        )
    await db_session.execute(
        update(UsageEventModel)
        .where(
            UsageEventModel.subscription_id == seed.KEEP_SUBSCRIPTION_ID,
        )
        .values(occurred_at=datetime.now(UTC), quantity=2, is_unknown=False)
    )
    await db_session.commit()
    created = await create(client)
    assert created.status_code == 202, created.text
    job = await db_session.scalar(select(JobModel))

    class Pipeline(FakePipeline):
        async def recommend(self, context):
            # Neither rationale nor citation identifies the chosen alternative.
            draft = await super().recommend(context)
            return draft.model_copy(update={"alternative_plan_id": selected_id})

    async def handler(session, job):
        await run_analysis(session, job, Pipeline(action="downgrade"))

    await JobRunner(
        async_sessionmaker(db_session.bind, expire_on_commit=False), {"analysis.run": handler}
    ).execute(job.id)
    assert (await client.get(created.headers["location"])).json()["status"] == "completed"
    row = await db_session.scalar(
        select(RecommendationModel).where(
            RecommendationModel.analysis_id == UUID(created.json()["id"]),
        )
    )
    stored = list(
        (
            await db_session.scalars(
                select(RecommendationEvidenceModel).where(
                    RecommendationEvidenceModel.recommendation_id == row.id,
                )
            )
        ).all()
    )
    selected = [piece for piece in stored if piece.evidence_type == "selected_downgrade_target"]
    assert len(selected) == 1
    assert selected[0].source_id == selected_id
    assert selected[0].source_table == "plans"
    expected_terms = {
        "target_schema_version": "1.0",
        "amount": "3000.0000",
        "currency": "NGN",
        "billing_interval": "monthly",
    }
    assert selected[0].snapshot_json == expected_terms
    plan_sources = {piece.source_id for piece in stored if piece.source_table == "plans"}
    assert plan_sources == {seed.STANDARD_PLAN_ID, seed.BASIC_PLAN_ID, selected_id}

    async def public_result():
        listing = await client.get(
            "/api/v1/recommendations",
            params={
                "subscription_id": str(seed.KEEP_SUBSCRIPTION_ID),
            },
        )
        assert listing.status_code == 200, listing.text
        item = next(item for item in listing.json()["items"] if item["id"] == str(row.id))
        detail = await client.get(f"/api/v1/recommendations/{row.id}")
        assert detail.status_code == 200, detail.text
        assert detail.json() == item
        targets = [
            piece
            for piece in item["evidence"]
            if piece["evidence_type"] == "selected_downgrade_target"
        ]
        assert len(targets) == 1
        assert targets[0]["source_id"] == str(selected_id)
        assert targets[0]["snapshot"] == expected_terms
        return item

    before = await public_result()
    await db_session.execute(
        update(PlanModel)
        .where(PlanModel.id == selected_id)
        .values(
            amount=Decimal("9999.9900"),
            currency="USD",
            billing_interval="yearly",
            name="Changed",
        )
    )
    await db_session.execute(
        delete(SubscriptionAlternativeModel).where(
            SubscriptionAlternativeModel.subscription_id == seed.KEEP_SUBSCRIPTION_ID,
        )
    )
    await db_session.commit()
    assert await public_result() == before
    async with async_sessionmaker(db_session.bind, expire_on_commit=False)() as fresh:
        persisted = await fresh.get(RecommendationEvidenceModel, selected[0].id)
        assert persisted.source_id == selected_id
        assert persisted.snapshot_json == expected_terms


@pytest.mark.parametrize("selected_id", [None, UUID("30000000-0000-4000-8000-000000000099")])
async def test_unvalidated_downgrade_target_is_not_persisted(
    client, db_session, prepared, selected_id
):
    created = await create(client)
    job = await db_session.scalar(select(JobModel))

    class Pipeline(FakePipeline):
        async def recommend(self, context):
            draft = await super().recommend(context)
            return draft.model_copy(update={"alternative_plan_id": selected_id})

    async def handler(session, job):
        await run_analysis(session, job, Pipeline(action="downgrade"))

    await JobRunner(
        async_sessionmaker(db_session.bind, expire_on_commit=False), {"analysis.run": handler}
    ).execute(job.id)
    assert (await client.get(created.headers["location"])).json()["status"] == "failed"
    assert (
        await db_session.scalar(
            select(RecommendationModel).where(
                RecommendationModel.analysis_id == UUID(created.json()["id"]),
            )
        )
        is None
    )
