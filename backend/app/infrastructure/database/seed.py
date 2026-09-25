from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    ActionModel,
    AnalysisModel,
    AuditEventModel,
    ConsentModel,
    ConversationModel,
    DecisionType,
    EvaluationResultModel,
    EvaluationRunModel,
    MessageModel,
    PlanModel,
    PromptVersionModel,
    ProviderConnectionModel,
    ProviderModel,
    RecommendationAction,
    RecommendationDecisionModel,
    RecommendationEvidenceModel,
    RecommendationModel,
    SavingsKind,
    SavingsRecordModel,
    SubscriptionModel,
    SubscriptionStatus,
    TransactionModel,
    UsageEventModel,
    UserModel,
    WorkStatus,
)
from app.infrastructure.database.session import async_session_factory

SEED_TIMESTAMP = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

CURRENCY = "NGN"

KEEP_USER_ID = uuid.UUID("10000000-0000-4000-8000-000000000001")
REVIEW_USER_ID = uuid.UUID("10000000-0000-4000-8000-000000000002")

STREAMING_PROVIDER_ID = uuid.UUID("20000000-0000-4000-8000-000000000001")
PRODUCTIVITY_PROVIDER_ID = uuid.UUID("20000000-0000-4000-8000-000000000002")

BASIC_PLAN_ID = uuid.UUID("30000000-0000-4000-8000-000000000001")
STANDARD_PLAN_ID = uuid.UUID("30000000-0000-4000-8000-000000000002")
PREMIUM_PLAN_ID = uuid.UUID("30000000-0000-4000-8000-000000000003")

# Subscription IDs
KEEP_SUBSCRIPTION_ID = uuid.UUID("40000000-0000-4000-8000-000000000001")
DOWNGRADE_SUBSCRIPTION_ID = uuid.UUID("40000000-0000-4000-8000-000000000002")
CANCEL_SUBSCRIPTION_ID = uuid.UUID("40000000-0000-4000-8000-000000000003")
REVIEW_SUBSCRIPTION_ID = uuid.UUID("40000000-0000-4000-8000-000000000004")
MISSING_USAGE_SUBSCRIPTION_ID = uuid.UUID("40000000-0000-4000-8000-000000000005")
CONFLICTING_EVIDENCE_SUBSCRIPTION_ID = uuid.UUID("40000000-0000-4000-8000-000000000006")

# Analysis IDs
KEEP_ANALYSIS_ID = uuid.UUID("50000000-0000-4000-8000-000000000001")
DOWNGRADE_ANALYSIS_ID = uuid.UUID("50000000-0000-4000-8000-000000000002")
CANCEL_ANALYSIS_ID = uuid.UUID("50000000-0000-4000-8000-000000000003")
REVIEW_ANALYSIS_ID = uuid.UUID("50000000-0000-4000-8000-000000000004")
MISSING_USAGE_ANALYSIS_ID = uuid.UUID("50000000-0000-4000-8000-000000000005")
CONFLICTING_EVIDENCE_ANALYSIS_ID = uuid.UUID("50000000-0000-4000-8000-000000000006")

# Recommendation IDs
KEEP_RECOMMENDATION_ID = uuid.UUID("60000000-0000-4000-8000-000000000001")
DOWNGRADE_RECOMMENDATION_ID = uuid.UUID("60000000-0000-4000-8000-000000000002")
CANCEL_RECOMMENDATION_ID = uuid.UUID("60000000-0000-4000-8000-000000000003")
REVIEW_RECOMMENDATION_ID = uuid.UUID("60000000-0000-4000-8000-000000000004")
MISSING_USAGE_RECOMMENDATION_ID = uuid.UUID("60000000-0000-4000-8000-000000000005")
CONFLICTING_EVIDENCE_RECOMMENDATION_ID = uuid.UUID("60000000-0000-4000-8000-000000000006")


