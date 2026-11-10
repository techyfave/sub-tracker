from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalysisCreateRequest(BaseModel):
    subscription_id: UUID


class AnalysisCreateResponse(BaseModel):
    id: UUID
    status: str
    created_at: datetime


class AnalysisStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subscription_id: UUID
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    failure_code: str | None = None
    failure_message: str | None = None
