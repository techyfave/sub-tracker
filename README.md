# AI-Native Subscription Optimization Agent

This repository supports a seven-person learning project that will eventually become a production-structured subscription optimization agent.

## Start here: solo prototypes

The team must **not begin by dividing the shared application into frontend, backend, and AI tasks**. Every participant first builds the same small AI prototype independently.

Read these documents in order:

1. [Solo prototype guide](docs/learning/solo-prototype.md)
2. [Prototype comparison and convergence](docs/learning/comparison-and-convergence.md)
3. [Product vision and scope](docs/product/vision-and-scope.md)
4. [Delivery roadmap](docs/roadmap.md)

The solo task is:

> Given a subscription, recent charges, known usage, preferences, and available alternatives, return a validated recommendation to keep, downgrade, cancel, or review it, including evidence, uncertainty, and deterministic savings.

The goal is not merely to get a model response. Every participant must learn structured outputs, tool use, deterministic business logic, failure handling, grounding, and evaluation.

### Beginner-friendly tour

If the repository feels unfamiliar, begin with one of these guides:

- Interactive FAQ: `tour/` (searchable questions, file map, and solo-build route)
- Printable guide: [SubTracker Beginner Field Guide](output/pdf/subtracker-beginner-field-guide.pdf)

To run the interactive tour locally:

```bash
cd tour
pnpm install
pnpm run dev
```

## Shared-system foundation

The repository also contains a minimal foundation for the shared system that the team will build **after** prototype comparison:

- Python 3.12 and FastAPI;
- dependencies and commands managed with `uv`;
- Pydantic settings;
- SQLAlchemy 2 with async PostgreSQL;
- Alembic migration wiring;
- Docker and Docker Compose;
- liveness and readiness endpoints;
- pytest, Ruff, and mypy configuration.

This scaffold intentionally contains no subscription features or AI agent implementation yet.

## Documentation map

- [Documentation index](docs/README.md)
- [Product vision and scope](docs/product/vision-and-scope.md)
- [Solo prototype guide](docs/learning/solo-prototype.md)
- [Comparison and convergence](docs/learning/comparison-and-convergence.md)
- [System architecture](docs/architecture/system-architecture.md)
- [AI system design](docs/architecture/ai-system.md)
- [Data and API plan](docs/architecture/data-and-api.md)
- [Repository structure](docs/architecture/repository-structure.md)
- [Docker and local development](docs/platform/docker-and-development.md)
- [Quality, security, and operations](docs/platform/quality-security-operations.md)
- [Roadmap](docs/roadmap.md)
- [Open decisions](docs/open-decisions.md)

## Shared backend quick start

The shared backend lives in `backend/`.

```bash
cd backend
uv sync --group dev
uv run uvicorn app.main:app --reload
```

Or start the containerized environment from the repository root:

```bash
docker compose up --build
```

Then open:

- API documentation: `http://localhost:8000/docs`
- Liveness: `http://localhost:8000/api/v1/health/live`
- Readiness: `http://localhost:8000/api/v1/health/ready`

Copy `.env.example` to `.env` before changing local defaults. Do not commit real secrets.

## Current stage

The current repository provides planning documentation and a shared-system foundation only. The next team activity is Phase 0: approve the solo prototype specification, shared cases, and comparison rubric.
