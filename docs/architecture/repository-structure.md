# Proposed Repository Structure

The current repository includes only the documentation and minimal shared-backend subset. Remaining directories are created when their phase begins.

```text
sub-tracker/
|-- README.md
|-- compose.yaml
|-- .env.example
|-- docs/
|   |-- learning/
|   |-- product/
|   |-- architecture/
|   `-- platform/
|-- prototypes/                 # added during Phase 0
|   |-- shared/
|   `-- participant-01..07/
|-- backend/
|   |-- pyproject.toml
|   |-- uv.lock
|   |-- alembic.ini
|   |-- Dockerfile
|   |-- alembic/
|   |-- app/
|   |   |-- api/v1/endpoints/
|   |   |-- core/
|   |   |-- domain/
|   |   |-- application/
|   |   |-- infrastructure/
|   |   |-- agents/
|   |   `-- workers/
|   `-- tests/
|-- evaluations/                # added after convergence
|-- frontend/                   # added with shared vertical slice
|-- infrastructure/
`-- .github/workflows/
```

## Backend boundary rules

- `domain` contains no FastAPI, SQLAlchemy, Redis, or provider code.
- `application` coordinates use cases through abstractions.
- `infrastructure` implements persistence and providers.
- `api` translates HTTP into application calls.
- `agents` owns prompts, tools, schemas, validators, and policies.
- evaluation data remains independently runnable.
- database entities do not leak into HTTP responses.
- provider payloads do not define the domain model.

## Creation order

1. Documentation and minimal FastAPI platform foundation.
2. Phase 0 shared prototype specification and participant folders.
3. Seven independent prototypes.
4. Convergence artifacts and ADRs.
5. Shared product domain and application modules.
6. Evaluation package and thin frontend.
7. Provider adapters and deployment infrastructure.
