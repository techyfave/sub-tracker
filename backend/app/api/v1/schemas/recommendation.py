from __future__ import annotations  # allow modern type hints

import uuid  # unique ids
from datetime import datetime  # timestamps
from decimal import Decimal  # exact numbers
from typing import Any  # JSON-like values

from pydantic import BaseModel, Field  # schema tools

from app.api.v1.schemas.common import MoneySchema, PaginatedResponse  # shared schemas
from app.infrastructure.database.models import RecommendationAction, WorkStatus  # enums


class VersionInfo(BaseModel):
    recommendation_version: int  # version of this recommendation
    prompt_version: str  # prompt version used
    schema_version: str  # output schema version used


class AnalysisState(BaseModel):
    analysis_id: uuid.UUID  # analysis that produced it
    subscription_id: uuid.UUID  # subscription it is about
    status: WorkStatus  # state of the analysis
    completed_at: datetime | None  # when the analysis finished


class UncertaintyInfo(BaseModel):
    confidence: Decimal = Field(ge=0, le=1)  # confidence between 0 and 1
    details: dict[str, Any]  # structured uncertainty details


class SavingsInfo(BaseModel):
    monthly: MoneySchema  # deterministic monthly savings
    annual: MoneySchema  # deterministic annual savings


class EvidenceResponse(BaseModel):
    id: uuid.UUID  # evidence id
    evidence_type: str  # kind of evidence
    source_table: str  # table the evidence came from
    source_id: uuid.UUID | None  # row the evidence came from
    snapshot: dict[str, Any]  # frozen copy of the evidence
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
