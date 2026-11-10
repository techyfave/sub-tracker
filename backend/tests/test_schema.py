from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.recommendations.enums import RecommendationAction
from app.domain.recommendations.schema import (
    DeterministicSavings,
    EvidenceReference,
    RecommendationContract,
)


@pytest.fixture
def valid_recommendation():
    return RecommendationContract(
        action=RecommendationAction.KEEP,
        confidence=Decimal("0.95"),
        uncertainty=Decimal("0.05"),
        evidence_references=(
            EvidenceReference(
                evidence_id="subscription_001",
                source="supplied",
                fact_path="subscription.id",
            ),
        ),
        missing_information=(),
        conflicting_information=(),
        rationale="The subscription is actively used.",
        savings=DeterministicSavings(
            amount=Decimal("0.00"),
            currency="NGN",
            period="month",
        ),
        prompt_version="recommendation_prompt_v1",
        schema_version="recommendation_schema_v1",
    )


def test_valid_recommendation(valid_recommendation):
    assert valid_recommendation.action == RecommendationAction.KEEP


def test_recommendation_is_immutable(valid_recommendation):
    with pytest.raises(ValidationError):
        valid_recommendation.confidence = 0.5


def test_confidence_cannot_exceed_one():
    with pytest.raises(ValidationError):
        RecommendationContract(
            action="keep",
            confidence=Decimal("1.5"),
            uncertainty=Decimal("0"),
            evidence_references=(
                EvidenceReference(
                    evidence_id="subscription_001",
                    source="supplied",
                    fact_path="subscription.id",
                ),
            ),
            rationale="Test",
            savings={
                "amount": Decimal("0.00"),
                "currency": "NGN",
                "period": "month",
            },
            prompt_version="v1",
            schema_version="v1",
        )


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        RecommendationContract(
            action="keep",
            confidence=Decimal("0.9"),
            uncertainty=Decimal("0.1"),
            evidence_references=(
                EvidenceReference(
                    evidence_id="subscription_001",
                    source="supplied",
                    fact_path="subscription.id",
                ),
            ),
            rationale="Test",
            savings={
                "amount": Decimal("0.00"),
                "currency": "NGN",
                "period": "month",
            },
            prompt_version="v1",
            schema_version="v1",
            invented_field="not_allowed",
        )


def test_review_requires_a_reason():
    with pytest.raises(ValidationError):
        RecommendationContract(
            action="review",
            confidence=Decimal("0.5"),
            uncertainty=Decimal("0.5"),
            evidence_references=(
                EvidenceReference(
                    evidence_id="subscription_001",
                    source="supplied",
                    fact_path="subscription.id",
                ),
            ),
            rationale="Review this subscription.",
            savings=DeterministicSavings(
                amount=Decimal("0"),
                currency="NGN",
                period="month",
            ),
            prompt_version="v1",
            schema_version="v1",
        )