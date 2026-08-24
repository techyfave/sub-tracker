# Quality, Security, and Operations

## Test layers

- unit tests for domain rules, tools, and state transitions;
- PostgreSQL integration tests for mappings and transactions;
- API tests for validation, ownership, and contracts;
- worker tests for retries and idempotency;
- provider contract tests;
- end-to-end critical flows;
- security and migration tests;
- versioned AI evaluation cases.

PostgreSQL-specific behavior must be tested against PostgreSQL rather than silently replaced with SQLite.

## CI quality gates

- Ruff formatting and linting;
- mypy type checks;
- unit and integration tests;
- migration consistency;
- schema compatibility;
- dependency and container scans;
- secret detection;
- targeted AI evaluation smoke tests;
- full evaluation before model or prompt promotion.

## Security baseline

- secure authentication and resource-level authorization;
- explicit consent scopes and revocation;
- encryption in transit and at rest;
- secrets outside source control;
- data minimization and deletion workflows;
- rate limits on authentication and AI endpoints;
- append-only audit events;
- idempotency for analysis and actions;
- imported text treated as untrusted data;
- model tools allow-listed and schema-constrained;
- no raw credentials sent to the model.

## Observability

Structured logs include correlation, analysis, job, prompt, schema, and provider references without unnecessarily recording sensitive content.

Metrics cover:

- API latency and errors;
- job and action state;
- model latency, retry rate, and cost;
- structured-output failures;
- recommendation and decision distributions;
- evaluation scores by version;
- PostgreSQL and Redis health.

Traces should connect an HTTP request through job execution, model/tool calls, validation, persistence, and approved action.

## Required runbooks before production

- AI-provider outage and rollback;
- queue backlog;
- failed migration;
- compromised provider connection;
- accidental sensitive logging;
- repeated action failure;
- backup restoration;
- prompt/model rollback.
