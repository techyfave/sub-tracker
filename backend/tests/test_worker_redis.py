"""Optional real Celery/Redis delivery test; all services must be disposable."""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.jobs import JobRequest, JobStatus
from app.infrastructure.database.models.job import JobModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.jobs import PostgresJobRepository


def test_celery_dispatch_duplicate_delivery_and_restart(tmp_path: Path) -> None:
    url = os.getenv("TEST_DATABASE_URL")
    redis_url = os.getenv("TEST_REDIS_URL")
    if not url or not redis_url:
        pytest.skip("TEST_DATABASE_URL and TEST_REDIS_URL required for real broker test")
    from celery import Celery

    queue = "worker-test-" + uuid4().hex
    user_id = uuid4()
    environment = {**os.environ, "DATABASE_URL": url, "REDIS_URL": redis_url, "JOB_QUEUE": queue}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        env=environment,
        capture_output=True,
    )
    publisher = Celery("smoke", broker=redis_url)
    publisher.conf.update(
        task_default_queue=queue,
        task_serializer="json",
        accept_content=["json"],
        task_ignore_result=True,
    )

    async def setup():
        engine = create_async_engine(url)
        try:
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            async with sessions.begin() as session:
                session.add(
                    UserModel(
                        id=user_id, email=f"{user_id}@example.test", hashed_password="not-a-login"
                    )
                )
                await session.flush()
                return await PostgresJobRepository(session).enqueue(
                    JobRequest(user_id, "system.probe", "first", {})
                )
        finally:
            await engine.dispose()

    async def read(job_id):
        engine = create_async_engine(url)
        try:
            async with async_sessionmaker(engine)() as session:
                job = await session.get(JobModel, job_id)
                return job.status, job.attempt_count
        finally:
            await engine.dispose()

    async def abandoned():
        engine = create_async_engine(url)
        try:
            sessions = async_sessionmaker(engine, expire_on_commit=False)
            async with sessions.begin() as session:
                job_id = await PostgresJobRepository(session).enqueue(
                    JobRequest(user_id, "system.probe", "restart", {})
                )
                # A prior process committed its claim, then disappeared.
                from datetime import UTC, datetime, timedelta

                await session.execute(
                    update(JobModel)
                    .where(JobModel.id == job_id)
                    .values(
                        status=JobStatus.RUNNING,
                        attempt_count=1,
                        run_token=uuid4(),
                        lease_until=datetime.now(UTC) - timedelta(seconds=1),
                    )
                )
                return job_id
        finally:
            await engine.dispose()

    def await_success(job_id):
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            value = asyncio.run(read(job_id))
            if value[0] == JobStatus.SUCCEEDED:
                return value[1]
            time.sleep(0.25)
        pytest.fail("Celery job did not finish; inspect worker/beat logs in " + str(tmp_path))

    log = (tmp_path / "worker.log").open("w")
    beat_log = (tmp_path / "beat.log").open("w")
    processes = []

    def worker():
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "celery",
                "-A",
                "app.infrastructure.jobs.celery_app:celery_app",
                "worker",
                "--pool=solo",
                "--loglevel=INFO",
                "--without-gossip",
                "--without-mingle",
                "--without-heartbeat",
                "-Q",
                queue,
            ],
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        processes.append(process)
        return process

    def stop(process):
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

    try:
        first_id = asyncio.run(setup())
        publisher.send_task("jobs.execute", args=[str(first_id)], queue=queue)
        publisher.send_task("jobs.execute", args=[str(first_id)], queue=queue)
        first_worker = worker()
        assert await_success(first_id) == 1
        stop(first_worker)
        recovered_id = asyncio.run(abandoned())
        worker()
        beat = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "celery",
                "-A",
                "app.infrastructure.jobs.celery_app:celery_app",
                "beat",
                "--loglevel=INFO",
                "--schedule=" + str(tmp_path / "schedule"),
            ],
            env=environment,
            stdout=beat_log,
            stderr=subprocess.STDOUT,
        )
        processes.append(beat)
        # Actual beat -> Redis dispatcher -> PostgreSQL scan -> Redis worker delivery.
        assert await_success(recovered_id) == 2
        publisher.send_task("jobs.execute", args=[str(first_id)], queue=queue)
        time.sleep(1)
        assert asyncio.run(read(first_id)) == (JobStatus.SUCCEEDED, 1)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                stop(process)
        publisher.control.purge()
        publisher.close()
        log.close()
        beat_log.close()

        async def cleanup():
            engine = create_async_engine(url)
            try:
                async with async_sessionmaker(engine).begin() as session:
                    await session.execute(delete(UserModel).where(UserModel.id == user_id))
            finally:
                await engine.dispose()

        asyncio.run(cleanup())