async def seed_users_providers_plans(session: AsyncSession) -> None:
    """Create the deterministic users, providers, and plans."""

    users = [
        UserModel(
            id=KEEP_USER_ID,
            email="demo.keep@example.test",
            hashed_password="demo-seed-password-not-for-login",
            is_active=True,
            created_at=SEED_TIMESTAMP,
        ),
        UserModel(
            id=REVIEW_USER_ID,
            email="demo.review@example.test",
            hashed_password="demo-seed-password-not-for-login",
            is_active=True,
            created_at=SEED_TIMESTAMP,
        ),
    ]

    providers = [
        ProviderModel(
            id=STREAMING_PROVIDER_ID,
            slug="demo-streaming",
            display_name="Demo Streaming",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        ProviderModel(
            id=PRODUCTIVITY_PROVIDER_ID,
            slug="demo-productivity",
            display_name="Demo Productivity",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    plans = [
        PlanModel(
            id=BASIC_PLAN_ID,
            provider_id=STREAMING_PROVIDER_ID,
            external_reference="demo-basic",
            name="Demo Basic",
            amount=Decimal("3000.00"),
            currency=CURRENCY,
            billing_interval="monthly",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        PlanModel(
            id=STANDARD_PLAN_ID,
            provider_id=STREAMING_PROVIDER_ID,
            external_reference="demo-standard",
            name="Demo Standard",
            amount=Decimal("6000.00"),
            currency=CURRENCY,
            billing_interval="monthly",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        PlanModel(
            id=PREMIUM_PLAN_ID,
            provider_id=STREAMING_PROVIDER_ID,
            external_reference="demo-premium",
            name="Demo Premium",
            amount=Decimal("10000.00"),
            currency=CURRENCY,
            billing_interval="monthly",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    session.add_all(users)
    session.add_all(providers)
    session.add_all(plans)

    await session.flush()


async def seed_connections_and_subscriptions(session: AsyncSession) -> None:
    """Create provider connections and the six demo subscription scenarios."""

    connections = [
        ProviderConnectionModel(
            id=uuid.UUID("70000000-0000-4000-8000-000000000001"),
            user_id=KEEP_USER_ID,
            provider_id=STREAMING_PROVIDER_ID,
            external_reference="demo-keep-connection",
            status="connected",
            metadata_json={"demo": True},
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        ProviderConnectionModel(
            id=uuid.UUID("70000000-0000-4000-8000-000000000002"),
            user_id=REVIEW_USER_ID,
            provider_id=STREAMING_PROVIDER_ID,
            external_reference="demo-review-connection",
            status="connected",
            metadata_json={"demo": True},
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    subscriptions = [
        SubscriptionModel(
            id=KEEP_SUBSCRIPTION_ID,
            user_id=KEEP_USER_ID,
            plan_id=STANDARD_PLAN_ID,
            provider_connection_id=connections[0].id,
            name="Demo Streaming Standard - Keep",
            status=SubscriptionStatus.ACTIVE,
            started_at=SEED_TIMESTAMP,
            renewal_at=datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        SubscriptionModel(
            id=DOWNGRADE_SUBSCRIPTION_ID,
            user_id=KEEP_USER_ID,
            plan_id=PREMIUM_PLAN_ID,
            provider_connection_id=connections[0].id,
            name="Demo Premium - Downgrade",
            status=SubscriptionStatus.ACTIVE,
            started_at=SEED_TIMESTAMP,
            renewal_at=datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        SubscriptionModel(
            id=CANCEL_SUBSCRIPTION_ID,
            user_id=KEEP_USER_ID,
            plan_id=STANDARD_PLAN_ID,
            provider_connection_id=connections[0].id,
            name="Demo Streaming Standard - Cancel",
            status=SubscriptionStatus.ACTIVE,
            started_at=SEED_TIMESTAMP,
            renewal_at=datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        SubscriptionModel(
            id=REVIEW_SUBSCRIPTION_ID,
            user_id=REVIEW_USER_ID,
            plan_id=STANDARD_PLAN_ID,
            provider_connection_id=connections[1].id,
            name="Demo Streaming Standard - Review",
            status=SubscriptionStatus.PAUSED,
            started_at=SEED_TIMESTAMP,
            renewal_at=datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        SubscriptionModel(
            id=MISSING_USAGE_SUBSCRIPTION_ID,
            user_id=REVIEW_USER_ID,
            plan_id=BASIC_PLAN_ID,
            provider_connection_id=connections[1].id,
            name="Demo Basic - Missing Usage",
            status=SubscriptionStatus.EXPIRED,
            started_at=SEED_TIMESTAMP,
            renewal_at=datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
            ended_at=datetime(2026, 2, 2, 12, 0, tzinfo=UTC),
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        SubscriptionModel(
            id=CONFLICTING_EVIDENCE_SUBSCRIPTION_ID,
            user_id=REVIEW_USER_ID,
            plan_id=STANDARD_PLAN_ID,
            provider_connection_id=connections[1].id,
            name="Demo Streaming Standard - Conflicting Evidence",
            status=SubscriptionStatus.ACTIVE,
            started_at=SEED_TIMESTAMP,
            renewal_at=datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    session.add_all(connections)
    session.add_all(subscriptions)

    await session.flush()


async def seed_transactions_and_usage(session: AsyncSession) -> None:
    """Create deterministic transaction and usage evidence."""

    transactions = [
        TransactionModel(
            id=uuid.UUID("80000000-0000-4000-8000-000000000001"),
            user_id=KEEP_USER_ID,
            subscription_id=KEEP_SUBSCRIPTION_ID,
            amount=Decimal("6000.00"),
            currency=CURRENCY,
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            source="demo",
            external_reference="demo-tx-keep",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        TransactionModel(
            id=uuid.UUID("80000000-0000-4000-8000-000000000002"),
            user_id=KEEP_USER_ID,
            subscription_id=DOWNGRADE_SUBSCRIPTION_ID,
            amount=Decimal("10000.00"),
            currency=CURRENCY,
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            source="demo",
            external_reference="demo-tx-downgrade",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        TransactionModel(
            id=uuid.UUID("80000000-0000-4000-8000-000000000003"),
            user_id=KEEP_USER_ID,
            subscription_id=CANCEL_SUBSCRIPTION_ID,
            amount=Decimal("6000.00"),
            currency=CURRENCY,
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            source="demo",
            external_reference="demo-tx-cancel",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        TransactionModel(
            id=uuid.UUID("80000000-0000-4000-8000-000000000004"),
            user_id=REVIEW_USER_ID,
            subscription_id=REVIEW_SUBSCRIPTION_ID,
            amount=Decimal("6000.00"),
            currency=CURRENCY,
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            source="demo",
            external_reference="demo-tx-review",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        TransactionModel(
            id=uuid.UUID("80000000-0000-4000-8000-000000000005"),
            user_id=REVIEW_USER_ID,
            subscription_id=MISSING_USAGE_SUBSCRIPTION_ID,
            amount=Decimal("3000.00"),
            currency=CURRENCY,
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            source="demo",
            external_reference="demo-tx-missing-usage",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        TransactionModel(
            id=uuid.UUID("80000000-0000-4000-8000-000000000006"),
            user_id=REVIEW_USER_ID,
            subscription_id=CONFLICTING_EVIDENCE_SUBSCRIPTION_ID,
            amount=Decimal("6000.00"),
            currency=CURRENCY,
            occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            source="demo",
            external_reference="demo-tx-conflicting",
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    usage_events = [
        UsageEventModel(
            id=uuid.UUID("90000000-0000-4000-8000-000000000001"),
            user_id=KEEP_USER_ID,
            subscription_id=KEEP_SUBSCRIPTION_ID,
            occurred_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            source="demo",
            kind="active_use",
            quantity=Decimal("18"),
            is_unknown=False,
            evidence_json={"sessions": 18, "value_signal": "high"},
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        UsageEventModel(
            id=uuid.UUID("90000000-0000-4000-8000-000000000002"),
            user_id=KEEP_USER_ID,
            subscription_id=DOWNGRADE_SUBSCRIPTION_ID,
            occurred_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            source="demo",
            kind="light_use",
            quantity=Decimal("4"),
            is_unknown=False,
            evidence_json={"sessions": 4, "value_signal": "low", "lower_tier_suitable": True},
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        UsageEventModel(
            id=uuid.UUID("90000000-0000-4000-8000-000000000003"),
            user_id=KEEP_USER_ID,
            subscription_id=CANCEL_SUBSCRIPTION_ID,
            occurred_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            source="demo",
            kind="inactive",
            quantity=Decimal("0"),
            is_unknown=False,
            evidence_json={"sessions": 0, "value_signal": "none"},
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        UsageEventModel(
            id=uuid.UUID("90000000-0000-4000-8000-000000000004"),
            user_id=REVIEW_USER_ID,
            subscription_id=REVIEW_SUBSCRIPTION_ID,
            occurred_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            source="demo",
            kind="irregular_use",
            quantity=Decimal("2"),
            is_unknown=False,
            evidence_json={"sessions": 2, "value_signal": "uncertain"},
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        UsageEventModel(
            id=uuid.UUID("90000000-0000-4000-8000-000000000005"),
            user_id=REVIEW_USER_ID,
            subscription_id=MISSING_USAGE_SUBSCRIPTION_ID,
            occurred_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            source="demo",
            kind="usage_unavailable",
            quantity=None,
            is_unknown=True,
            evidence_json={
                "sessions": None,
                "reason": "provider_usage_not_available",
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        UsageEventModel(
            id=uuid.UUID("90000000-0000-4000-8000-000000000006"),
            user_id=REVIEW_USER_ID,
            subscription_id=CONFLICTING_EVIDENCE_SUBSCRIPTION_ID,
            occurred_at=datetime(2026, 1, 15, 12, 0, tzinfo=UTC),
            source="demo",
            kind="usage_conflict",
            quantity=Decimal("8"),
            is_unknown=False,
            evidence_json={
                "usage_signal": "active",
                "billing_signal": "inactive",
                "conflict": True,
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    session.add_all(transactions)
    session.add_all(usage_events)

    await session.flush()


PROMPT_VERSION_ID = uuid.UUID("A0000000-0000-4000-8000-000000000001")


async def seed_analyses_and_recommendations(session: AsyncSession) -> None:
    """Create deterministic analyses and their expected recommendations."""

    prompt_version = PromptVersionModel(
        id=PROMPT_VERSION_ID,
        name="subscription-recommendation",
        version="1.0.0",
        schema_version="1.0",
        template="Demo subscription recommendation prompt for deterministic seed scenarios.",
        is_active=True,
        created_at=SEED_TIMESTAMP,
        updated_at=SEED_TIMESTAMP,
    )

    analyses = [
        AnalysisModel(
            id=KEEP_ANALYSIS_ID,
            user_id=KEEP_USER_ID,
            subscription_id=KEEP_SUBSCRIPTION_ID,
            prompt_version_id=PROMPT_VERSION_ID,
            status=WorkStatus.SUCCEEDED,
            idempotency_key="demo-analysis-keep-v1",
            attempt_count=1,
            started_at=SEED_TIMESTAMP,
            completed_at=SEED_TIMESTAMP,
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        AnalysisModel(
            id=DOWNGRADE_ANALYSIS_ID,
            user_id=KEEP_USER_ID,
            subscription_id=DOWNGRADE_SUBSCRIPTION_ID,
            prompt_version_id=PROMPT_VERSION_ID,
            status=WorkStatus.SUCCEEDED,
            idempotency_key="demo-analysis-downgrade-v1",
            attempt_count=1,
            started_at=SEED_TIMESTAMP,
            completed_at=SEED_TIMESTAMP,
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        AnalysisModel(
            id=CANCEL_ANALYSIS_ID,
            user_id=KEEP_USER_ID,
            subscription_id=CANCEL_SUBSCRIPTION_ID,
            prompt_version_id=PROMPT_VERSION_ID,
            status=WorkStatus.SUCCEEDED,
            idempotency_key="demo-analysis-cancel-v1",
            attempt_count=1,
            started_at=SEED_TIMESTAMP,
            completed_at=SEED_TIMESTAMP,
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        AnalysisModel(
            id=REVIEW_ANALYSIS_ID,
            user_id=REVIEW_USER_ID,
            subscription_id=REVIEW_SUBSCRIPTION_ID,
            prompt_version_id=PROMPT_VERSION_ID,
            status=WorkStatus.SUCCEEDED,
            idempotency_key="demo-analysis-review-v1",
            attempt_count=1,
            started_at=SEED_TIMESTAMP,
            completed_at=SEED_TIMESTAMP,
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        AnalysisModel(
            id=MISSING_USAGE_ANALYSIS_ID,
            user_id=REVIEW_USER_ID,
            subscription_id=MISSING_USAGE_SUBSCRIPTION_ID,
            prompt_version_id=PROMPT_VERSION_ID,
            status=WorkStatus.SUCCEEDED,
            idempotency_key="demo-analysis-missing-usage-v1",
            attempt_count=1,
            started_at=SEED_TIMESTAMP,
            completed_at=SEED_TIMESTAMP,
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        AnalysisModel(
            id=CONFLICTING_EVIDENCE_ANALYSIS_ID,
            user_id=REVIEW_USER_ID,
            subscription_id=CONFLICTING_EVIDENCE_SUBSCRIPTION_ID,
            prompt_version_id=PROMPT_VERSION_ID,
            status=WorkStatus.SUCCEEDED,
            idempotency_key="demo-analysis-conflicting-evidence-v1",
            attempt_count=1,
            started_at=SEED_TIMESTAMP,
            completed_at=SEED_TIMESTAMP,
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    recommendations = [
        RecommendationModel(
            id=KEEP_RECOMMENDATION_ID,
            user_id=KEEP_USER_ID,
            analysis_id=KEEP_ANALYSIS_ID,
            version=1,
            recommended_action=RecommendationAction.KEEP,
            confidence=Decimal("0.95"),
            rationale="Recent usage and value evidence support keeping the subscription.",
            uncertainty_json={"level": "low"},
            monthly_savings_amount=Decimal("0.00"),
            annual_savings_amount=Decimal("0.00"),
            currency=CURRENCY,
            prompt_version="1.0.0",
            schema_version="1.0",
            created_at=SEED_TIMESTAMP,
        ),
        RecommendationModel(
            id=DOWNGRADE_RECOMMENDATION_ID,
            user_id=KEEP_USER_ID,
            analysis_id=DOWNGRADE_ANALYSIS_ID,
            version=1,
            recommended_action=RecommendationAction.DOWNGRADE,
            confidence=Decimal("0.91"),
            rationale="Usage is light and the lower-tier plan is sufficient for observed usage.",
            uncertainty_json={"level": "low"},
            monthly_savings_amount=Decimal("4000.00"),
            annual_savings_amount=Decimal("48000.00"),
            currency=CURRENCY,
            prompt_version="1.0.0",
            schema_version="1.0",
            created_at=SEED_TIMESTAMP,
        ),
        RecommendationModel(
            id=CANCEL_RECOMMENDATION_ID,
            user_id=KEEP_USER_ID,
            analysis_id=CANCEL_ANALYSIS_ID,
            version=1,
            recommended_action=RecommendationAction.CANCEL,
            confidence=Decimal("0.93"),
            rationale="The subscription has no observed usage in the demo evidence period.",
            uncertainty_json={"level": "low"},
            monthly_savings_amount=Decimal("6000.00"),
            annual_savings_amount=Decimal("72000.00"),
            currency=CURRENCY,
            prompt_version="1.0.0",
            schema_version="1.0",
            created_at=SEED_TIMESTAMP,
        ),
        RecommendationModel(
            id=REVIEW_RECOMMENDATION_ID,
            user_id=REVIEW_USER_ID,
            analysis_id=REVIEW_ANALYSIS_ID,
            version=1,
            recommended_action=RecommendationAction.REVIEW,
            confidence=Decimal("0.55"),
            rationale="The available evidence is uncertain and requires human review.",
            uncertainty_json={"level": "medium", "reason": "uncertain_usage_pattern"},
            monthly_savings_amount=Decimal("0.00"),
            annual_savings_amount=Decimal("0.00"),
            currency=CURRENCY,
            prompt_version="1.0.0",
            schema_version="1.0",
            created_at=SEED_TIMESTAMP,
        ),
        RecommendationModel(
            id=MISSING_USAGE_RECOMMENDATION_ID,
            user_id=REVIEW_USER_ID,
            analysis_id=MISSING_USAGE_ANALYSIS_ID,
            version=1,
            recommended_action=RecommendationAction.REVIEW,
            confidence=Decimal("0.50"),
            rationale=(
                "Usage data is unavailable; missing usage is not treated as proof of non-use."
            ),
            uncertainty_json={"level": "high", "reason": "missing_usage"},
            monthly_savings_amount=Decimal("0.00"),
            annual_savings_amount=Decimal("0.00"),
            currency=CURRENCY,
            prompt_version="1.0.0",
            schema_version="1.0",
            created_at=SEED_TIMESTAMP,
        ),
        RecommendationModel(
            id=CONFLICTING_EVIDENCE_RECOMMENDATION_ID,
            user_id=REVIEW_USER_ID,
            analysis_id=CONFLICTING_EVIDENCE_ANALYSIS_ID,
            version=1,
            recommended_action=RecommendationAction.REVIEW,
            confidence=Decimal("0.45"),
            rationale=(
                "Evidence sources conflict, so the system should not make an "
                "overconfident recommendation."
            ),
            uncertainty_json={"level": "high", "reason": "conflicting_evidence"},
            monthly_savings_amount=Decimal("0.00"),
            annual_savings_amount=Decimal("0.00"),
            currency=CURRENCY,
            prompt_version="1.0.0",
            schema_version="1.0",
            created_at=SEED_TIMESTAMP,
        ),
    ]

    session.add(prompt_version)
    session.add_all(analyses)
    session.add_all(recommendations)

    await session.flush()


async def seed_recommendation_evidence(session: AsyncSession) -> None:
    """Create deterministic evidence supporting each recommendation."""

    evidence = [
        RecommendationEvidenceModel(
            id=uuid.UUID("61000000-0000-4000-8000-000000000001"),
            user_id=KEEP_USER_ID,
            recommendation_id=KEEP_RECOMMENDATION_ID,
            evidence_type="usage",
            source_table="usage_events",
            source_id=uuid.UUID("90000000-0000-4000-8000-000000000001"),
            snapshot_json={
                "sessions": 18,
                "value_signal": "high",
                "supports": "keep",
            },
            created_at=SEED_TIMESTAMP,
        ),
        RecommendationEvidenceModel(
            id=uuid.UUID("61000000-0000-4000-8000-000000000002"),
            user_id=KEEP_USER_ID,
            recommendation_id=DOWNGRADE_RECOMMENDATION_ID,
            evidence_type="usage",
            source_table="usage_events",
            source_id=uuid.UUID("90000000-0000-4000-8000-000000000002"),
            snapshot_json={
                "sessions": 4,
                "value_signal": "low",
                "lower_tier_suitable": True,
            },
            created_at=SEED_TIMESTAMP,
        ),
        RecommendationEvidenceModel(
            id=uuid.UUID("61000000-0000-4000-8000-000000000003"),
            user_id=KEEP_USER_ID,
            recommendation_id=CANCEL_RECOMMENDATION_ID,
            evidence_type="usage",
            source_table="usage_events",
            source_id=uuid.UUID("90000000-0000-4000-8000-000000000003"),
            snapshot_json={
                "sessions": 0,
                "value_signal": "none",
                "supports": "cancel",
            },
            created_at=SEED_TIMESTAMP,
        ),
        RecommendationEvidenceModel(
            id=uuid.UUID("61000000-0000-4000-8000-000000000004"),
            user_id=REVIEW_USER_ID,
            recommendation_id=REVIEW_RECOMMENDATION_ID,
            evidence_type="usage",
            source_table="usage_events",
            source_id=uuid.UUID("90000000-0000-4000-8000-000000000004"),
            snapshot_json={
                "sessions": 2,
                "value_signal": "uncertain",
                "requires_review": True,
            },
            created_at=SEED_TIMESTAMP,
        ),
        RecommendationEvidenceModel(
            id=uuid.UUID("61000000-0000-4000-8000-000000000005"),
            user_id=REVIEW_USER_ID,
            recommendation_id=MISSING_USAGE_RECOMMENDATION_ID,
            evidence_type="usage",
            source_table="usage_events",
            source_id=uuid.UUID("90000000-0000-4000-8000-000000000005"),
            snapshot_json={
                "sessions": None,
                "usage_available": False,
                "reason": "provider_usage_not_available",
            },
            created_at=SEED_TIMESTAMP,
        ),
        RecommendationEvidenceModel(
            id=uuid.UUID("61000000-0000-4000-8000-000000000006"),
            user_id=REVIEW_USER_ID,
            recommendation_id=CONFLICTING_EVIDENCE_RECOMMENDATION_ID,
            evidence_type="conflict",
            source_table="usage_events",
            source_id=uuid.UUID("90000000-0000-4000-8000-000000000006"),
            snapshot_json={
                "usage_signal": "active",
                "billing_signal": "inactive",
                "conflict": True,
                "requires_review": True,
            },
            created_at=SEED_TIMESTAMP,
        ),
    ]

    session.add_all(evidence)

    await session.flush()


async def seed_recommendation_decisions(session: AsyncSession) -> None:
    """Create deterministic decisions for seeded recommendations."""

    decisions = [
        RecommendationDecisionModel(
            id=uuid.UUID("62000000-0000-4000-8000-000000000001"),
            user_id=KEEP_USER_ID,
            recommendation_id=KEEP_RECOMMENDATION_ID,
            recommendation_version=1,
            decision=DecisionType.APPROVE,
            reason="User approved the keep recommendation.",
            correction_json=None,
            defer_until=None,
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        RecommendationDecisionModel(
            id=uuid.UUID("62000000-0000-4000-8000-000000000002"),
            user_id=KEEP_USER_ID,
            recommendation_id=DOWNGRADE_RECOMMENDATION_ID,
            recommendation_version=1,
            decision=DecisionType.APPROVE,
            reason="User approved the downgrade recommendation.",
            correction_json=None,
            defer_until=None,
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    session.add_all(decisions)

    await session.flush()


async def seed_actions(session: AsyncSession) -> None:
    """Create deterministic simulated actions."""

    actions = [
        ActionModel(
            id=uuid.UUID("63000000-0000-4000-8000-000000000001"),
            user_id=KEEP_USER_ID,
            decision_id=uuid.UUID("62000000-0000-4000-8000-000000000001"),
            status=WorkStatus.SUCCEEDED,
            action_type="keep",
            provider="demo-streaming",
            idempotency_key="demo-action-keep-v1",
            attempt_count=1,
            result_json={
                "simulated": True,
                "result": "subscription_kept",
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        ActionModel(
            id=uuid.UUID("63000000-0000-4000-8000-000000000002"),
            user_id=KEEP_USER_ID,
            decision_id=uuid.UUID("62000000-0000-4000-8000-000000000002"),
            status=WorkStatus.QUEUED,
            action_type="downgrade",
            provider="demo-streaming",
            idempotency_key="demo-action-downgrade-v1",
            attempt_count=0,
            result_json={
                "simulated": True,
                "result": "pending_execution",
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    session.add_all(actions)

    await session.flush()


async def seed_savings_records(session: AsyncSession) -> None:
    """Create deterministic estimated and verified savings records."""

    savings_records = [
        SavingsRecordModel(
            id=uuid.UUID("64000000-0000-4000-8000-000000000001"),
            user_id=KEEP_USER_ID,
            action_id=uuid.UUID("63000000-0000-4000-8000-000000000002"),
            recommendation_id=DOWNGRADE_RECOMMENDATION_ID,
            kind=SavingsKind.ESTIMATED,
            amount=Decimal("4000.00"),
            currency=CURRENCY,
            period="monthly",
            calculation_json={
                "from_plan_amount": "10000.00",
                "to_plan_amount": "6000.00",
                "method": "plan_price_difference",
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        SavingsRecordModel(
            id=uuid.UUID("64000000-0000-4000-8000-000000000002"),
            user_id=KEEP_USER_ID,
            action_id=None,
            recommendation_id=DOWNGRADE_RECOMMENDATION_ID,
            kind=SavingsKind.VERIFIED,
            amount=Decimal("4000.00"),
            currency=CURRENCY,
            period="monthly",
            calculation_json={
                "verified": True,
                "verified_amount": "4000.00",
                "method": "confirmed_billing_difference",
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    session.add_all(savings_records)

    await session.flush()


async def seed_conversation(session: AsyncSession) -> None:
    """Create one deterministic conversation with two messages."""

    conversation_id = uuid.UUID("65000000-0000-4000-8000-000000000001")

    conversation = ConversationModel(
        id=conversation_id,
        user_id=REVIEW_USER_ID,
        recommendation_id=REVIEW_RECOMMENDATION_ID,
        created_at=SEED_TIMESTAMP,
        updated_at=SEED_TIMESTAMP,
    )

    messages = [
        MessageModel(
            id=uuid.UUID("66000000-0000-4000-8000-000000000001"),
            user_id=REVIEW_USER_ID,
            conversation_id=conversation_id,
            role="user",
            content="Why did the system recommend reviewing this subscription?",
            metadata_json={"demo": True},
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        MessageModel(
            id=uuid.UUID("66000000-0000-4000-8000-000000000002"),
            user_id=REVIEW_USER_ID,
            conversation_id=conversation_id,
            role="assistant",
            content=(
                "The recommendation is review because the available usage "
                "evidence is uncertain. The system does not have enough "
                "confidence to recommend keeping or cancelling the subscription."
            ),
            metadata_json={"demo": True},
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    session.add(conversation)
    session.add_all(messages)

    await session.flush()


async def seed_evaluation(session: AsyncSession) -> None:
    """Create a deterministic evaluation run for all seed scenarios."""

    evaluation_run_id = uuid.UUID("67000000-0000-4000-8000-000000000001")

    evaluation_run = EvaluationRunModel(
        id=evaluation_run_id,
        prompt_version_id=PROMPT_VERSION_ID,
        status=WorkStatus.SUCCEEDED,
        dataset_version="issue-4-seed-v1",
        summary_json={
            "total_cases": 6,
            "passed_cases": 6,
            "currency": CURRENCY,
        },
        created_at=SEED_TIMESTAMP,
        updated_at=SEED_TIMESTAMP,
    )

    results = [
        EvaluationResultModel(
            id=uuid.UUID("68000000-0000-4000-8000-000000000001"),
            evaluation_run_id=evaluation_run_id,
            case_id="keep",
            passed=True,
            score=Decimal("1.00"),
            details_json={
                "expected_action": "keep",
                "expected_monthly_savings": "0.00",
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        EvaluationResultModel(
            id=uuid.UUID("68000000-0000-4000-8000-000000000002"),
            evaluation_run_id=evaluation_run_id,
            case_id="downgrade",
            passed=True,
            score=Decimal("1.00"),
            details_json={
                "expected_action": "downgrade",
                "expected_monthly_savings": "4000.00",
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        EvaluationResultModel(
            id=uuid.UUID("68000000-0000-4000-8000-000000000003"),
            evaluation_run_id=evaluation_run_id,
            case_id="cancel",
            passed=True,
            score=Decimal("1.00"),
            details_json={
                "expected_action": "cancel",
                "expected_monthly_savings": "6000.00",
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        EvaluationResultModel(
            id=uuid.UUID("68000000-0000-4000-8000-000000000004"),
            evaluation_run_id=evaluation_run_id,
            case_id="review",
            passed=True,
            score=Decimal("1.00"),
            details_json={
                "expected_action": "review",
                "expected_monthly_savings": "0.00",
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        EvaluationResultModel(
            id=uuid.UUID("68000000-0000-4000-8000-000000000005"),
            evaluation_run_id=evaluation_run_id,
            case_id="missing-usage",
            passed=True,
            score=Decimal("1.00"),
            details_json={
                "expected_action": "review",
                "expected_monthly_savings": "0.00",
                "missing_usage_is_not_proof_of_non_use": True,
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        EvaluationResultModel(
            id=uuid.UUID("68000000-0000-4000-8000-000000000006"),
            evaluation_run_id=evaluation_run_id,
            case_id="conflicting-evidence",
            passed=True,
            score=Decimal("1.00"),
            details_json={
                "expected_action": "review",
                "expected_monthly_savings": "0.00",
                "conflicting_evidence_requires_review": True,
            },
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    session.add(evaluation_run)
    session.add_all(results)

    await session.flush()


async def seed_consents_and_audit_events(session: AsyncSession) -> None:
    """Create deterministic consent records and audit events."""

    consents = [
        ConsentModel(
            id=uuid.UUID("69000000-0000-4000-8000-000000000001"),
            user_id=KEEP_USER_ID,
            policy_version="2026-01",
            scopes=[
                "subscriptions:read",
                "usage:read",
            ],
            granted_at=SEED_TIMESTAMP,
            revoked_at=None,
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
        ConsentModel(
            id=uuid.UUID("69000000-0000-4000-8000-000000000002"),
            user_id=REVIEW_USER_ID,
            policy_version="2026-01",
            scopes=[
                "subscriptions:read",
                "usage:read",
            ],
            granted_at=SEED_TIMESTAMP,
            revoked_at=datetime(
                2026,
                1,
                20,
                12,
                0,
                tzinfo=UTC,
            ),
            created_at=SEED_TIMESTAMP,
            updated_at=SEED_TIMESTAMP,
        ),
    ]

    audit_events = [
        AuditEventModel(
            id=uuid.UUID("6a000000-0000-4000-8000-000000000001"),
            user_id=KEEP_USER_ID,
            event_type="demo.seed.recommendation",
            actor_type="system",
            actor_id=None,
            resource_type="recommendation",
            resource_id=KEEP_RECOMMENDATION_ID,
            correlation_id="issue-4-seed-v1",
            payload_json={
                "scenario": "keep",
                "expected_action": "keep",
            },
            occurred_at=SEED_TIMESTAMP,
        ),
        AuditEventModel(
            id=uuid.UUID("6a000000-0000-4000-8000-000000000002"),
            user_id=KEEP_USER_ID,
            event_type="demo.seed.recommendation",
            actor_type="system",
            actor_id=None,
            resource_type="recommendation",
            resource_id=DOWNGRADE_RECOMMENDATION_ID,
            correlation_id="issue-4-seed-v1",
            payload_json={
                "scenario": "downgrade",
                "expected_action": "downgrade",
                "monthly_savings": "4000.00",
            },
            occurred_at=SEED_TIMESTAMP,
        ),
        AuditEventModel(
            id=uuid.UUID("6a000000-0000-4000-8000-000000000003"),
            user_id=KEEP_USER_ID,
            event_type="demo.seed.recommendation",
            actor_type="system",
            actor_id=None,
            resource_type="recommendation",
            resource_id=CANCEL_RECOMMENDATION_ID,
            correlation_id="issue-4-seed-v1",
            payload_json={
                "scenario": "cancel",
                "expected_action": "cancel",
                "monthly_savings": "6000.00",
            },
            occurred_at=SEED_TIMESTAMP,
        ),
        AuditEventModel(
            id=uuid.UUID("6a000000-0000-4000-8000-000000000004"),
            user_id=REVIEW_USER_ID,
            event_type="demo.seed.recommendation",
            actor_type="system",
            actor_id=None,
            resource_type="recommendation",
            resource_id=REVIEW_RECOMMENDATION_ID,
            correlation_id="issue-4-seed-v1",
            payload_json={
                "scenario": "review",
                "expected_action": "review",
            },
            occurred_at=SEED_TIMESTAMP,
        ),
        AuditEventModel(
            id=uuid.UUID("6a000000-0000-4000-8000-000000000005"),
            user_id=REVIEW_USER_ID,
            event_type="demo.seed.recommendation",
            actor_type="system",
            actor_id=None,
            resource_type="recommendation",
            resource_id=MISSING_USAGE_RECOMMENDATION_ID,
            correlation_id="issue-4-seed-v1",
            payload_json={
                "scenario": "missing-usage",
                "expected_action": "review",
                "missing_usage_is_not_proof_of_non_use": True,
            },
            occurred_at=SEED_TIMESTAMP,
        ),
        AuditEventModel(
            id=uuid.UUID("6a000000-0000-4000-8000-000000000006"),
            user_id=REVIEW_USER_ID,
            event_type="demo.seed.recommendation",
            actor_type="system",
            actor_id=None,
            resource_type="recommendation",
            resource_id=CONFLICTING_EVIDENCE_RECOMMENDATION_ID,
            correlation_id="issue-4-seed-v1",
            payload_json={
                "scenario": "conflicting-evidence",
                "expected_action": "review",
                "conflicting_evidence_requires_review": True,
            },
            occurred_at=SEED_TIMESTAMP,
        ),
    ]

    session.add_all(consents)
    session.add_all(audit_events)

    await session.flush()


async def seed_demo_data(session: AsyncSession) -> None:
    """Load all deterministic demo seed data exactly once."""

    recommendation_ids = {
        KEEP_RECOMMENDATION_ID,
        DOWNGRADE_RECOMMENDATION_ID,
        CANCEL_RECOMMENDATION_ID,
        REVIEW_RECOMMENDATION_ID,
        MISSING_USAGE_RECOMMENDATION_ID,
        CONFLICTING_EVIDENCE_RECOMMENDATION_ID,
    }

    result = await session.execute(
        select(RecommendationModel.id).where(RecommendationModel.id.in_(recommendation_ids))
    )
    existing_ids = set(result.scalars().all())

    if len(existing_ids) == len(recommendation_ids):
        print("Demo seed data already exists. Nothing to do.")
        return

    if existing_ids:
        raise RuntimeError(
            "Partial demo seed data detected. "
            "Reset the demo database before running the seed again."
        )

    await seed_users_providers_plans(session)
    await seed_connections_and_subscriptions(session)
    await seed_transactions_and_usage(session)
    await seed_analyses_and_recommendations(session)
    await seed_recommendation_evidence(session)
    await seed_recommendation_decisions(session)
    await seed_actions(session)
    await seed_savings_records(session)
    await seed_conversation(session)
    await seed_evaluation(session)
    await seed_consents_and_audit_events(session)

    print("Demo seed data loaded successfully.")


async def main() -> None:
    """Run the deterministic demo seed."""

    async with async_session_factory() as session:
        try:
            await seed_demo_data(session)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
