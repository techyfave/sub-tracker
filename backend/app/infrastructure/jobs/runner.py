"""PostgreSQL claims, fencing and atomic domain-result/job completion."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from app.application.jobs import JobStatus, PermanentJobError, RetryableJobError
from app.infrastructure.database.models.job import JobModel

Handler = Callable[[AsyncSession, JobModel], Awaitable[None]]
logger = logging.getLogger(__name__)


def due(now: datetime) -> ColumnElement[bool]:
    # Kept in one place so recovery and normal dispatch use the same eligibility rule.
    return or_(
        and_(JobModel.status == JobStatus.QUEUED, JobModel.available_at <= now),
        and_(JobModel.status == JobStatus.RUNNING, JobModel.lease_until <= now),
    )


class JobRunner:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        handlers: dict[str, Handler],
        *,
        timeout_seconds: float = 240,
        lease_seconds: int = 300,
        retry_delay_seconds: int = 5,
    ) -> None:
        if not 0 < timeout_seconds < lease_seconds:
            raise ValueError("job timeout must be positive and shorter than lease")
        self.sessions = sessions
        self.handlers = handlers
        self.timeout_seconds = timeout_seconds
        self.lease_seconds = lease_seconds
        self.retry_delay_seconds = retry_delay_seconds

    async def claim(self, job_id: UUID) -> UUID | None:
        now = datetime.now(UTC)
        async with self.sessions.begin() as session:
            job = await session.scalar(
                select(JobModel)
                .where(JobModel.id == job_id, due(now))
                .with_for_update(skip_locked=True)
            )
            if job is None:
                return None
            if job.attempt_count >= job.max_attempts:
                job.status = JobStatus.FAILED
                job.failure_code = "attempts_exhausted"
                job.completed_at = now
                job.lease_until = None
                job.run_token = None
                return None
            token = uuid4()
            job.status = JobStatus.RUNNING
            job.attempt_count += 1
            job.started_at = now
            job.lease_until = now + timedelta(seconds=self.lease_seconds)
            job.run_token = token
            logger.info("job_claimed job_id=%s attempt=%s", job.id, job.attempt_count)
            return token

    async def execute(self, job_id: UUID) -> None:
        token = await self.claim(job_id)
        if token is not None:
            await self.execute_claim(job_id, token)

    async def execute_claim(self, job_id: UUID, token: UUID) -> None:
        try:
            async with self.sessions.begin() as session:
                # The row lock protects both domain writes and success. A recovery
                # scanner skips a live executor even if its lease expires.
                job = await session.scalar(
                    select(JobModel)
                    .where(
                        JobModel.id == job_id,
                        JobModel.status == JobStatus.RUNNING,
                        JobModel.run_token == token,
                    )
                    .with_for_update()
                )
                if job is None:
                    return  # stale delivery after a newer claim
                handler = self.handlers.get(job.job_type)
                if handler is None:
                    raise PermanentJobError("unsupported_job_type")
                async with asyncio.timeout(self.timeout_seconds):
                    await handler(session, job)
                job.status = JobStatus.SUCCEEDED
                job.completed_at = datetime.now(UTC)
                job.failure_code = None
                job.lease_until = None
                job.run_token = None
            logger.info("job_succeeded job_id=%s", job_id)
        except Exception as exc:
            # The context above has rolled back domain writes before failure is saved.
            retryable = isinstance(exc, (RetryableJobError, TimeoutError))
            code = (
                "timeout"
                if isinstance(exc, TimeoutError)
                else "transient"
                if retryable
                else "permanent"
                if isinstance(exc, PermanentJobError)
                else "unexpected"
            )
            async with self.sessions.begin() as session:
                job = await session.scalar(
                    select(JobModel)
                    .where(
                        JobModel.id == job_id,
                        JobModel.status == JobStatus.RUNNING,
                        JobModel.run_token == token,
                    )
                    .with_for_update()
                )
                if job is None:
                    return
                now = datetime.now(UTC)
                job.failure_code = code
                job.lease_until = None
                job.run_token = None
                if retryable and job.attempt_count < job.max_attempts:
                    job.status = JobStatus.QUEUED
                    delay = min(300, self.retry_delay_seconds * 2 ** (job.attempt_count - 1))
                    job.available_at = now + timedelta(seconds=delay)
                else:
                    job.status = JobStatus.FAILED
                    job.completed_at = now
                logger.warning(
                    "job_failure job_id=%s status=%s code=%s attempt=%s",
                    job.id,
                    job.status,
                    code,
                    job.attempt_count,
                )


async def dispatch_due(
    sessions: async_sessionmaker[AsyncSession],
    publish: Callable[[UUID], None],
    *,
    batch_size: int = 100,
) -> int:
    async with sessions() as session:
        ids = list(
            (
                await session.scalars(
                    select(JobModel.id)
                    .where(due(datetime.now(UTC)))
                    .order_by(JobModel.available_at, JobModel.id)
                    .limit(batch_size)
                )
            ).all()
        )
    sent = 0
    for job_id in ids:
        try:
            await asyncio.to_thread(publish, job_id)
            sent += 1
        except Exception:
            # Never remove database work when Redis is unavailable.
            logger.warning("job_publish_failed job_id=%s", job_id)
            break
    return sent
