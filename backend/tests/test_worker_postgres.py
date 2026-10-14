"""Real PostgreSQL locks/transactions: SQLite cannot prove these guarantees."""

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.application.jobs import (
    IdempotencyConflict,
    JobRequest,
    JobStatus,
    PermanentJobError,
    RetryableJobError,
)
from app.infrastructure.database.models.job import JobModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.jobs import PostgresJobRepository
from app.infrastructure.jobs.runner import JobRunner, dispatch_due


@pytest.fixture(scope="module")
def job_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL required for worker PostgreSQL tests")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": url},
        check=True,
        capture_output=True,
    )
    return url


@pytest.fixture
async def jobs(
    job_database_url: str,
) -> AsyncIterator[tuple[async_sessionmaker[AsyncSession], UUID]]:
    engine = create_async_engine(job_database_url, pool_size=12)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    user_id = uuid4()
    async with sessions.begin() as session:
        session.add(
            UserModel(id=user_id, email=f"{user_id}@example.test", hashed_password="not-a-login")
        )
    try:
        yield sessions, user_id
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(UserModel).where(UserModel.id == user_id))
        await engine.dispose()


async def enqueue(
    sessions: async_sessionmaker[AsyncSession],
    user: UUID,
    *,
    max_attempts: int = 3,
) -> UUID:
    async with sessions.begin() as session:
        return await PostgresJobRepository(session).enqueue(
            JobRequest(user, "test.effect", str(uuid4()), {}, max_attempts)
        )


async def state(sessions: async_sessionmaker[AsyncSession], job_id: UUID) -> JobModel:
    async with sessions() as session:
        job = await session.get(JobModel, job_id)
        assert job is not None
        return job


async def effect(session: AsyncSession, job: JobModel) -> None:
    user = await session.get(UserModel, job.user_id)
    assert user is not None
    user.email += ".done"
    await session.flush()


async def expire(sessions: async_sessionmaker[AsyncSession], job_id: UUID) -> None:
    async with sessions.begin() as session:
        await session.execute(
            update(JobModel)
            .where(JobModel.id == job_id)
            .values(
                lease_until=datetime.now(UTC) - timedelta(seconds=1),
                available_at=datetime.now(UTC) - timedelta(seconds=1),
            )
        )


async def test_enqueue_is_atomic_owner_scoped_and_conflict_checked(jobs):
    sessions, user = jobs
    request = JobRequest(user, "test.effect", "one-key", {"analysis_id": "123"})

    async def submit():
        async with sessions.begin() as session:
            return await PostgresJobRepository(session).enqueue(request)

    ids = await asyncio.gather(*(submit() for _ in range(8)))
    assert len(set(ids)) == 1
    with pytest.raises(IdempotencyConflict):
        async with sessions.begin() as session:
            await PostgresJobRepository(session).enqueue(
                JobRequest(user, "test.effect", "one-key", {"analysis_id": "456"})
            )
    with pytest.raises(RuntimeError):
        async with sessions.begin() as session:
            rolled_back = await PostgresJobRepository(session).enqueue(
                JobRequest(user, "test.effect", "rolled-back", {})
            )
            raise RuntimeError("request fails before commit")
    async with sessions() as session:
        assert await session.get(JobModel, rolled_back) is None
        assert await PostgresJobRepository(session).get(ids[0], uuid4()) is None


async def test_concurrent_and_repeated_delivery_commits_one_domain_result(jobs):
    sessions, user = jobs
    job_id = await enqueue(sessions, user)
    runner = JobRunner(sessions, {"test.effect": effect})
    await asyncio.gather(*(runner.execute(job_id) for _ in range(8)))
    await runner.execute(job_id)
    job = await state(sessions, job_id)
    assert job.status == JobStatus.SUCCEEDED and job.attempt_count == 1
    async with sessions() as session:
        account = await session.get(UserModel, user)
        assert account.email == f"{user}@example.test.done"


async def test_failure_rolls_back_domain_write_and_bounded_retry(jobs):
    sessions, user = jobs
    job_id = await enqueue(sessions, user, max_attempts=2)

    async def transient(session, job):
        await effect(session, job)
        raise RetryableJobError("secret-must-not-be-persisted")

    runner = JobRunner(sessions, {"test.effect": transient}, retry_delay_seconds=5)
    await runner.execute(job_id)
    job = await state(sessions, job_id)
    assert job.status == JobStatus.QUEUED and job.failure_code == "transient"
    assert job.available_at > datetime.now(UTC)
    await runner.execute(job_id)
    assert (await state(sessions, job_id)).attempt_count == 1
    await expire(sessions, job_id)
    await runner.execute(job_id)
    job = await state(sessions, job_id)
    assert job.status == JobStatus.FAILED and job.attempt_count == 2
    async with sessions() as session:
        assert (await session.get(UserModel, user)).email == f"{user}@example.test"
    await runner.execute(job_id)
    assert (await state(sessions, job_id)).attempt_count == 2


