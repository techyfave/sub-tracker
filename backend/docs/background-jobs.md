# Durable background jobs (issue #12)

The accepted queue is Celery with Redis (ADR-002). PostgreSQL owns job state;
Redis carries only job IDs. The API, worker and scheduler use the same backend
image. Start one scheduler per deployment.

## Start locally

From the repository root:

```sh
docker compose up --build -d
docker compose ps
docker compose logs -f worker scheduler
```

Compose waits for PostgreSQL, applies migrations, and starts the API, Redis,
Celery worker and Celery beat scheduler. Local ports default to 5432, 6379 and
8000. Set POSTGRES_PORT, REDIS_PORT or API_PORT to avoid conflicts. These ports
are exposed on loopback only. This file uses development credentials; provide
deployment-specific credentials/settings for other environments.

To run processes separately from backend/, set DATABASE_URL, REDIS_URL and
optionally JOB_QUEUE, then run:

```sh
uv sync --frozen
uv run alembic upgrade head
uv run celery -A app.infrastructure.jobs.celery_app:celery_app worker --loglevel=INFO --concurrency=2
uv run celery -A app.infrastructure.jobs.celery_app:celery_app beat --loglevel=INFO
```

The supported deployment worker uses Linux prefork. Use the Docker setup on
Windows; native Windows solo mode is only suitable for development smoke tests.

## Smoke check and operator recovery

Register an account through the existing API, or load development seeds with
`docker compose exec api uv run python -m app.infrastructure.database.seed`.
The seed user ID below is fixed and has no usable login password.

```sh
docker compose exec api uv run python -m app.infrastructure.jobs.cli probe --user-id 10000000-0000-4000-8000-000000000001 --key smoke-v1
docker compose exec api uv run python -m app.infrastructure.jobs.cli status --user-id 10000000-0000-4000-8000-000000000001 --job-id JOB_ID
docker compose exec api uv run python -m app.infrastructure.jobs.cli retry --user-id 10000000-0000-4000-8000-000000000001 --job-id JOB_ID
```

Replace JOB_ID with the returned UUID. The harmless system.probe verifies
dispatch and completion. Status reads are scoped by owner. Retry is available
only for failed jobs, preserves the job ID/key, resets the bounded attempt
budget, and increments retry_count. This is trusted operator tooling, not a
public API. An operator must correct a permanent failure before retrying it.

## Enqueue from an application use case

The application-facing JobPort lives in app/application/jobs.py. Its PostgreSQL
adapter is PostgresJobRepository. Pass the existing request transaction:

```python
job_id = await PostgresJobRepository(session).enqueue(
    JobRequest(
        user_id=current_user.id,
        job_type="analysis",
        idempotency_key=request_key,
        payload={"analysis_id": str(analysis.id)},
    )
)
# The caller commits the analysis and job in the SAME transaction.
```

enqueue never commits or publishes. Rollback removes both the domain request
and the job. Keys are scoped to owner and job type. Repeating identical inputs
returns the same ID; conflicting payloads or attempt budgets raise
IdempotencyConflict, which the integrating endpoint should translate to 409.
Payloads should contain bounded resource IDs, not secrets, imported text or
provider responses. PostgreSQL is the only payload store; broker messages
contain the UUID only.

The analysis/action use cases are implemented by issues #13 and #16.
They register handlers in infrastructure/jobs/celery_app.py. Unregistered job
types fail visibly rather than claiming to have executed domain work.

## Delivery, retries and restart guarantees

- Beat requests a database scan every five seconds. Due queued jobs and expired
  running claims are republished. Publishing failure leaves rows intact for the
  next scan. Broker outages and a crash between commit and publish cannot lose work.
- A worker claims one eligible job under SELECT FOR UPDATE SKIP LOCKED. It
  persists running, increments attempt_count and creates a 300-second lease
  plus an unpredictable run token. Duplicate delivery cannot claim live work.
- Execution locks that job again and checks its token. Database domain writes
  and succeeded commit in one transaction. A stale executor cannot overwrite
  a newer claim. Recovery skips a still-locked live executor.
- Handlers have a 240-second cooperative timeout; Linux Celery soft/hard limits
  are 260/280 seconds. The Redis visibility timeout is 3600 seconds. Hard worker
  loss leaves a claim for database recovery after the lease, independently of
  Redis redelivery. Celery acknowledges late and rejects work on worker loss.
- RetryableJobError and timeout are temporary failures. Domain writes roll back,
  then the job becomes queued with exponential delays of 5, 10, 20... seconds,
  capped at 300 seconds. max_attempts includes the initial attempt and defaults
  to three (allowed range 1-10).
- PermanentJobError and unexpected exceptions fail immediately. Repeated worker
  crashes exhaust the same attempt budget. Failed jobs retain a safe
  failure_code and completed_at for inspection and explicit operator retry.
- Logs contain job ID, attempt, state and safe failure classification. Exception
  messages and payloads are deliberately excluded.

A handler receives the runner-owned AsyncSession and JobModel. It may flush
but MUST NOT commit, roll back or open an independent domain-write transaction.
It must finish within the execution bound and propagate cancellation. Avoid
holding unrelated locks in inconsistent order across handlers.

This guarantees one committed database result per successful job despite
duplicate delivery and restart. It does not make external side effects exactly
once. Future provider adapters must use a stable job ID as their own idempotency
key and implement reconciliation; perform expensive external work before the
short final database write where appropriate. For the MVP, actions are simulations.

## Verification

```sh
# Use an empty, disposable PostgreSQL database: migration tests reset its schema.
TEST_DATABASE_URL=postgresql+asyncpg://... uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

test_worker_postgres.py tests concurrent enqueue/delivery, atomic rollback,
bounded retries, owner-scoped recovery, stale-worker fencing, cancellation during
domain writes and broker publish failure using real PostgreSQL connections.
test_worker_redis.py optionally starts actual Celery worker/beat subprocesses;
set TEST_REDIS_URL to a disposable Redis instance as well as TEST_DATABASE_URL.
It uses a unique queue and checks actual dispatch, duplicate delivery and restart.

## Troubleshooting

Jobs staying queued: check scheduler and worker logs, database connectivity,
REDIS_URL and matching JOB_QUEUE. Redis being healthy alone does not mean the
worker is consuming. A persistent broker outage preserves queued rows.

Jobs staying running after a crash: wait for the 300-second lease and next scan.
If PostgreSQL still sees a live transaction holding the job lock, recovery skips
it until the worker disconnects or the time limit kills it. Do not manually
clear a lease on a live job.

Failed jobs: inspect failure_code via the CLI. Fix the handler/provider/input
problem, then retry only the failed job. Unsupported job types require their
handler to be registered. No automatic retry occurs for permanent/unexpected errors.

During shutdown use docker compose stop; restart with docker compose up -d.
Deleting Redis data cannot delete PostgreSQL job state. Do not remove PostgreSQL
volumes when testing worker restarts.

