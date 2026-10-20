from __future__ import annotations  # allow modern type hints

import re  # pattern matching for safe values
import uuid  # unique ids
from datetime import datetime  # timestamps
from decimal import Decimal  # exact numbers
from enum import StrEnum  # string enum base
from typing import Any  # raw stored JSON values

from pydantic import BaseModel, Field  # schema tools

from app.api.v1.schemas.common import MoneySchema, PaginatedResponse  # shared schemas
from app.infrastructure.database.models import RecommendationAction, WorkStatus  # stored enums


class AnalysisStatus(StrEnum):
    """Public analysis states, as defined in doc/TERMINOLOGY.md."""

    QUEUED = "queued"  # waiting to start
    RUNNING = "running"  # in progress
    COMPLETED = "completed"  # finished successfully
    FAILED = "failed"  # finished with an error


# stored worker status -> public analysis status; the only place the two vocabularies meet
_STORED_TO_PUBLIC: dict[WorkStatus, AnalysisStatus] = {
    WorkStatus.QUEUED: AnalysisStatus.QUEUED,  # same word
    WorkStatus.RUNNING: AnalysisStatus.RUNNING,  # same word
    WorkStatus.SUCCEEDED: AnalysisStatus.COMPLETED,  # job word becomes analysis word
    WorkStatus.FAILED: AnalysisStatus.FAILED,  # same word
}


def to_public_status(stored: str) -> AnalysisStatus:
    # convert a stored status text to the public analysis status
    return _STORED_TO_PUBLIC[WorkStatus(stored)]


def to_stored_status(public: AnalysisStatus) -> str:
    # convert a public analysis status back to the stored text used by the queries
    for stored, mapped in _STORED_TO_PUBLIC.items():
        # find the stored status that maps to this public one
        if mapped == public:
            # return its stored text
            return stored.value
    # unreachable while every public status is mapped
    raise ValueError(f"Unmapped analysis status: {public}")


# a value is safe to publish only if it is a short simple token, never free text
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")
# Numeric(18, 4) snapshots remain decimal strings; never coerce through float.
_PUBLIC_DECIMAL = re.compile(r"^[0-9]{1,14}(?:\.[0-9]{1,4})?$")
_PUBLIC_CURRENCY = re.compile(r"^[A-Z]{3}$")
_PUBLIC_CADENCES = frozenset({"daily", "weekly", "monthly", "yearly"})
TYPED_EVIDENCE_KEYS = frozenset(
    {
        "amount",
        "currency",
        "occurred_at",
        "kind",
        "is_unknown",
        "quantity",
        "billing_interval",
    }
)
# the only uncertainty keys that are public
PUBLIC_UNCERTAINTY_KEYS = ("level", "reason")
# the only evidence snapshot keys that are public
PUBLIC_EVIDENCE_KEYS = (
    frozenset(
        {
            "sessions",  # how many sessions were observed
            "value_signal",  # high, low, none or uncertain
            "supports",  # which action the evidence supports
            "lower_tier_suitable",  # whether a cheaper plan would do
            "requires_review",  # whether a human must check
            "usage_available",  # whether usage data existed
            "reason",  # short reason code
            "usage_signal",  # usage side of a conflict
            "billing_signal",  # billing side of a conflict
            "conflict",  # whether the sources disagree
        }
    )
    | TYPED_EVIDENCE_KEYS
)
# the kinds of value an evidence snapshot may publish
PublicValue = str | int | bool | None


def _is_public_value(value: object) -> bool:
    # null and booleans are safe
    if value is None or isinstance(value, bool):
        return True
    # whole numbers are safe
    if isinstance(value, int):
        return True
    # strings are safe only when they are short simple tokens
    if isinstance(value, str):
        return _SAFE_TOKEN.fullmatch(value) is not None
    # dictionaries, lists, floats and everything else are dropped
    return False


def public_snapshot(raw: dict[str, Any]) -> dict[str, PublicValue]:
    # keep only allowlisted keys whose values are simple; nested values never pass
    return {
        key: value
        for key, value in raw.items()
        if key in PUBLIC_EVIDENCE_KEYS and _is_public_evidence_value(key, value)
    }


def _is_public_evidence_value(key: str, value: object) -> bool:
    """Validate new evidence fields by type, retaining the #14 summary contract."""
    if key in ("amount", "quantity"):
        if key == "quantity" and value is None:
            return True  # Missing quantity is distinct from an observed zero.
        return isinstance(value, str) and _PUBLIC_DECIMAL.fullmatch(value) is not None
    if key == "currency":
        return isinstance(value, str) and _PUBLIC_CURRENCY.fullmatch(value) is not None
    if key == "is_unknown":
        return isinstance(value, bool)
    if key == "kind":
        return isinstance(value, str) and _SAFE_TOKEN.fullmatch(value) is not None
    if key == "billing_interval":
        return isinstance(value, str) and value in _PUBLIC_CADENCES
    if key == "occurred_at":
        if not isinstance(value, str) or len(value) > 40 or "T" not in value:
            return False
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return False
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    return _is_public_value(value)


def public_uncertainty(raw: dict[str, Any]) -> dict[str, str | None]:
    # start with nothing public
    result: dict[str, str | None] = {}
    # look only at the allowlisted keys
    for key in PUBLIC_UNCERTAINTY_KEYS:
        # read the stored value
        value = raw.get(key)
        # keep it only when it is a simple token string
        result[key] = value if isinstance(value, str) and _SAFE_TOKEN.fullmatch(value) else None
    # hand back the safe projection
    return result


class VersionInfo(BaseModel):
    recommendation_version: int  # version of this recommendation
    prompt_version: str  # prompt version used
    schema_version: str  # output schema version used


class AnalysisState(BaseModel):
    analysis_id: uuid.UUID  # analysis that produced it
    subscription_id: uuid.UUID  # subscription it is about
    status: AnalysisStatus  # public analysis state
    completed_at: datetime | None  # when the analysis finished


class UncertaintyInfo(BaseModel):
    confidence: Decimal = Field(ge=0, le=1)  # confidence between 0 and 1
    level: str | None  # public level such as low, medium or high
    reason: str | None  # public reason code such as missing_usage


class SavingsInfo(BaseModel):
    monthly: MoneySchema  # deterministic monthly savings
    annual: MoneySchema  # deterministic annual savings


class EvidenceResponse(BaseModel):
    id: uuid.UUID  # evidence id
    evidence_type: str  # kind of evidence
    source_table: str  # table the evidence came from
    source_id: uuid.UUID | None  # row the evidence came from
    snapshot: dict[str, PublicValue]  # allowlisted summary of the evidence
    created_at: datetime  # when it was recorded


class RecommendationResponse(BaseModel):
    id: uuid.UUID  # recommendation id
    recommended_action: RecommendationAction  # keep, downgrade, cancel or review
    rationale: str  # plain explanation
    versions: VersionInfo  # version information
    analysis: AnalysisState  # analysis state
    uncertainty: UncertaintyInfo  # uncertainty
    savings: SavingsInfo  # savings
    evidence: list[EvidenceResponse]  # evidence provenance
    created_at: datetime  # when the snapshot was created


# paginated list of recommendations
RecommendationListResponse = PaginatedResponse[RecommendationResponse]
