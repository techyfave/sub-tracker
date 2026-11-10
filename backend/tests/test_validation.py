
from decimal import Decimal

import pytest

from app.domain.recommendations.enums import RecommendationAction
from app.domain.recommendations.schema import (
    DeterministicSavings,
    EvidenceReference,
    RecommendationContract,
)
from app.domain.recommendations.validation import (
    EvidenceGroundingError,
    validate_evidence,
    validate_savings,
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
        rationale="The subscription is actively used.",
        savings=DeterministicSavings(
            amount=Decimal("0.00"),
            currency="NGN",
            period="month",
        ),
        prompt_version="recommendation_prompt_v1",
        schema_version="recommendation_schema_v1",
    )


def test_rejects_unsupported_evidence(valid_recommendation):
    allowed_evidence = {
        "subscription_002": EvidenceReference(
            evidence_id="subscription_002",
            source="supplied",
            fact_path="subscription.id",
        )
    }

    with pytest.raises(EvidenceGroundingError):
        validate_evidence(
            valid_recommendation,
            allowed_evidence,
        )


def test_accepts_supplied_evidence(valid_recommendation):
    allowed_evidence = {
        "subscription_001": EvidenceReference(
            evidence_id="subscription_001",
            source="supplied",
            fact_path="subscription.id",
        )
    }

    assert validate_evidence(
        valid_recommendation,
        allowed_evidence,
    ) == tuple(allowed_evidence.values())


def test_rejects_a_claimed_path_that_differs_from_the_supplied_fact(valid_recommendation):
    allowed_evidence = {
        "subscription_001": EvidenceReference(
            evidence_id="subscription_001",
            source="supplied",
            fact_path="subscription.name",
        )
    }

    with pytest.raises(EvidenceGroundingError):
        validate_evidence(valid_recommendation, allowed_evidence)


def test_savings_must_match_backend_calculation(valid_recommendation):
    expected = DeterministicSavings(
        amount=Decimal("0.00"),
        currency="NGN",
        period="month",
    )
    validate_savings(valid_recommendation, expected)

    with pytest.raises(ValueError):
        validate_savings(
            valid_recommendation,
            DeterministicSavings(
                amount=Decimal("1.00"),
                currency="NGN",
                period="month",
            ),
        )
