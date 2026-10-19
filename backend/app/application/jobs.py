"""Provider-neutral durable job contracts; callers own the enqueue transaction."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class JobRequest:
    user_id: UUID
    job_type: str
    idempotency_key: str
    payload: dict[str, str]
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if not self.job_type or len(self.job_type) > 100:
            raise ValueError("job_type must contain 1-100 characters")
        if not self.idempotency_key or len(self.idempotency_key) > 255:
            raise ValueError("idempotency_key must contain 1-255 characters")
        if not 1 <= self.max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")


class JobPort(Protocol):
    async def enqueue(self, request: JobRequest) -> UUID:
        """Persist work in the caller's transaction; do not publish before commit."""
        ...


class IdempotencyConflict(ValueError):
    """A key was reused with different inputs."""


class RetryableJobError(Exception):
    """A handler explicitly classified a temporary failure; details are not logged."""


class PermanentJobError(Exception):
    """A handler rejected the work; operator intervention is required."""
