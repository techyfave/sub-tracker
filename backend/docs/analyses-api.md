# Asynchronous analyses

`POST /api/v1/analyses` requires bearer authentication, an `Idempotency-Key`
header (1–255 characters, containing a non-whitespace character), and a body:

```json
{"subscription_id": "40000000-0000-4000-8000-000000000001"}
```

Returns **202** with `id`, `subscription_id`, `status`, `attempt_count`,
`failure_code`, `started_at`, and `completed_at`; `Location` points to
`GET /api/v1/analyses/{id}`. Public states are queued, running, completed, failed.
The GET endpoint exposes only the caller's records. Missing and foreign records
both return 404. Repeating a user-scoped key returns the original analysis and
never adds a job. Reusing it for another subscription returns 409. Missing stored
billing/usage evidence or an active prompt returns 422. Missing usage alone is
allowed when billing evidence exists; it is represented as unknown, never zero.

## Worker and AI gateway

Run the Celery worker and Beat dispatcher as documented in `background-jobs.md`.
Creation writes the analysis and durable job in a single database transaction.
Beat publishes committed jobs, so Redis downtime does not lose accepted work.
The `analysis.run` handler is registered in the normal worker. Polling reports
attempt count and sanitized failure codes (`transient`, `timeout`, `permanent`,
`unexpected`, `attempts_exhausted`). Transient failures retry using the durable
worker's existing backoff. Job and analysis state transitions share a transaction.

The main branch did not contain the pipeline from dependent issues #10–11.
`AnalysisPipeline` defines the integration seam. The included HTTP adapter calls
an AI gateway configured with `ANALYSIS_PROVIDER_URL` (HTTPS required) and
`ANALYSIS_PROVIDER_TOKEN`. These settings belong in the worker environment.
No provider credentials are stored in jobs or exposed by status responses.
Unconfigured providers fail permanently, rather than producing demo output.

The gateway receives a JSON POST with `context` and `response_schema`.
Context contains the pinned prompt template/version/schema version, normalized
costs, usage classification, freshness, stored alternative plans and evidence
snapshots. It contains no user ID, provider secrets or raw ingestion metadata.
The gateway must return a JSON object matching the supplied schema, for example:

```json
{
  "action": "review",
  "alternative_plan_id": null,
  "confidence": "0.6",
  "rationale": "Usage evidence is incomplete; review the subscription.",
  "evidence_ids": ["70000000-0000-4000-8000-000000000001"]
}
```

Evidence IDs must refer to the provided context. Output fields, confidence,
actions and references are validated locally. Savings are calculated from stored
plans, never supplied by AI. Cancellation requires fresh explicit unused evidence;
downgrades require a stored cheaper alternative in the same currency and known
usage. Recommendations and the evidence snapshots used to produce them commit
atomically with successful job and analysis state. Exceptions roll back all results.
Only recommendations are produced; no subscription action is executed.

AI gateway 429/5xx/network failures retry; invalid output and other HTTP errors
fail permanently. The adapter limits the response to 64 KiB and uses a 60-second
network timeout within the existing worker timeout. Tests inject a local pipeline;
no paid API call is needed. A live gateway smoke test requires deployment-specific
configuration and credentials.

## Verification

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

Set `TEST_DATABASE_URL` and `TEST_REDIS_URL` to run the existing real-service
worker/migration tests. SQLite tests verify API behavior and rollback, but cannot
prove PostgreSQL row-lock or concurrent request behavior.
