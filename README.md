# AI-Native Subscription Optimization Agent

This repository supports a seven-person learning project that is evolving toward a production-structured subscription optimization agent.

## Start here: project and backend guides

Start with the documentation index to understand the current project, then follow the backend setup guide to run and test the API.

Read these documents in order:

1. [Backend documentation index](doc/README.md)
2. [Backend contributor runbook](backend/docs/contributor-runbook.md)
3. [Background jobs](backend/docs/background-jobs.md)
4. [Seed scenarios](doc/seed-scenarios.md)

The project is evolving toward a subscription optimization agent. The intended system will use subscription details, recent charges, known usage, preferences, and available alternatives to recommend whether to keep, downgrade, cancel, or review a subscription.

The shared backend foundation is available, but AI-provider execution and unverified roadmap features must not be treated as complete.

### Beginner-friendly resources

If you are new to the repository, start with the [Backend documentation index](doc/README.md) and follow the [Backend contributor runbook](backend/docs/contributor-runbook.md) to set up the environment and run the API.

For background-job behavior and troubleshooting, see the [Background Jobs guide](backend/docs/background-jobs.md).

## Shared-system foundation

The repository includes a shared backend foundation with API endpoints for authentication, user identity, consent management, health checks, and subscription management. The backend also contains supporting infrastructure and documentation for development, testing, database migrations, and background jobs.

The current foundation includes:

- Python and FastAPI.
- Dependency management with `uv`.
- Pydantic request and response schemas.
- SQLAlchemy and database migration wiring.
- Authentication and user-owned resource access.
- Consent grant, listing, and revocation.
- Subscription creation, listing, detail, update, and deletion.
- Transaction and usage-event endpoints.
- Liveness and readiness endpoints.
- Pytest, Ruff, and mypy configuration.
- Background-job infrastructure and development documentation.

**Implementation status:** These API and infrastructure foundations do not mean the complete subscription optimization agent is finished. AI-provider execution, end-to-end provider integrations, and other roadmap features must be treated as planned until implemented and verified.

## Documentation map

### Product and learning

The original solo-prototype learning guides and roadmap referenced by earlier versions of this README are not present in this checkout. Do not rely on those paths until the documents are restored.

- [Backend documentation index](doc/README.md)
- [Domain terminology](doc/TERMINOLOGY.md)
- [Product and delivery planning](doc/README.md)
- [Seed scenarios](doc/seed-scenarios.md)
- [Idempotency contract](doc/idempotency-contract.md)
- [ADR-006: Seed data shape](doc/adr/006-seed-data-shape.md)
- [ADR-007: Credential management and refresh-token rotation](doc/adr/007-application-managed-credentials-and-refresh-rotation.md)

### Backend and contribution

- [Backend contributor runbook](backend/docs/contributor-runbook.md) — setup, environment variables, migrations, seed data, authentication, tests, and troubleshooting.
- [Background jobs](backend/docs/background-jobs.md) — job processing, worker operation, and failure investigation.
- [Subscriptions API](backend/docs/subscriptions-api.md) — subscription endpoint behavior and API conventions.
- [Seed scenarios](doc/seed-scenarios.md) — deterministic demonstration scenarios and expected outcomes.
- [ADR-006: Seed data shape](doc/adr/006-seed-data-shape.md) — seed-data relationships, constraints, and savings semantics.
- [Idempotency contract](doc/idempotency-contract.md) — idempotent behavior and expectations.
- [Fresh contributor walkthrough](doc/contributor-walkthrough.md) — recorded environment checks, completed steps, and outstanding verification.

## API inventory

The API uses the `/api/v1` prefix. The registered routes are listed below; consult the linked backend documentation for request schemas, response formats, authorization requirements, and error examples.

| Area | Method and path | Purpose |
|---|---|---|
| Health | `GET /api/v1/health/live` | Liveness probe |
| Health | `GET /api/v1/health/ready` | Readiness probe |
| Authentication | `POST /api/v1/auth/register` | Register a user |
| Authentication | `POST /api/v1/auth/login` | Authenticate and obtain tokens |
| Authentication | `POST /api/v1/auth/refresh` | Refresh authentication tokens |
| User | `GET /api/v1/me` | Get the authenticated user's identity |
| Consents | `GET /api/v1/consents` | List the authenticated user's consents |
| Consents | `POST /api/v1/consents` | Grant consent for validated scopes and policy version |
| Consents | `DELETE /api/v1/consents/{consent_id}` | Revoke a consent |
| Subscriptions | `POST /api/v1/subscriptions` | Create a subscription |
| Subscriptions | `GET /api/v1/subscriptions` | List subscriptions |
| Subscriptions | `GET /api/v1/subscriptions/{id}` | Retrieve a subscription |
| Subscriptions | `PATCH /api/v1/subscriptions/{id}` | Update a subscription |
| Subscriptions | `DELETE /api/v1/subscriptions/{id}` | Delete a subscription |
| Transactions | `POST /api/v1/subscriptions/{id}/transactions` | Record a transaction for a subscription |
| Usage events | `POST /api/v1/subscriptions/usage-events` | Record a usage event |

### API behavior notes

- Protected routes require the appropriate authentication.
- Consent requests validate policy versions and scopes. Invalid values produce request-validation errors.
- A user cannot revoke another user's consent. Repeated revocation preserves the original revocation timestamp.
- Subscription endpoints enforce resource ownership and the documented lifecycle rules.
- The readiness endpoint can return an unavailable response when its required dependencies are not ready.
- Use the actual response schemas and operation-level examples in the generated OpenAPI document rather than assuming all endpoints share the same response format.
- The API inventory reflects the routes registered by the current application. It is not a claim that every planned integration or agent feature is implemented.

## Shared backend quick start

The backend lives in `backend/`. For a reproducible setup, follow the [Backend Contributor Runbook](backend/docs/contributor-runbook.md) first. It documents environment variables, host-local versus containerized service URLs, database setup, migrations, seed data, authentication, and testing.

From the repository root, a containerized environment can be started with:

```bash
docker compose up --build
```

This command requires Docker and Docker Compose to be installed and working. It has not been verified as successful in every contributor environment.

For a host-local backend setup, follow the runbook's environment configuration before starting the server. Do not assume that launching Uvicorn alone creates a configured database, Redis service, or background worker.

When the environment is configured, the API documentation is available at:

- OpenAPI UI: `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`
- Liveness: `http://localhost:8000/api/v1/health/live`
- Readiness: `http://localhost:8000/api/v1/health/ready`

Copy `.env.example` to `.env` when using the documented environment-file workflow. Never commit real credentials, tokens, or production secrets.

## Testing and verification

The backend quality checks include:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

Database- and Redis-dependent integration tests require the corresponding test-service configuration. A passing local test run with skipped integration tests is **not** evidence that PostgreSQL, Redis, migrations, seed repeatability, or worker operation has passed end-to-end verification.

The current contributor walkthrough records the checks performed and the outstanding environment-dependent work. Update it with actual commands, versions, expected and observed results, corrections, and blockers when further verification is completed. Do not mark an untested step as passed.

## Current stage

The project is developing the shared-system foundation alongside the team's learning and prototype-comparison process. Continue to follow the [delivery roadmap](docs/roadmap.md), the [backend contributor runbook](backend/docs/contributor-runbook.md), and the documented decisions.

The shared backend must remain reproducible, testable, and explicit about its limitations. Keep unimplemented AI-provider behavior and unverified infrastructure checks clearly distinguished from completed functionality.
