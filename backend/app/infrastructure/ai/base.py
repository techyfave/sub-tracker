
from abc import ABC, abstractmethod
from typing import Any


class AIProviderError(Exception):
    """Base exception for AI provider failures."""


class AIProviderTimeoutError(AIProviderError):
    """Raised when an AI request times out."""


class AIProviderUnavailableError(AIProviderError):
    """Raised when the AI provider is unavailable."""


class PermanentAIProviderError(AIProviderError):
    """Raised when an AI request fails permanently."""

class AIProvider(ABC):
    """
    Contract that every AI provider must implement.

    This allows us to replace OpenAI with another provider
    without changing the recommendation service.
    """

    @abstractmethod
    async def generate(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate a structured recommendation from bounded context.

        Args:
            context: Sanitized information supplied by the backend.

        Returns:
            A dictionary containing the model's recommendation.
        """
        raise NotImplementedError
