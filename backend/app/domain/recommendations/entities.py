import uuid  # unique ids
from dataclasses import dataclass  # plain data holders
from datetime import datetime  # timestamps
from decimal import Decimal  # exact numbers for money and confidence
from typing import Any  # JSON-like values


@dataclass(frozen=True)  # read-only record of one piece of evidence
class RecommendationEvidence:
    id: uuid.UUID  # evidence id
    evidence_type: str  # kind of evidence, such as usage
    source_table: str  # table the evidence came from
    source_id: uuid.UUID | None  # row the evidence came from
    snapshot: dict[str, Any]  # frozen copy of the evidence at analysis time
    created_at: datetime  # when it was recorded


@dataclass(frozen=True)  # read-only recommendation snapshot
class Recommendation:
    id: uuid.UUID  # recommendation id
    analysis_id: uuid.UUID  # analysis that produced it
    subscription_id: uuid.UUID  # subscription it is about
    analysis_status: str  # state of the analysis, such as succeeded
    analysis_completed_at: datetime | None  # when the analysis finished
    version: int  # recommendation version
    recommended_action: str  # keep, downgrade, cancel or review
    confidence: Decimal  # confidence between 0 and 1
    rationale: str  # plain explanation
    uncertainty: dict[str, Any]  # structured uncertainty details
    monthly_savings_amount: Decimal  # deterministic monthly savings
    annual_savings_amount: Decimal  # deterministic annual savings
    currency: str  # currency of both savings
    prompt_version: str  # prompt version used
    schema_version: str  # output schema version used
    created_at: datetime  # when the snapshot was created
    evidence: list[RecommendationEvidence]  # supporting evidence
