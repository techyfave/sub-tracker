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
from app.domain.analysis.features import classify_usage, evidence_freshness, normalize_cost
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
                "occurred_at": row.occurred_at.isoformat(),
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
                "occurred_at": row.occurred_at.isoformat(),
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
    if draft.action == RecommendationAction.CANCEL:
        if cost.monthly is None or cost.annual is None:
            raise PermanentJobError("unsupported_cost")
        monthly, annual = cost.monthly.amount, cost.annual.amount
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
        alternative_cost = normalize_cost(
            alternative.amount,
            alternative.currency,
            alternative.billing_interval,
        )
        if (
            cost.monthly is None
            or cost.annual is None
            or alternative_cost.monthly is None
            or alternative_cost.annual is None
        ):
            raise PermanentJobError("unsupported_cost")
        monthly = cost.monthly.amount - alternative_cost.monthly.amount
        annual = cost.annual.amount - alternative_cost.annual.amount
        if monthly <= 0 or annual <= 0:
            raise PermanentJobError("alternative_not_cheaper")
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
    for table, key, snapshot in snapshots:
        session.add(
            RecommendationEvidenceModel(
                user_id=job.user_id,
                recommendation_id=recommendation.id,
                evidence_type={"transactions": "billing", "plans": "plan", "usage_events": "usage"}[
                    table
                ],
                source_table=table,
                source_id=key,
                snapshot_json=snapshot,
            )
        )
    await session.flush()
