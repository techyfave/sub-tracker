from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.consents.rule import validate_policy_version, validate_scopes


class ConsentCreateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "policy_version": "2026-10",
                    "scopes": [
                        "subscriptions.read",
                        "analytics.use",
                    ],
                }
            ]
        },
    )

    policy_version: str = Field(min_length=1, max_length=50)
    scopes: list[str] = Field(min_length=1, max_length=50)

    @field_validator("policy_version")
    @classmethod
    def policy_version_is_valid(cls, value: str) -> str:
        return validate_policy_version(value)

    @field_validator("scopes")
    @classmethod
    def scopes_are_valid(cls, value: list[str]) -> list[str]:
        return validate_scopes(value)


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_version: str
    scopes: list[str]
    granted_at: datetime
    revoked_at: datetime | None

    @field_validator("revoked_at", mode="before")
    @classmethod
    def ensure_revoked_at_is_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)


class ConsentListResponse(BaseModel):
    items: list[ConsentResponse]
