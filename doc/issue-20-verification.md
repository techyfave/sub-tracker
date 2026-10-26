# Issue #20 agent verification — 2026-10-26

This is an agent-run check of PR #40 after merging current main (a5c2aa2).
It is not the independent human acceptance walkthrough. The earlier author attempt in
contributor-walkthrough.md remains unchanged as historical evidence.

## Database and seed

A disposable PostgreSQL 18 cluster on loopback port 55439 was initialized using initdb,
started with pg_ctl, and given a database named issue20. No existing developer database
was reset. From backend/ with DATABASE_URL pointing to that disposable database:

```sh
uv run alembic upgrade head
uv run python -m app.infrastructure.database.seed
uv run python -m app.infrastructure.database.seed
```

Upgrade reached c24000000001. First seed: `Demo seed data loaded successfully.` Second:
`Demo seed data already exists. Nothing to do.` A SQL count after each run returned
6 subscriptions, 6 recommendations and 1 savings record. The existing PostgreSQL
migration/seed tests additionally verify the broader table inventory and repeatability.

## Actual API handlers against PostgreSQL

HTTPX ASGITransport invoked the real application with a second disposable database,
issue20_smoke. It did not override the database session or authentication dependency.
The same migrations and seed command prepared that database. A synthetic example.com
account registered with 201 and logged in with 200. The login token was used in memory
and is not recorded here.

| Request | Observed |
|---|---|
| GET /api/v1/me with token | 200 |
| GET /api/v1/consents with token | 200 |
| GET /api/v1/recommendations with token | 200, empty own list |
| GET /api/v1/recommendations without token | 401 |
| GET /api/v1/subscriptions?page_size=0 with token | 422 |
| GET /api/v1/recommendations?status=succeeded with token | 422 |
| GET another owner's recommendation ID with token | 404 |
| GET /api/v1/health/ready | 200 |

The first smoke attempt used a reserved .test email and correctly received validation 422;
the successful check used example.com. Documentation examples likewise use example.com.
ASGITransport exercises application HTTP handlers, not a real network listener or Compose.

## Direct worker probe

Enqueued system.probe for the fixed seeded owner through PostgresJobRepository, committed,
and executed through JobRunner with the registered probe handler. Persisted state became
`succeeded`. This verifies the direct handler/transaction path. It does not establish
Redis delivery, Celery Beat dispatch, or a Docker deployment.

## Remaining independent checks

The human must complete the fresh-clone/Compose/Redis walkthrough described in
[the handoff](issue-20-handoff.md). Do not convert these agent checks into a fabricated
human sign-off. Future endpoint examples remain pending the merged contracts for
#13/#15/#16/#17 and #11 provider modes.
