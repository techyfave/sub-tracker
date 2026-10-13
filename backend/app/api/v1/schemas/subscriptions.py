from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID

class TransactionCreate(BaseModel):
    amount: float = Field(..., description="The transaction fee value.")
    currency: str = Field(..., max_length=3, description="ISO currency code.")
    occurrence_time: datetime = Field(..., description="When the charge actually occurred.")
    source: str = Field(..., description="System origin details.")
    external_id: Optional[str] = Field(None, description="External reference ID for duplicate suppression.")

class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subscription_id: UUID
    amount: float
    currency: str
    occurrence_time: datetime
    source: str
    external_id: Optional[str]

class UsageEventCreate(BaseModel):
    subscription_id: UUID
    occurrence_time: datetime = Field(..., description="Timestamp when usage occurred.")
    units_used: Optional[float] = Field(None, description="Quantified units. Null means Unknown Usage.")
    is_unknown: bool = Field(False, description="Explicit flag marking tracking as unknown.")
    source: str = Field(..., description="Source provenance identifier.")
    idempotency_key: Optional[str] = Field(None, description="Unique constraint mapping key.")

class UsageEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    subscription_id: UUID
    occurrence_time: datetime
    units_used: Optional[float]
    is_unknown: bool
    source: str
    idempotency_key: Optional[str]
