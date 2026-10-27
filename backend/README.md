# Shared FastAPI Backend

This is the minimal foundation for the shared application that begins after solo prototype comparison. It does not yet contain subscription or AI-agent features.

## Setup with uv

```bash
uv sync --group dev
uv run uvicorn app.main:app --reload
```

## Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

## Database migrations

Set `DATABASE_URL` for a reachable PostgreSQL instance, then run:

```bash
uv run alembic upgrade head
```
## Demo seed data

After applying the database migrations, load the deterministic demo data with:

uv run python -m app.infrastructure.database.seed

The seed creates the six Issue #4 scenarios: keep, downgrade, cancel, review, missing usage, and conflicting evidence.

The seed is idempotent. Running it again after a successful seed does not create duplicate demo records.

## Background worker

See [background-jobs.md](docs/background-jobs.md) for Celery/Redis setup, durable job integration, retries, recovery and verification.

## Asynchronous analysis

See [analyses-api.md](docs/analyses-api.md) for creation, polling, idempotency and AI gateway configuration.
