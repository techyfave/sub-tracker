
# Subscription Optimization API

FastAPI backend for the Sub-Tracker subscription optimization project.

The backend provides health checks, account authentication, subscription management, consent management, and background-job infrastructure. Consult the endpoint implementations and generated OpenAPI document before assuming a planned provider integration or AI feature is available.

## Quick start

### Requirements

- Python 3.12 or 3.13 for local Python development
- Git
- `uv`
- Docker Desktop with Docker Compose for the complete development stack
- PostgreSQL
- Redis when working with background jobs

The project declares Python `>=3.12,<3.14`.

### Run the complete stack

From the repository root:

```bash
docker compose up --build -d
docker compose ps
```

Inspect the service logs:

```bash
docker compose logs --tail=100 api postgres migrate redis worker scheduler
```

The configured Compose stack includes PostgreSQL, Redis, migrations, the API, and background-job services. Confirm actual service names and health status with `docker compose ps`.

When the API is published on port 8000, these local URLs are available:

- Liveness: http://127.0.0.1:8000/api/v1/health/live
- Readiness: http://127.0.0.1:8000/api/v1/health/ready
- Interactive API documentation: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

Stop containers without deleting stored data:

```bash
docker compose stop
```

Remove containers and the Compose network:

```bash
docker compose down
```

Do not use `docker compose down --volumes` unless you intentionally want to delete the associated local database and Redis volumes. Compose credentials are for development only.

## Local Python development

From the repository root:

```bash
cd backend
uv sync --group dev
```

Set `DATABASE_URL` to a reachable PostgreSQL database. Set `REDIS_URL` when working with background jobs.

Apply migrations:

```bash
uv run alembic upgrade head
```

Start the API:

```bash
uv run uvicorn app.main:app --reload
```

Run these `uv` commands from `backend/`.

For host-local development, use database and Redis hostnames and ports reachable from your computer. Inside Docker Compose, use the configured service hostnames and internal ports. A container's `localhost` refers to that container, not another service.

See the [Backend Contributor Runbook](docs/contributor-runbook.md) for environment-variable examples, test setup, authentication instructions, and validation procedures.

## Implemented API inventory

All API routes use the `/api/v1` prefix.

### Health

- `GET /api/v1/health/live` — liveness check
- `GET /api/v1/health/ready` — readiness check

These health endpoints do not require authentication.

### Authentication

- `POST /api/v1/auth/register` — register an account
- `POST /api/v1/auth/login` — log in and obtain tokens
- `POST /api/v1/auth/refresh` — refresh an access token
- `GET /api/v1/me` — retrieve the authenticated user's details

Registration returns user details, not tokens. Log in and use `tokens.access_token` from the login response for protected requests.

### Subscriptions

The API supports subscription creation, listing, retrieval, updates, and deletion. Related operations include subscription transactions and usage events.

Consult `/docs`, `/openapi.json`, and the [Subscription API Guide](docs/subscriptions-api.md) for the exact routes, schemas, pagination, lifecycle rules, and response codes.

Subscription deletion returns `204 No Content` with no response body.

### Consents

- `GET /api/v1/consents` — list the authenticated user's consents
- `POST /api/v1/consents` — grant consent
- `DELETE /api/v1/consents/{consent_id}` — revoke consent

Consent operations require authentication. Consent records are scoped to the authenticated user. Repeated revocation of an existing consent is idempotent and preserves the original revocation timestamp.

Consult the generated OpenAPI schema and endpoint tests for the exact request fields and error responses.

## Tests and code quality

Run from `backend/`:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

Some integration tests require disposable PostgreSQL or Redis services and test-specific variables such as `TEST_DATABASE_URL` and `TEST_REDIS_URL`.

Read the contributor runbook and relevant test configuration before running tests that recreate schemas or reset data. Never use a database containing information you need.

## Demo seed data

After applying migrations, run from `backend/`:

```bash
uv run python -m app.infrastructure.database.seed
```

With Docker Compose, run the seed in the API container:

```bash
docker compose exec api uv run python -m app.infrastructure.database.seed
```

The deterministic demo seed covers six scenarios:

1. Keep
2. Downgrade
3. Cancel
4. Review
5. Missing usage
6. Conflicting evidence

The fixtures use fixed IDs and timestamps and are intended to be idempotent. Seed accounts use placeholder password hashes and are not normal login accounts.

The downgrade scenario documents NGN 4,000 in estimated monthly savings and NGN 48,000 in estimated annual savings. These are projections, not verified realized savings. Verification requires a completed action and confirming post-change billing evidence.

See:

- [Demo Seed Scenarios](../doc/seed-scenarios.md)
- [ADR-006: Seed Data Shape](../doc/adr/006-seed-data-shape.md)

## Guides

- [Backend Contributor Runbook](docs/contributor-runbook.md) — setup, environment variables, testing, authentication, and contributor workflow.
- [Subscription API Guide](docs/subscriptions-api.md) — request fields, validation, lifecycle rules, and deletion semantics.
- [Background Jobs Runbook](docs/background-jobs.md) — Redis and Celery configuration, worker and scheduler startup, job status, retries, recovery, and troubleshooting.
- Interactive API reference: `/docs` when the API is running.
- OpenAPI schema: `/openapi.json` when the API is running.

## Troubleshooting

- **Database unavailable:** check the effective `DATABASE_URL`, `docker compose ps`, and PostgreSQL, migration, and API logs.
- **Jobs are not progressing:** check `REDIS_URL`, worker and scheduler logs, persisted job status, and `failure_code` where available. Redis being healthy does not prove a worker is consuming jobs.
- **Port conflict:** inspect the Compose configuration and its supported port variables before changing port settings.
- **Invalid request:** inspect the HTTP status and problem response, then compare the request with `/docs` and the relevant API guide.
- **Authentication fails:** registration returns user details. Log in and use `tokens.access_token`. Seed users are fixtures, not normal accounts.
- **AI or provider behavior:** verify that the relevant implementation exists before expecting real provider calls. Do not describe a simulation as a live integration.

## Security

Default settings, credentials, and seed data are for local development only. Use environment-specific secrets and credentials for shared or deployed environments. Do not commit `.env` files, tokens, passwords, or real user data.


## Implemented recommendation API

Issue #14 / PR #37 is merged: authenticated `GET /api/v1/recommendations` and `GET /api/v1/recommendations/{id}` return immutable snapshots. Use `page`, `page_size`, `status` (queued/running/completed/failed), `action` and `subscription_id` filters. Missing or foreign IDs return the same 404. Invalid filters/IDs return 422; missing authentication returns 401. Generated OpenAPI includes safe evidence, version, uncertainty and estimated-savings examples.
