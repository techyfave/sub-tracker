# Backend Contributor Runbook

This guide explains how to prepare a local development environment, run the API, validate changes, and contribute safely to the Sub-Tracker backend.

## 1. Backend overview

The backend uses FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Redis, and Celery.

The API includes:

- Health and readiness checks.
- User registration, login, token refresh, and current-user lookup.
- Consent listing, granting, and revocation.
- Subscription creation, listing, retrieval, updates, and deletion.
- Subscription transaction and usage-event endpoints.
- Structured error responses.

Issue #8 and its ingestion API work are recorded as merged. Check the current routes, schemas, and tests for the exact supported ingestion contract. Do not infer additional endpoints or provider integrations from the documentation alone.

### Consent endpoints

- `GET /api/v1/consents` — list the authenticated user's consents.
- `POST /api/v1/consents` — grant consent using an allowed scope and policy version.
- `DELETE /api/v1/consents/{consent_id}` — revoke a consent.

Consent operations require authentication. Invalid scopes or policy values are rejected by request validation. Revoking a consent owned by another user returns `403 Forbidden`; revoking a nonexistent consent returns `404 Not Found`. Repeated revocation preserves the original `revoked_at` timestamp and does not generate another revocation audit event.

Do not assume planned provider integrations or AI features are implemented unless the relevant code and tests confirm this.

## 2. Requirements

For local Python development, install:

- Python 3.12 or 3.13.
- Git.
- `uv`.
- A reachable PostgreSQL database.
- Redis when working with background jobs or running tests that require Redis.

The project declares Python `>=3.12,<3.14`. Check your versions:

```bash
python --version
uv --version
git --version
```

For Docker Compose, install and start Docker Desktop, then verify:

```bash
docker --version
docker compose version
```

## 3. Start the complete development stack

Docker Desktop with Docker Compose is required for this option.

Run the following commands from the repository root:

```bash
docker compose up --build -d
docker compose ps
```

Check API logs:

```bash
docker compose logs -f api
```

Useful local URLs:

- Liveness: <http://127.0.0.1:8000/api/v1/health/live>
- Readiness: <http://127.0.0.1:8000/api/v1/health/ready>
- Interactive API documentation: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

Confirm readiness before testing database-backed endpoints. A successful liveness response alone does not establish database readiness or worker health.

Stop the stack without removing stored data:

```bash
docker compose down
```

Avoid `docker compose down --volumes` unless you intentionally want to delete local database and Redis data.

## 4. Set up local Python development

From the repository root:

```bash
cd backend
uv sync --group dev
```

Configure environment variables for the services you intend to use.

### Bash example

These examples match the repository's local development defaults. Use them only for a local development environment and replace the credentials if your setup differs. The test database must be separate and disposable.

```bash
export DATABASE_URL="postgresql+asyncpg://sub_tracker:sub_tracker_local@localhost:5432/sub_tracker"
export REDIS_URL="redis://localhost:6379/0"
export JOB_QUEUE="sub-tracker.jobs"

export TEST_DATABASE_URL="postgresql+asyncpg://sub_tracker:sub_tracker_local@localhost:5432/sub_tracker_test"
export TEST_REDIS_URL="redis://localhost:6379/1"
```

### PowerShell example

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://sub_tracker:sub_tracker_local@localhost:5432/sub_tracker"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:JOB_QUEUE = "sub-tracker.jobs"

