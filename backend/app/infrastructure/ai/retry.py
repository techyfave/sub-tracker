import asyncio
from typing import Any

from app.infrastructure.ai.base import (
    AIProvider,
    AIProviderError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)


class RetryingAIProvider:
    def __init__(
        self,
        provider: AIProvider,
        max_attempts: int = 3,
        delay_seconds: float = 2.0,
    ) -> None:
        self.provider = provider
        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds

    async def generate(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        for attempt in range(1, self.max_attempts + 1):
            try:
                return await self.provider.generate(context)

            except (
                AIProviderUnavailableError,
                AIProviderTimeoutError,
            ):
                if attempt == self.max_attempts:
                    raise

                await asyncio.sleep(
                    self.delay_seconds * attempt
                )

            except AIProviderError:
                # Permanent or invalid requests should not be retried.
                raise

        raise AIProviderError("AI retry attempts exhausted.")

    async def close(self) -> None:
        await self.provider.close()