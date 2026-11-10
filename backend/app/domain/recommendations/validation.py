
from collections.abc import Mapping
from decimal import Decimal

from app.domain.analysis.features import Freshness, UsageLevel
from app.domain.recommendations.enums import RecommendationAction
from app.domain.recommendations.schema import (
    DeterministicSavings,
    EvidenceReference,
    RecommendationContract,
    RecommendationModelOutput,
)


class EvidenceGroundingError(ValueError):
    """A model reference does not match evidence supplied to this invocation."""


class RecommendationPolicyError(ValueError):
    """The proposed action conflicts with deterministic business policy."""


def validate_evidence(
    recommendation: RecommendationModelOutput,
    allowed_evidence: Mapping[str, EvidenceReference],
) -> tuple[EvidenceReference, ...]:
    references: list[EvidenceReference] = []
    seen: set[str] = set()
    for reference in recommendation.evidence_references:
        if reference.evidence_id in seen:
            raise EvidenceGroundingError("Duplicate evidence reference.")
        seen.add(reference.evidence_id)
        allowed = allowed_evidence.get(reference.evidence_id)
        if allowed is None:
            raise EvidenceGroundingError("Unsupported evidence reference.")
        if (
            reference.source != allowed.source
            or reference.fact_path != allowed.fact_path
            or reference.derivation != allowed.derivation
        ):
            raise EvidenceGroundingError("Evidence reference does not match its supplied fact.")
        references.append(allowed)
    if not references:
        raise EvidenceGroundingError("At least one grounded evidence reference is required.")
    return tuple(references)


def validate_evidence_relevance(
    recommendation: RecommendationModelOutput,
    grounded_references: tuple[EvidenceReference, ...],
) -> None:
    required_paths = {"usage.level", "usage.freshness"}
    if recommendation.action == RecommendationAction.CANCEL:
        required_paths.add("savings.cancellation_monthly")
    elif recommendation.action == RecommendationAction.DOWNGRADE:
        required_paths.add("savings.downgrade_monthly")
    grounded_paths = {reference.fact_path for reference in grounded_references}
    if not required_paths.issubset(grounded_paths):
        raise EvidenceGroundingError("Recommendation omits required supporting evidence.")


def validate_business_policy(
    recommendation: RecommendationModelOutput,
    *,
    usage_level: UsageLevel,
    freshness: Freshness,
    cancellation_savings: DeterministicSavings,
    downgrade_savings: DeterministicSavings | None,
) -> DeterministicSavings:
    action = recommendation.action
    needs_review = usage_level == UsageLevel.UNKNOWN or freshness in {
        Freshness.UNKNOWN,
        Freshness.STALE,
    }
    if needs_review and action != RecommendationAction.REVIEW:
        raise RecommendationPolicyError("Insufficient or stale usage evidence requires review.")

    if action == RecommendationAction.REVIEW:
        return DeterministicSavings(
            amount=Decimal("0"),
            currency=cancellation_savings.currency,
            period="month",
        )
    if action == RecommendationAction.KEEP:
        return DeterministicSavings(
            amount=Decimal("0"),
            currency=cancellation_savings.currency,
            period="month",
        )
    if action == RecommendationAction.CANCEL:
        if usage_level != UsageLevel.UNUSED or freshness not in {
            Freshness.FRESH,
            Freshness.AGING,
        }:
            raise RecommendationPolicyError("Cancellation requires recent evidence of no usage.")
        if cancellation_savings.amount <= 0:
            raise RecommendationPolicyError(
                "Cancellation must yield positive deterministic savings."
            )
        return cancellation_savings
    if action == RecommendationAction.DOWNGRADE:
        if downgrade_savings is None or downgrade_savings.amount <= 0:
            raise RecommendationPolicyError("Downgrade requires a cheaper supported alternative.")
        if freshness not in {Freshness.FRESH, Freshness.AGING}:
            raise RecommendationPolicyError("Downgrade requires recent usage evidence.")
        return downgrade_savings
    raise RecommendationPolicyError("Unsupported recommendation action.")


def validate_savings(
    recommendation: RecommendationContract,
    expected: DeterministicSavings,
) -> None:
    if recommendation.savings != expected:
        raise RecommendationPolicyError("Recommendation savings are not backend-calculated.")