$env:TEST_DATABASE_URL = "postgresql+asyncpg://sub_tracker:sub_tracker_local@localhost:5432/sub_tracker_test"
$env:TEST_REDIS_URL = "redis://localhost:6379/1"
```

These environment variables apply only to the current terminal session. The database credentials match the repository's local Compose defaults; never use these development credentials in production.

Create the disposable test database from the repository root (both Bash and PowerShell):

```sh
docker compose exec postgres createdb -U sub_tracker sub_tracker_test
```

Expected: exit 0 with no output. If it already exists, reuse it only if it is disposable.
Return to `backend/`, set the test URLs above, and run `uv run pytest`.
The migration tests reset that test database; they must never target `sub_tracker`.

Create the `sub_tracker_test` database before running database-dependent integration tests. Confirm that the test configuration uses the intended test database and Redis instance before running tests that modify or recreate data.

### Host-local versus Compose configuration

- When running Python directly on your computer, use `localhost` for PostgreSQL and Redis services exposed on the host.
- When running the API inside Docker Compose, use the service hostnames `postgres` and `redis`. The Compose configuration supplies the appropriate database and Redis URLs to its containers.
- `TEST_DATABASE_URL` must point to a separate, disposable test database. Never point destructive tests at a database containing important data.
- `TEST_REDIS_URL` must point to the test Redis configuration required by the tests. The example uses Redis database `1`; verify that the tests and Redis setup support this isolation before relying on it.
- The application defaults `JOB_QUEUE` to `sub-tracker.jobs`. Use the queue name supported by the current configuration. Do not invent additional job modes or flags.

Apply database migrations from `backend/`:

```bash
uv run alembic upgrade head
```

Expected result: the command exits successfully, and Alembic applies outstanding migrations or reports that the database is already up to date.

Start the API:

```bash
uv run uvicorn app.main:app --reload
```

Keep the API running while checking the health endpoints. Database-backed requests also require the configured database to be reachable.

## 5. Database migrations

Alembic manages database schema changes.

Apply migrations:

```bash
uv run alembic upgrade head
```

Before changing the schema, inspect the existing models and migration history. Create and review a migration rather than assuming that editing a model updates an existing database.

Never run destructive migration or test commands against a database containing data you need.

## 6. Deterministic demo seed

After applying migrations, run the seed from `backend/`:

```bash
uv run python -m app.infrastructure.database.seed
```

With Docker Compose, run the seed in the API container from the repository root:

```bash
docker compose exec api uv run python -m app.infrastructure.database.seed
```

The seed documents six subscription-review scenarios:

1. Keep.
2. Downgrade.
3. Cancel.
4. Review.
5. Missing usage.
6. Conflicting evidence.

The seeded downgrade scenario includes **one estimated `SavingsRecord`** representing NGN 4,000 in estimated monthly savings. This is a projection based on the difference between current and proposed plan prices, not realized savings. Do not create or document a separate fabricated verified-savings record.

The seeded downgrade action is queued with zero attempts. Its estimated savings record is not proof that a provider-side change has completed. Savings must remain estimated until the action has completed and post-change billing evidence confirms the actual savings.

The fixtures use fixed IDs and timestamps and are intended to be idempotent. Seed accounts use placeholder password hashes and are not normal login accounts.

### Verify seed idempotency

Use a disposable PostgreSQL database with migrations already applied. From `backend/`, run the seed twice:

```bash
uv run python -m app.infrastructure.database.seed
uv run python -m app.infrastructure.database.seed
```

Record the output of both runs and compare the relevant table counts or logical fixture records. The second run should not create duplicate logical records. Confirm that all six scenarios remain present and that the downgrade still has exactly one estimated savings record.

Do not claim PostgreSQL seed repeatability has passed until both runs have actually completed and the results have been checked. A SQLite test alone does not establish PostgreSQL behavior.

Parent records must be flushed before dependent records are created so their identifiers are available and foreign-key relationships remain valid. This reflects the lesson from PR #34.

For the six scenarios and their expected behavior, see [Demo Seed Scenarios](../../doc/seed-scenarios.md).

For the seed data decisions, see [ADR-006: Seed Data Shape](../../doc/adr/006-seed-data-shape.md).

## 7. Tests and code quality

Run these commands from `backend/`:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

Some integration tests require a disposable PostgreSQL or Redis instance and test-specific environment variables, including `TEST_DATABASE_URL` or `TEST_REDIS_URL`.

Read the test configuration before running integration tests. Tests that recreate schemas must never target a database containing important data.

A test run that reports skipped tests has not verified those skipped scenarios. Record the skip reasons, configure the required services, and rerun the tests before claiming the full integration suite has passed.

## 8. API conventions and OpenAPI verification

- API routes use the `/api/v1` prefix.
- Protected endpoints require a valid bearer access token.
- Subscription resources are scoped to the authenticated user.
- Consent operations enforce authentication, accepted scopes and policy values, and ownership.
- Revoking another user's consent returns `403 Forbidden`.
- Revoking a nonexistent consent returns `404 Not Found`.
- Repeated consent revocation preserves the original timestamp and does not create another revocation audit event.
- Request validation and documented HTTP errors use structured `application/problem+json` responses where specified by the endpoint.
- Rate-limit responses may use a different content type; check the actual endpoint contract.
- Monetary values in JSON examples must follow the relevant schema, including decimal-string fields where required.
- Timezone-aware timestamps must include a timezone, such as `Z` for UTC.
- Unknown fields are rejected by subscription request schemas.
- Subscription deletion returns HTTP `204 No Content`, with no response body.

Inspect the generated contract at `/docs` and `/openapi.json`.

When changing endpoint behavior, verify both:

1. The generated OpenAPI response codes, examples, and schemas.
2. Representative actual HTTP success and error responses.

A schema audit is useful for checking the generated OpenAPI document, but it does not replace live HTTP testing.

Do not document status codes or response bodies that the endpoint does not actually return. Examples must match the implementation, including authentication failures, validation errors, resource ownership errors, missing resources, conflicts, and rate limits where applicable.

## 9. Background jobs

Read [Background Jobs](background-jobs.md) for Redis and Celery configuration, worker and scheduler startup, retries, recovery, and troubleshooting.

A running Redis service does not by itself prove that a worker is consuming jobs. Check worker and scheduler logs and the relevant job status. Follow the guide's documented harmless probe or status check.

### Stuck or failed jobs

Where available, inspect the persisted job `status` and `failure_code`, along with worker logs and timestamps.

Before retrying a job:

- Confirm the underlying cause has been corrected.
- Check whether the operation is safe to retry and whether it is idempotent.
- Check whether a provider-side action may already have succeeded despite a timeout.
- Follow the application's actual retry policy and documented recovery procedure.
- Do not manually mark a job successful or claim realized savings without evidence of completion.

Do not invent a retry command, job mode, or administrative API that the implementation does not support.

An API health response is not proof that background processing works. Record the actual probe result and worker output.

## 10. Troubleshooting

### The database is unavailable

Check the database URL, whether PostgreSQL is running, and whether the configured database exists. With Compose, inspect `docker compose ps` and the database and migration logs. Confirm whether the URL is intended for a host process or a container.

### Migrations fail

Confirm database connectivity and inspect the migration error before retrying. Do not delete database volumes as a routine troubleshooting step.

### Background jobs are not progressing

Check Redis connectivity, worker and scheduler logs, and the job's recorded `status` and `failure_code`, where available. Follow [Background Jobs](background-jobs.md) and check retry prerequisites before attempting recovery.

### Authentication fails

Registration creates the user but does not itself provide a login access token. Register a normal account, then send a login request to `POST /api/v1/auth/login`. Read `tokens.access_token` from the login response and send it as a bearer token to protected endpoints.

Seed fixtures are not normal login accounts. Never store passwords or live access tokens in the walkthrough or committed documentation.

### Consent requests fail

Check that the request is authenticated, that the requested scopes and policy version are accepted, and that the consent belongs to the authenticated user when revoking it. A foreign consent returns `403`; a nonexistent consent returns `404`. Repeated revocation is idempotent.

### A request returns an error

Check the HTTP status, structured error response, request schema, and examples in `/docs`. Compare the actual response with the corresponding operation in `/openapi.json`. If the documented example and actual response disagree, verify the route implementation and tests before changing the documentation.

## 11. Feature status and related documentation

- **Ingestion APIs:** Issue #8 is recorded as merged. Verify the supported endpoints and conventions against their implementation and tests.
- **Deterministic savings calculation:** Issue #9 / PR #43 is recorded as merged. Estimated savings must not be described as realized savings without confirming evidence.
- **Recommendation list/detail:** Issue #14 / PR #37 is merged. See [recommendation contracts](recommendations-api.md); list/detail support ownership, pagination, filters, versions, uncertainty, savings and evidence.
- **AI provider execution:** Remains planned until issue #11 is implemented and verified. Do not claim live AI execution or invent provider-execution flags.
- **Issues #13–#17:** Check the current issue tracker for the latest implementation and review status instead of inferring completion from this runbook.

See the [Documentation Index](../../doc/README.md) for architecture decisions, seed scenarios, implementation status, and related documentation.

See the [Fresh Contributor Walkthrough](../../doc/contributor-walkthrough.md) for recorded checks, results, and outstanding verification work.

## 12. Before opening a pull request

- Run relevant tests and record skipped integration tests.
- Run Ruff linting and formatting checks.
- Run mypy.
- Review migration and seed changes for safety and determinism.
- Verify seed idempotency against a disposable PostgreSQL database when making seed-related changes.
- Update API examples and documentation when endpoint behavior changes.
- Clearly identify features that are planned but not implemented.
- Review `git diff` and `git diff --check`.
- Never commit secrets, `.env` files, credentials, or real user data.
- Record environment limitations honestly in the contributor walkthrough.

Do not mark the pull request ready for review until its acceptance requirements and required integration evidence have been addressed.

## Implemented recommendation API

Issue #14 / PR #37 is merged: authenticated `GET /api/v1/recommendations` and `GET /api/v1/recommendations/{id}` return immutable snapshots. Use `page`, `page_size`, `status` (queued/running/completed/failed), `action` and `subscription_id` filters. Missing or foreign IDs return the same 404. Invalid filters/IDs return 422; missing authentication returns 401. Generated OpenAPI includes safe evidence, version, uncertainty and estimated-savings examples.


## Exact worker smoke check

From the repository root after the seed command, run:

```sh
docker compose exec api uv run python -m app.infrastructure.jobs.cli probe --user-id 10000000-0000-4000-8000-000000000001 --key contributor-smoke-v1
docker compose exec api uv run python -m app.infrastructure.jobs.cli status --user-id 10000000-0000-4000-8000-000000000001 --job-id JOB_ID_FROM_PROBE
```

Replace `JOB_ID_FROM_PROBE` with the UUID printed by the first command. Poll status until
`succeeded`; the scheduler scans every five seconds. Record actual job state and worker logs.
If queued persists, check matching queue/Redis settings and worker/scheduler logs.
This probe uses the seed user's fixed ID and performs no provider-side action.

## Features awaiting implementation

| Issue | Current contract | Documentation completion |
|---|---|---|
| #13 | Analysis creation/status PR #44 is under review | Add accepted 202, idempotency, state and failure examples after merge |
| #14 | Recommendation list/detail merged | Examples included in OpenAPI |
| #15 | Decision endpoints pending | Add request, conflict and ownership examples when implemented |
| #16 | Action execution pending | Add queued/running/terminal and retry examples when implemented |
| #17 | Savings APIs pending | Add estimated/verified and evidence examples when implemented |
| #11 | Provider pipeline pending | No production fake/provider CLI mode exists on main |

For the current deterministic development mode, run the seed and tests; those are fixtures,
not live AI execution. Do not set undocumented provider flags. Use
`uv run pytest tests/integration/recommendations tests/unit/analysis -q` for deterministic
recommendation/calculation checks. Provider outage/retry troubleshooting will follow the
accepted #11/#13 configuration rather than a guessed credential or URL.

See `doc/issue-20-handoff.md` from the repository root for remaining human verification.


## Register, log in and read a protected resource

With the API listening on port 8000, PowerShell can capture the token automatically:

```powershell
$body = @{ email = 'contributor@example.com'; password = 'LocalExamplePass123!' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/register -ContentType application/json -Body $body
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/login -ContentType application/json -Body $body
$headers = @{ Authorization = "Bearer $($login.tokens.access_token)" }
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/me -Headers $headers
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/v1/recommendations -Headers $headers
```

Expected: registration 201 with user data, login 200 with `tokens`, protected GETs 200.
A new user's recommendation list is empty; demo recommendations belong to the seeded
users, whose placeholder hashes cannot be used to log in. Registration repeated with the
same email returns 409; use the existing account's login or a different local email.
These are synthetic local credentials, not an invitation to commit personal credentials.

Bash equivalent (run from `backend/` so `uv run python` is available):

```bash
body='{"email":"contributor@example.com","password":"LocalExamplePass123!"}'
curl -i -H 'Content-Type: application/json' -d "$body" http://127.0.0.1:8000/api/v1/auth/register
token=$(curl -fsS -H 'Content-Type: application/json' -d "$body" http://127.0.0.1:8000/api/v1/auth/login | uv run python -c 'import json,sys; print(json.load(sys.stdin)["tokens"]["access_token"])')
curl -i -H "Authorization: Bearer $token" http://127.0.0.1:8000/api/v1/me
curl -i -H "Authorization: Bearer $token" http://127.0.0.1:8000/api/v1/recommendations
```

Inspect the ingestion request examples in `/docs`: measured zero has `quantity: "0"`
and `is_unknown: false`; unknown usage has `quantity: null` and `is_unknown: true`.
Do not combine a quantity with unknown usage. The usage idempotency key is optional;
when supplied, replay it with the same owner/source/subscription/time/quantity/unknown
values. Incompatible reuse returns 409. Transaction references similarly cannot be
reassigned to another subscription; a same-subscription replay updates the recorded charge.
Both ingestion endpoints return 201 with `status` and `message`, not a created resource ID.
