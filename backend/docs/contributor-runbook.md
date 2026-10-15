# Backend Contributor Runbook



This guide explains how to prepare a local development environment, run the API, validate changes, and contribute safely to the Sub-Tracker backend.



## 1. Backend overview



The backend uses FastAPI, Pydantic, SQLAlchemy, Alembic, and PostgreSQL. Redis and Celery support background jobs.



The API currently includes:



- Health and readiness checks

- User registration, login, token refresh, and current-user lookup

- Subscription creation, listing, retrieval, updates, and deletion

- Structured error responses



Do not assume planned provider integrations or AI features are implemented unless the relevant code confirms this.



## 2. Requirements



For local Python development:



- Python 3.12 or 3.13

- Git

- `uv`

- A reachable PostgreSQL database

- Redis when working with background jobs



The project declares Python `>=3.12,<3.14`. Check your Python version before installing dependencies:



```bash

python --version

uv --version

```



## 3. Start the complete development stack



Docker Desktop with Docker Compose is required for this option.



From the repository root:



```bash

docker compose up --build -d

docker compose ps

```



Check the API logs:



```bash

docker compose logs -f api

```



Useful local URLs:



- Liveness: http://127.0.0.1:8000/api/v1/health/live

- Readiness: http://127.0.0.1:8000/api/v1/health/ready

- Interactive API documentation: http://127.0.0.1:8000/docs

- OpenAPI JSON: http://127.0.0.1:8000/openapi.json



Stop the stack without removing stored data:



```bash

docker compose down

```



Avoid `docker compose down --volumes` unless you intentionally want to delete the local database and Redis data.



## 4. Set up local Python development



From the repository root:



```bash

cd backend

uv sync --group dev

```



Configure `DATABASE_URL` to point to a reachable PostgreSQL database. Configure `REDIS_URL` when running background jobs.



Apply database migrations:



```bash

uv run alembic upgrade head

```



Start the API:



```bash

uv run uvicorn app.main:app --reload

```



Run these commands from the `backend/` directory. The API requires its configured database to be available for database-backed operations.



## 5. Database migrations



Alembic manages database schema changes.



Apply migrations:



```bash

uv run alembic upgrade head

```



Before changing the database schema, inspect the existing models and migration history. Create and review a migration rather than assuming that editing a model updates an existing database.



Never run destructive migration or test commands against a database containing data you need.



## 6. Deterministic demo seed



After the database migrations have been applied, run from `backend/`:



```bash

uv run python -m app.infrastructure.database.seed

```



With Docker Compose, the seed can be run in the API container:



```bash

docker compose exec api uv run python -m app.infrastructure.database.seed

```



The seed contains six subscription-review scenarios: keep, downgrade, cancel, review, missing usage, and conflicting evidence.



The fixtures use fixed IDs and timestamps and are intended to be idempotent. Seed accounts use placeholder password hashes and are not normal login accounts.



When changing seed scenarios, preserve deterministic behavior and verify that running the seed twice does not create duplicate records.



## 7. Tests and code quality



Run these commands from `backend/`:



```bash

uv run pytest

uv run ruff check .

uv run ruff format --check .

uv run mypy app

```



Some integration tests require a disposable PostgreSQL or Redis instance and test-specific environment variables, such as `TEST_DATABASE_URL` or `TEST_REDIS_URL`.



Read the relevant test configuration before running integration tests. Tests that recreate schemas must never target a database containing important data.



## 8. API conventions



- API routes use the `/api/v1` prefix.

- Protected endpoints require a valid bearer access token.

- Subscription resources are scoped to the authenticated user.

- Request validation errors use structured `application/problem+json` responses.

- Subscription amounts use decimal values; send monetary amounts as strings in JSON examples.

- Timestamps that require timezone awareness should include a timezone, such as `Z`.

- Unknown fields are rejected by subscription request schemas.

- Subscription deletion returns HTTP `204 No Content`, with no response body.



Use `/docs` and `/openapi.json` to inspect the running API's generated schema.



## 9. Background jobs



Read [Background Jobs](background-jobs.md) for Redis and Celery configuration, worker and scheduler startup, retries, recovery, and troubleshooting.



A running Redis service does not by itself prove that a worker is consuming jobs. Check worker logs and the relevant job status.



## 10. Troubleshooting



**The database is unavailable**



Check the database URL, whether PostgreSQL is running, and whether the configured database exists. With Docker Compose, inspect `docker compose ps` and the database and migration logs.



**Migrations fail**



Confirm the database is reachable and inspect the migration error before retrying. Do not delete database volumes as a routine troubleshooting step.



**Background jobs are not progressing**



Check Redis connectivity, worker and scheduler logs, and the job's recorded status. Follow the background-jobs guide.



**Authentication fails**



Register a normal account and use the returned access token as a bearer token. Seed fixtures are not normal login accounts.



**A request returns an error**



Check the HTTP status, structured error response, request schema, and examples in `/docs`.



## 11. Before opening a pull request



- Run relevant tests.

- Run Ruff linting and formatting checks.

- Run mypy.

- Review migration and seed changes for safety and determinism.

- Update API examples and documentation when endpoint behavior changes.

- Clearly identify features that are planned but not implemented.

- Review `git diff` and `git diff --check`.

- Never commit secrets, `.env` files, credentials, or real user data.
