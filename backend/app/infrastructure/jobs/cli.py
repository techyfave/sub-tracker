"""Operator tooling, not a public authorization bypass or HTTP endpoint."""

import argparse
import asyncio
import json
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.jobs import JobRequest
from app.core.config import get_settings
from app.infrastructure.database.repositories.jobs import PostgresJobRepository


async def run(command: str, user_id: UUID, job_id: UUID | None, key: str) -> None:
    engine = create_async_engine(get_settings().database_url)
    try:
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions.begin() as session:
            repository = PostgresJobRepository(session)
            if command == "probe":
                created = await repository.enqueue(JobRequest(user_id, "system.probe", key, {}))
                print(json.dumps({"job_id": str(created)}))
            elif job_id is None:
                raise ValueError("--job-id is required")
            elif command == "retry":
                print(json.dumps({"retried": await repository.retry_failed(job_id, user_id)}))
            else:
                job = await repository.get(job_id, user_id)
                if job is None:
                    raise ValueError("Job not found for this owner")
                print(
                    json.dumps(
                        {
                            "job_id": str(job.id),
                            "status": job.status,
                            "attempt_count": job.attempt_count,
                            "max_attempts": job.max_attempts,
                            "retry_count": job.retry_count,
                            "failure_code": job.failure_code,
                        }
                    )
                )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["probe", "status", "retry"])
    parser.add_argument("--user-id", type=UUID, required=True)
    parser.add_argument("--job-id", type=UUID)
    parser.add_argument("--key", default="worker-smoke-v1")
    args = parser.parse_args()
    asyncio.run(run(args.command, args.user_id, args.job_id, args.key))


if __name__ == "__main__":
    main()
