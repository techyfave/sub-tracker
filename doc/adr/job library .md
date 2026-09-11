## Context

The subscription tracker performs work that should not block HTTP requests, including AI analysis and potentially provider synchronization. The MVP needs a reliable background-job mechanism while preserving the modular-monolith boundary.

The job system is infrastructure. Domain and application code must not depend directly on Celery or Redis APIs.

## Options considered

1. **Synchronous execution**
   - Minimal infrastructure.
   - Blocks API requests and is unsuitable for longer AI/provider operations.

2. **Celery + Redis**
   - Mature Python task-processing ecosystem.
   - Redis provides a straightforward broker/result infrastructure.
   - Supports retries, task routing, and operational visibility.

3. **RQ + Redis**
   - Simple Python API and lower conceptual overhead.
   - Smaller feature set and less suitable if job orchestration grows.

## Decision

The MVP uses **Celery with Redis**.

The application exposes a provider-neutral job boundary such as:

```text
JobPort.enqueue(job_type, payload) -> JobId
```

Celery task definitions live in the infrastructure/application integration layer. Redis is an infrastructure dependency.

The domain layer must not import Celery task objects, Redis clients, broker message types, or task decorators.

The canonical Job lifecycle is defined in `TERMINOLOGY.md`:

`queued -> running -> succeeded | failed | cancelled`

## Consequences

### Positive

- Long-running AI/provider work can run asynchronously.
- Celery supports retries and operational controls needed by the MVP.
- Redis is simple to run locally and in deployment.
- The job mechanism can be replaced behind `JobPort`.
- Preserves the modular-monolith architecture.

### Negative

- Adds Redis and worker processes to the development/deployment setup.
- Requires task idempotency and retry-safe operations.
- Operational monitoring is needed for failed/stuck jobs.
- Celery-specific configuration remains infrastructure complexity.

## Implementation boundary

```text
Application service
  -> JobPort
      -> Celery adapter
          -> Redis broker
              -> Worker
```

Changing Celery/Redis later must not require changes to domain entities or business rules.
