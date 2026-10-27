"""Transactional analysis handler; JobRunner owns commit and rollback."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.analyses.pipeline import (
    AnalysisPipeline,
    HttpAnalysisPipeline,
    RecommendationDraft,
)
from app.application.jobs import PermanentJobError
from app.domain.analysis.features import (
    AnalysisStatus,
    calculate_savings,
    charges_per_year,
    classify_usage,
    evidence_freshness,
    normalize_cost,
)
from app.domain.subscriptions.entities import BillingCadence, Plan
from app.infrastructure.database.models.core import (
    AnalysisModel,
    PlanModel,
    PromptVersionModel,
    RecommendationAction,
    RecommendationEvidenceModel,
    RecommendationModel,
    SubscriptionAlternativeModel,
    SubscriptionModel,
    TransactionModel,
    UsageEventModel,
)
from app.infrastructure.database.models.job import JobModel


def domain_plan(row: PlanModel) -> Plan:
    try:
        cadence = BillingCadence(row.billing_interval)
    except ValueError:
        raise PermanentJobError("unsupported_cost") from None
    return Plan(
        id=row.id,
        provider_id=row.provider_id,
        name=row.name,
        amount=row.amount,
        currency=row.currency,
        billing_interval=cadence,
    )


def timestamp(value: datetime) -> str:
    return (value.replace(tzinfo=UTC) if value.tzinfo is None else value).isoformat()


async def run_analysis(
    session: AsyncSession,
    job: JobModel,
    pipeline: AnalysisPipeline | None = None,
) -> None:
    analysis = await session.scalar(
        select(AnalysisModel).where(
            AnalysisModel.id == UUID(job.payload["analysis_id"]),
            AnalysisModel.user_id == job.user_id,
        )
    )
    if analysis is None:
        raise PermanentJobError("analysis_not_found")
    subscription = await session.scalar(
        select(SubscriptionModel).where(
            SubscriptionModel.id == analysis.subscription_id,
            SubscriptionModel.user_id == job.user_id,
            SubscriptionModel.deleted_at.is_(None),
        )
    )
    if subscription is None:
        raise PermanentJobError("subscription_not_found")
    plan = await session.get(PlanModel, subscription.plan_id)
    prompt = await session.get(PromptVersionModel, analysis.prompt_version_id)
    if plan is None or prompt is None:
        raise PermanentJobError("analysis_configuration_missing")
    transactions = list(
        (
            await session.scalars(
                select(TransactionModel)
                .where(
                    TransactionModel.subscription_id == subscription.id,
                    TransactionModel.user_id == job.user_id,
                )
                .order_by(TransactionModel.id)
            )
        ).all()
    )
    usage = list(
        (
            await session.scalars(
                select(UsageEventModel)
                .where(
                    UsageEventModel.subscription_id == subscription.id,
                    UsageEventModel.user_id == job.user_id,
                )
                .order_by(UsageEventModel.id)
            )
        ).all()
    )
    if not transactions and not usage:
        raise PermanentJobError("missing_evidence")
    now = datetime.now(UTC)
    usage_unknown = not usage or any(
        row.is_unknown or (row.quantity is not None and row.quantity < 0) for row in usage
    )
    usage_level = classify_usage(
        None
        if usage_unknown
        else sum(1 for row in usage if row.quantity is None or row.quantity > 0)
    )
    latest = max((row.occurred_at for row in usage), default=None)
    freshness = evidence_freshness(latest, now)
    cost = normalize_cost(plan.amount, plan.currency, plan.billing_interval)
    snapshots: list[tuple[str, UUID, dict[str, Any]]] = [
        (
            "transactions",
            row.id,
            {
                "amount": str(row.amount),
                "currency": row.currency,
                "occurred_at": timestamp(row.occurred_at),
            },
        )
        for row in transactions
    ] + [
        (
            "usage_events",
            row.id,
            {
                "kind": row.kind,
                "is_unknown": row.is_unknown,
                "quantity": str(row.quantity) if row.quantity is not None else None,
                "occurred_at": timestamp(row.occurred_at),
            },
        )
        for row in usage
    ]
    alternatives = list(
        (
            await session.scalars(
                select(PlanModel)
                .join(
                    SubscriptionAlternativeModel,
                    SubscriptionAlternativeModel.plan_id == PlanModel.id,
                )
                .where(SubscriptionAlternativeModel.subscription_id == subscription.id)
            )
        ).all()
    )
    for row in [plan, *alternatives]:
        snapshots.append(
            (
                "plans",
                row.id,
                {
                    "amount": str(row.amount),
                    "currency": row.currency,
                    "billing_interval": row.billing_interval,
                },
            )
        )
    context = {
        "alternatives": [
            {
                "id": str(row.id),
                "amount": str(row.amount),
                "currency": row.currency,
                "billing_interval": row.billing_interval,
            }
            for row in alternatives
        ],
        "prompt": prompt.template,
        "prompt_version": prompt.version,
        "schema_version": prompt.schema_version,
        "features": {
            "usage": usage_level.value,
            "freshness": freshness.value,
            "cost_status": cost.status.value,
            "monthly_cost": str(cost.monthly.amount) if cost.monthly else None,
            "annual_cost": str(cost.annual.amount) if cost.annual else None,
            "currency": plan.currency,
        },
        "evidence": [
            {"id": str(key), "source_table": table, "snapshot": snapshot}
            for table, key, snapshot in snapshots
        ],
    }
    # Validate even injected adapters: the provider boundary is never trusted.
    result = await (pipeline or HttpAnalysisPipeline()).recommend(context)
    try:
        draft = RecommendationDraft.model_validate(result.model_dump())
    except ValidationError:
        raise PermanentJobError("invalid_provider_output") from None
    cited = set(draft.evidence_ids)
    if not cited.issubset({key for _, key, _ in snapshots}):
        raise PermanentJobError("unsupported_evidence_reference")
    # No automatic destructive recommendation from absent/stale/unknown usage.
    # Downgrade savings are checked against stored alternative plans below.
    if draft.action == RecommendationAction.CANCEL and (
        usage_unknown or freshness.value != "fresh" or usage_level.value != "unused"
    ):
        raise PermanentJobError("unsupported_recommendation")
    monthly = annual = Decimal("0")
    alternative_plan: Plan | None = None
    if draft.action == RecommendationAction.DOWNGRADE:
        alternative = next(
            (row for row in alternatives if row.id == draft.alternative_plan_id), None
        )
        if (
            alternative is None
            or alternative.currency != plan.currency
            or usage_unknown
            or freshness.value != "fresh"
        ):
            raise PermanentJobError("unsupported_alternative")
        alternative_plan = domain_plan(alternative)
        current_periods = charges_per_year(plan.billing_interval)
        alternative_periods = charges_per_year(alternative_plan.billing_interval)
        if current_periods is None or alternative_periods is None:
            raise PermanentJobError("unsupported_cost")
        # Compare exact annual costs before either display value is rounded.
        if plan.amount * current_periods <= alternative_plan.amount * alternative_periods:
            raise PermanentJobError("alternative_not_cheaper")
    if draft.action in (RecommendationAction.CANCEL, RecommendationAction.DOWNGRADE):
        savings = calculate_savings(domain_plan(plan), alternative_plan)
        if savings.status == AnalysisStatus.CURRENCY_MISMATCH:
            raise PermanentJobError("unsupported_alternative")
        if savings.status != AnalysisStatus.OK or savings.monthly is None or savings.annual is None:
            raise PermanentJobError("unsupported_cost")
        monthly, annual = savings.monthly.amount, savings.annual.amount
        # A positive annual saving may have a zero monthly display. Accept it
        # when the annual saving is representable; reject sub-cent annual gains.
        if draft.action == RecommendationAction.DOWNGRADE and annual <= 0:
            raise PermanentJobError("savings_below_precision")
    recommendation = RecommendationModel(
        id=uuid4(),
        user_id=job.user_id,
        analysis_id=analysis.id,
        version=1,
        recommended_action=draft.action,
        confidence=draft.confidence,
        rationale=draft.rationale,
        uncertainty_json={
            "level": "high" if usage_unknown else "low",
            "reason": "missing_usage" if usage_unknown else "observed_usage",
        },
        monthly_savings_amount=monthly,
        annual_savings_amount=annual,
        currency=plan.currency,
        prompt_version=prompt.version,
        schema_version=prompt.schema_version,
    )
    session.add(recommendation)
    await session.flush()
    if (
        alternative_plan is not None
        and sum(table == "plans" and key == alternative_plan.id for table, key, _ in snapshots) != 1
    ):
        raise PermanentJobError("ambiguous_selected_target")
    for table, key, snapshot in snapshots:
        evidence_type = {"transactions": "billing", "plans": "plan", "usage_events": "usage"}[table]
        if alternative_plan is not None and table == "plans" and key == alternative_plan.id:
            # The selected, validated plan is part of the immutable result,
            # independent of rationale, citations, prices or later catalog edits.
            evidence_type = "selected_downgrade_target"
            snapshot = {**snapshot, "target_schema_version": "1.0"}
        session.add(
            RecommendationEvidenceModel(
                user_id=job.user_id,
                recommendation_id=recommendation.id,
                evidence_type=evidence_type,
                source_table=table,
                source_id=key,
                snapshot_json=snapshot,
            )
        )
    await session.flush()