@pytest.mark.parametrize(
    "error,code",
    [
        (PermanentJobError("private detail"), "permanent"),
        (ValueError("private detail"), "unexpected"),
    ],
)
async def test_permanent_and_unexpected_fail_without_automatic_retry(jobs, error, code, caplog):
    sessions, user = jobs
    job_id = await enqueue(sessions, user)

    async def fail(session, job):
        raise error

    await JobRunner(sessions, {"test.effect": fail}).execute(job_id)
    job = await state(sessions, job_id)
    assert job.status == JobStatus.FAILED and job.failure_code == code
    assert job.attempt_count == 1
    assert "private detail" not in caplog.text


async def test_expired_claim_is_recovered_and_stale_executor_is_fenced(jobs):
    sessions, user = jobs
    job_id = await enqueue(sessions, user)
    runner = JobRunner(sessions, {"test.effect": effect})
    stale_token = await runner.claim(job_id)  # worker dies after committed claim
    await expire(sessions, job_id)
    fresh_token = await runner.claim(job_id)
    assert stale_token and fresh_token and stale_token != fresh_token
    await runner.execute_claim(job_id, stale_token)
    assert (await state(sessions, job_id)).status == JobStatus.RUNNING
    await runner.execute_claim(job_id, fresh_token)
    job = await state(sessions, job_id)
    assert job.status == JobStatus.SUCCEEDED and job.attempt_count == 2


async def test_live_executor_lock_prevents_recovery_even_with_expired_lease(jobs):
    sessions, user = jobs
    job_id = await enqueue(sessions, user)
    entered, finish = asyncio.Event(), asyncio.Event()

    async def slow(session, job):
        entered.set()
        await finish.wait()
        await effect(session, job)

    runner = JobRunner(sessions, {"test.effect": slow})
    token = await runner.claim(job_id)
    await expire(sessions, job_id)
    task = asyncio.create_task(runner.execute_claim(job_id, token))
    try:
        await asyncio.wait_for(entered.wait(), 5)
        assert await runner.claim(job_id) is None
    finally:
        finish.set()
        await task
    assert (await state(sessions, job_id)).attempt_count == 1


async def test_worker_death_rolls_back_partial_result_then_recovers(jobs):
    sessions, user = jobs
    job_id = await enqueue(sessions, user)
    entered = asyncio.Event()

    async def interrupted(session, job):
        await effect(session, job)
        entered.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(JobRunner(sessions, {"test.effect": interrupted}).execute(job_id))
    await asyncio.wait_for(entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await expire(sessions, job_id)
    await JobRunner(sessions, {"test.effect": effect}).execute(job_id)
    async with sessions() as session:
        assert (await session.get(UserModel, user)).email == f"{user}@example.test.done"
    assert (await state(sessions, job_id)).attempt_count == 2


async def test_timeout_and_crash_exhaustion_are_terminal_and_recoverable(jobs):
    sessions, user = jobs
    job_id = await enqueue(sessions, user, max_attempts=1)

    async def slow(session, job):
        await asyncio.sleep(1)

    await JobRunner(sessions, {"test.effect": slow}, timeout_seconds=0.01).execute(job_id)
    assert (await state(sessions, job_id)).failure_code == "timeout"
    async with sessions.begin() as session:
        repo = PostgresJobRepository(session)
        assert not await repo.retry_failed(job_id, uuid4())
        assert await repo.retry_failed(job_id, user)
    assert (await state(sessions, job_id)).retry_count == 1
    runner = JobRunner(sessions, {"test.effect": effect})
    assert await runner.claim(job_id)
    await expire(sessions, job_id)
    assert await runner.claim(job_id) is None
    assert (await state(sessions, job_id)).failure_code == "attempts_exhausted"
    async with sessions.begin() as session:
        assert await PostgresJobRepository(session).retry_failed(job_id, user)
    await runner.execute(job_id)
    job = await state(sessions, job_id)
    assert job.status == JobStatus.SUCCEEDED and job.retry_count == 2
    async with sessions.begin() as session:
        assert not await PostgresJobRepository(session).retry_failed(job_id, user)


async def test_redis_failure_does_not_lose_committed_work(jobs):
    sessions, user = jobs
    job_id = await enqueue(sessions, user)

    def unavailable(job_id):
        raise ConnectionError("broker down")

    assert await dispatch_due(sessions, unavailable) == 0
    assert (await state(sessions, job_id)).status == JobStatus.QUEUED
    sent = []
    await dispatch_due(sessions, sent.append)
    assert job_id in sent
    await JobRunner(sessions, {"test.effect": effect}).execute(job_id)
    sent.clear()
    await dispatch_due(sessions, sent.append)
    assert job_id not in sent
