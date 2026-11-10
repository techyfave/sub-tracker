from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.recommendations.enums import RecommendationAction


class ImmutableSchema(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
    )


class EvidenceReference(ImmutableSchema):
    evidence_id: str = Field(min_length=1, max_length=100)
    source: Literal["supplied", "derived"]
    fact_path: str = Field(min_length=1, max_length=100)
    derivation: str | None = Field(default=None, max_length=200)


class MissingInformation(ImmutableSchema):
    field: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=300)


class ConflictingInformation(ImmutableSchema):
    field: str = Field(min_length=1, max_length=100)
    evidence_ids: tuple[str, ...] = Field(min_length=2, max_length=10)
    explanation: str = Field(min_length=1, max_length=300)


class DeterministicSavings(ImmutableSchema):
    amount: Decimal = Field(ge=0, max_digits=18, decimal_places=4)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    period: Literal["month", "year"]


class RecommendationModelOutput(ImmutableSchema):
    """Untrusted model output; authoritative savings and versions are not model fields."""

    action: RecommendationAction

    confidence: Decimal = Field(ge=0, le=1)
    uncertainty: Decimal = Field(ge=0, le=1)

    evidence_references: tuple[EvidenceReference, ...] = Field(max_length=20)

    missing_information: tuple[MissingInformation, ...] = Field(default=(), max_length=10)
    conflicting_information: tuple[ConflictingInformation, ...] = Field(default=(), max_length=10)

    rationale: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_review_and_uncertainty(self) -> RecommendationModelOutput:
        if self.action == RecommendationAction.REVIEW and not (
            self.missing_information or self.conflicting_information
        ):
            raise ValueError("Review requires missing or conflicting information.")
        if self.uncertainty > Decimal("0.5") and self.action != RecommendationAction.REVIEW:
            raise ValueError("High uncertainty requires review.")
        return self


class RecommendationContract(RecommendationModelOutput):
    """Validated, persistence-ready recommendation with server-owned metadata."""

    savings: DeterministicSavings
    prompt_version: str = Field(min_length=1, max_length=50)
    schema_version: str = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_savings_rules(self) -> RecommendationContract:
        if self.action in (
            RecommendationAction.KEEP,
            RecommendationAction.REVIEW,
        ) and self.savings.amount != Decimal("0"):
            raise ValueError("Keep and review recommendations must have zero savings.")
        return self