"""Provider boundary: structured output is untrusted until validated locally."""

import asyncio
import json
from decimal import Decimal
from typing import Any, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.application.jobs import PermanentJobError, RetryableJobError
from app.core.config import get_settings
from app.infrastructure.database.models.core import RecommendationAction


class RecommendationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: RecommendationAction
    alternative_plan_id: UUID | None = None
    confidence: Decimal = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=4000)
    evidence_ids: list[UUID] = Field(min_length=1, max_length=200)


class AnalysisPipeline(Protocol):
    async def recommend(self, context: dict[str, Any]) -> RecommendationDraft: ...


class HttpAnalysisPipeline:
    """POST a versioned prompt, facts and JSON schema to a trusted AI gateway.

    The gateway must return a JSON object matching RecommendationDraft, without
    markdown. No raw provider response or exception text is persisted or logged.
    """

    async def recommend(self, context: dict[str, Any]) -> RecommendationDraft:
        settings = get_settings()
        if not settings.analysis_provider_url or not settings.analysis_provider_token:
            raise PermanentJobError("analysis_provider_unconfigured")
        if not settings.analysis_provider_url.startswith("https://"):
            raise PermanentJobError("analysis_provider_requires_https")

        def send() -> bytes:
            request = Request(
                settings.analysis_provider_url,
                data=json.dumps(
                    {"context": context, "response_schema": RecommendationDraft.model_json_schema()}
                ).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.analysis_provider_token}",
                },
                method="POST",
            )
            with urlopen(request, timeout=60) as response:  # noqa: S310
                content = response.read(65537)
                if len(content) > 65536:
                    raise PermanentJobError("provider_response_too_large")
                return cast(bytes, content)

        try:
            raw = await asyncio.to_thread(send)
            return RecommendationDraft.model_validate_json(raw)
        except HTTPError as exc:
            if exc.code == 429 or exc.code >= 500:
                raise RetryableJobError("provider_unavailable") from None
            raise PermanentJobError("provider_rejected_request") from None
        except (URLError, TimeoutError):
            raise RetryableJobError("provider_unavailable") from None
        except (ValidationError, ValueError):
            raise PermanentJobError("invalid_provider_output") from None
