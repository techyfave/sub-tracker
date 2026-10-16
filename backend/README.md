# Subscription Optimization API

FastAPI backend for the Sub-Tracker subscription optimization project.

The current API includes health checks, account registration and authentication, and subscription management. Check the relevant guides before assuming a planned integration or AI feature is implemented.

## Quick start

### Requirements

- Python 3.12 or 3.13 for local development
- Docker with Docker Compose for the complete local stack
- Git
- uv for local Python development

### Run the complete stack

From the repository root:

```bash
docker compose up --build -d
docker compose ps
```

The stack includes PostgreSQL, Redis, database migrations, the API, a Celery worker, and a scheduler.

- Liveness: http://127.0.0.1:8000/api/v1/health/live
- Readiness: http://127.0.0.1:8000/api/v1/health/ready
- Interactive API docs: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

View logs:

```bash
docker compose logs -f api worker scheduler
```

Stop containers without deleting stored data:

```bash
docker compose stop
```

Remove containers and the network:

```bash
docker compose down
```

Do not use `docker compose down --volumes` unless you intentionally want to delete local database and Redis data. Compose uses development credentials; never reuse them in production.

## Local Python development

The project requires Python >=3.12 and <3.14. Use Python 3.12 or 3.13.

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

These commands run from `backend/`. See [Background jobs](docs/background-jobs.md) for worker and scheduler instructions.

## Tests and code quality

Run from `backend/`:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

Some integration tests require disposable PostgreSQL or Redis services and environment variables such as `TEST_DATABASE_URL` or `TEST_REDIS_URL`. Read the relevant test setup before running tests that reset a database schema. Never use a database containing data you need.

## Demo seed data

After applying migrations, run from `backend/`:

```bash
uv run python -m app.infrastructure.database.seed
```

With Docker Compose, run inside the API container:

```bash
docker compose exec api uv run python -m app.infrastructure.database.seed
```

The deterministic seed creates six scenarios: keep, downgrade, cancel, review, missing usage, and conflicting evidence. It uses fixed IDs and timestamps and is designed to be idempotent. Seed users have placeholder password hashes and cannot log in normally.

## API and contributor guides

- [Subscription API guide](docs/subscriptions-api.md): request fields, validation, lifecycle rules, and deletion semantics.
- [Background jobs runbook](docs/background-jobs.md): Redis, worker and scheduler setup, job status, retries, recovery, and troubleshooting.
- Interactive API reference: `/docs` when the API is running.
- OpenAPI schema: `/openapi.json` when the API is running.

## Troubleshooting

- **Database unavailable:** check `docker compose ps` and `docker compose logs postgres migrate api`.
- **Jobs are not running:** check `docker compose logs redis worker scheduler`. Healthy Redis does not guarantee a worker is consuming jobs.
- **Port conflict:** configure `API_PORT`, `POSTGRES_PORT`, or `REDIS_PORT` before starting Compose.
- **Invalid request:** inspect the HTTP status and problem response, then compare the request with `/docs` and the API guide.
- **Seeded account cannot log in:** seed users are fixtures, not normal accounts. Register a normal account for authentication tests.
- **AI or provider behavior:** confirm the relevant feature and handler are implemented before expecting real provider calls. Do not describe a simulation as a live integration.

## Security

Default settings and credentials are for local development only. Use environment-specific secrets and credentials for shared or deployed environments. Do not commit `.env` files, tokens, passwords, or real user data.
