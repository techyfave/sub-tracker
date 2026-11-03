# Subscription Tracker Backend Documentation

This index is the canonical entry point for backend architecture decisions, implementation status, and terminology. Start here, then follow the [Backend Contributor Runbook](../backend/docs/contributor-runbook.md) to set up the project, run the API, and execute the checks.

## Architecture

The MVP backend is a **modular monolith**: one deployable application with explicit domain/application/infrastructure boundaries. External integrations are replaceable adapters behind ports/interfaces. Vendor SDKs, broker clients, authentication implementations, and provider-specific models must not leak into domain logic.

## Contributor resources

- [Backend Contributor Runbook](../backend/docs/contributor-runbook.md) — environment setup, migrations, seed data, testing, and troubleshooting.
- [Fresh Contributor Walkthrough](contributor-walkthrough.md) — environment verification, completed checks, and outstanding integration blockers.
- [Background Jobs](../backend/docs/background-jobs.md) — worker behavior and troubleshooting.
- [Demo Seed Scenarios](seed-scenarios.md) — documented development seed scenarios and their limitations.

## Feature and implementation status

The statuses below distinguish documented or implemented API functionality from integrations and workflows that still require verification. Check the linked guides and current issue tracker before treating planned work as complete.

| Area | Current status | Guidance |
|---|---|---|
| Authentication | Implemented API functionality | Registration, login, token refresh, and authenticated access have documented API contracts. See the [Backend Contributor Runbook](../backend/docs/contributor-runbook.md). |
| Consent management | Implemented API functionality | Granting, listing, and revoking consent are supported. Revocation checks ownership, returns `403 Forbidden` for another user's consent, returns `404 Not Found` for a nonexistent consent, and preserves the original revocation timestamp on repeated requests. |
| Subscription management | Implemented API endpoints | Consult the endpoint schemas, examples, and tests. Do not assume that every external provider integration is complete. |
| Subscription optimization | Partially implemented | Use the [Demo Seed Scenarios](seed-scenarios.md) to understand the documented recommendation and action scenarios. A queued or attempted action is not proof of a completed provider-side change. |
| Deterministic savings calculation | Implemented work is tracked in the project history | Issue #8 and the deterministic calculation work associated with issue #9 / PR #43 are recorded as merged. Savings estimates must not be described as realized savings without confirming evidence. |
| AI provider execution | Planned; not confirmed complete | The provider-neutral boundary is documented in [ADR-003](adr/003-ai-provider-boundary.md). Live AI execution must not be claimed complete until issue #11 is implemented and verified. |
| Background jobs | Documented worker architecture; full execution not verified in the current walkthrough | The design uses Celery and Redis. Follow the [Background Jobs guide](../backend/docs/background-jobs.md), and verify worker execution separately from API availability. |
| Local integration environment | Partially verified | The [Fresh Contributor Walkthrough](contributor-walkthrough.md) records completed quality checks and outstanding Docker, PostgreSQL, Redis, and full-stack verification. |

### Roadmap and issue tracking

- **Issue #8 and issue #9 / PR #43:** recorded as merged in the project history.
- **Issue #14:** PR #37 is merged; authenticated recommendation list/detail contracts are implemented.
- **Issue #11:** AI provider execution remains planned until implementation and verification are complete.
- **Issues #13–#17:** consult the current issue tracker for their latest implementation and review status rather than inferring completion from documentation alone.

### Troubleshooting quick links

- **Environment setup, migrations, API usage, and tests:** [Backend Contributor Runbook](../backend/docs/contributor-runbook.md)
- **Worker startup, retries, and job processing:** [Background Jobs](../backend/docs/background-jobs.md)
- **Seed records and expected scenarios:** [Demo Seed Scenarios](seed-scenarios.md)
- **Seed-data design and savings evidence:** [ADR-006 — Seed Data Shape](adr/006-seed-data-shape.md)
- **Completed checks and outstanding blockers:** [Fresh Contributor Walkthrough](contributor-walkthrough.md)

Treat implementation status as evidence-based. Distinguish merged functionality from work in progress, estimated savings from verified outcomes, and documented architecture from integrations that have actually been tested.

## ADRs

| ADR | Decision |
|---|---|
| [001 Authentication Approach](adr/001-authentication-approach.md) | JWT bearer authentication behind an authentication port |
| [002 Background Job Library](adr/002-background-job-library.md) | Celery with Redis behind a job/queue port |
| [003 AI Provider Boundary](adr/003-ai-provider-boundary.md) | Groq is the MVP baseline behind a provider-neutral `AIProviderPort` |
| [004 AI Prompt and Response Retention](adr/004-ai-prompt-response-retention.md) | Raw AI prompts/responses retained for 30 days, then deleted |
| [005 Demo Currency](adr/005-demo-currency.md) | NGN is the canonical demo/seed currency |
| [006 Seed Data Shape](adr/006-seed-data-shape.md) | Deterministic, minimal, relationally valid, idempotent development-only seed |
| [007 Application-Managed Credentials and Refresh-Token Rotation](adr/007-application-managed-credentials-and-refresh-rotation.md) | Argon2id passwords, hashed opaque single-use refresh credentials with atomic rotation and replay revocation; refines ADR-001 |

## Domain terminology

See [TERMINOLOGY.md](TERMINOLOGY.md) for the canonical API/domain vocabulary, exact spellings, states, and value meanings.

## Implementation rule

When an implementation decision conflicts with an ADR, the ADR must be updated before implementation proceeds. These ADRs are the source of truth for the MVP backend contracts. Documentation must accurately reflect the implementation and its verification status.

## Implemented recommendation API

Issue #14 / PR #37 is merged: authenticated `GET /api/v1/recommendations` and `GET /api/v1/recommendations/{id}` return immutable snapshots. Use `page`, `page_size`, `status` (queued/running/completed/failed), `action` and `subscription_id` filters. Missing or foreign IDs return the same 404. Invalid filters/IDs return 422; missing authentication returns 401. Generated OpenAPI includes safe evidence, version, uncertainty and estimated-savings examples.
