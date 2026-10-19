from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.jobs import IdempotencyConflict, JobRequest, JobStatus
from app.infrastructure.database.models.job import JobModel
from app.infrastructure.jobs.runner import sync_analysis


class PostgresJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue(self, request: JobRequest) -> UUID:
        # ON CONFLICT serializes concurrent enqueue attempts on the same key.
        await self.session.execute(
            insert(JobModel)
            .values(
                id=uuid4(),
                user_id=request.user_id,
                job_type=request.job_type,
                idempotency_key=request.idempotency_key,
                payload=request.payload,
                status=JobStatus.QUEUED,
                attempt_count=0,
                max_attempts=request.max_attempts,
                retry_count=0,
                available_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=["user_id", "job_type", "idempotency_key"])
        )
        job = (
            await self.session.scalars(
                select(JobModel).where(
                    JobModel.user_id == request.user_id,
                    JobModel.job_type == request.job_type,
                    JobModel.idempotency_key == request.idempotency_key,
                )
            )
        ).one()
        if job.payload != request.payload or job.max_attempts != request.max_attempts:
            raise IdempotencyConflict("Job key already used with different inputs")
        return job.id

    async def get(self, job_id: UUID, user_id: UUID) -> JobModel | None:
        result = await self.session.scalars(
            select(JobModel).where(JobModel.id == job_id, JobModel.user_id == user_id)
        )
        return result.one_or_none()

    async def retry_failed(self, job_id: UUID, user_id: UUID) -> bool:
        job = await self.session.scalar(
            select(JobModel)
            .where(JobModel.id == job_id, JobModel.user_id == user_id)
            .with_for_update()
        )
        if job is None or job.status != JobStatus.FAILED:
            return False
        job.status = JobStatus.QUEUED
        job.attempt_count = 0
        job.retry_count += 1
        job.available_at = datetime.now(UTC)
        job.completed_at = None
        job.lease_until = None
        job.run_token = None
        # Retain failure_code until the next attempt succeeds for operator diagnosis.
        await sync_analysis(self.session, job)
        return True
