
from copy import deepcopy
from typing import Any

from app.infrastructure.ai.base import PermanentAIProviderError


class FakeAIProvider:
    def __init__(
        self,
        response: dict[str, Any] | list[dict[str, Any] | Exception],
    ):
        self._responses = [response] if isinstance(response, dict) else list(response)
        if not self._responses:
            raise ValueError("the fake provider requires at least one response")
        self.calls = 0
        self.requests: list[dict[str, Any]] = []

    async def generate_structured(
        self,
        *,
        system_prompt: str,
        context: dict[str, Any],
        output_schema: dict[str, Any],
        prompt_version: str,
        repair_feedback: str | None,
    ) -> dict[str, Any]:
        self.requests.append(
            deepcopy(
                {
                    "system_prompt": system_prompt,
                    "context": context,
                    "output_schema": output_schema,
                    "prompt_version": prompt_version,
                    "repair_feedback": repair_feedback,
                }
            )
        )
        if self.calls >= len(self._responses):
            raise PermanentAIProviderError("fake provider response sequence exhausted")
        response = self._responses[self.calls]
        self.calls += 1
        if isinstance(response, Exception):
            raise response
        return deepcopy(response)
