import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID

from celery import Celery  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.application.analyses.worker import run_analysis
from app.core.config import get_settings
from app.infrastructure.database.models.job import JobModel
from app.infrastructure.jobs.runner import Handler, JobRunner, dispatch_due

settings = get_settings()
celery_app = Celery("sub_tracker", broker=settings.redis_url)
celery_app.conf.update(
    task_default_queue=settings.job_queue,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 3600,
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
    },
    task_soft_time_limit=260,
    task_time_limit=280,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "dispatch-durable-jobs": {
            "task": "jobs.dispatch",
            "schedule": 5.0,
        }
    },
)


async def probe(session: AsyncSession, job: JobModel) -> None:
    """Operational smoke task; no domain action or analysis is simulated."""
    return None


# Issue #13 and #16 register their real transactional handlers here.
HANDLERS: dict[str, Handler] = {"system.probe": probe, "analysis.run": run_analysis}


async def with_sessions(
    operation: Callable[[async_sessionmaker[AsyncSession]], Awaitable[None]],
) -> None:
    # Each Celery delivery runs its own event loop. Never share pooled asyncpg
    # connections between loops or across prefork children.
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        await operation(async_sessionmaker(engine, expire_on_commit=False))
    finally:
        await engine.dispose()


def execute_job(job_id: str) -> None:
    async def run(sessions: async_sessionmaker[AsyncSession]) -> None:
        await JobRunner(sessions, HANDLERS).execute(UUID(job_id))

    asyncio.run(with_sessions(run))


def publish(job_id: UUID) -> None:
    celery_app.send_task("jobs.execute", args=[str(job_id)], retry=False)


def dispatch_jobs() -> None:
    async def run(sessions: async_sessionmaker[AsyncSession]) -> None:
        await dispatch_due(sessions, publish)

    asyncio.run(with_sessions(run))


celery_app.task(name="jobs.execute")(execute_job)
celery_app.task(name="jobs.dispatch")(dispatch_jobs)
