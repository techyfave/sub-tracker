# Fresh Contributor Walkthrough

**Contributor handle:** `Abbyleye`
**Walkthrough record date:** 2026-10-23
**Status:** Partially completed; full-stack walkthrough remains blocked
**Environment:** Windows, PowerShell
**Python:** 3.13.16
**uv:** 0.13.1
**Git:** 2.54.0.windows.1
**Docker:** Docker CLI unavailable in the attempted environment
**PostgreSQL:** No matching Windows service was found; `localhost:5432` refused TCP connections
**Redis:** `localhost:6379` refused TCP connections
**Integration tests:** 92 passed, 37 skipped, 0 failures in the latest recorded test run

This record distinguishes checks completed in the current working tree from integration steps that remain unverified. A fresh checkout and a complete full-stack walkthrough have not been confirmed. The Docker, PostgreSQL, and Redis checks document the current attempted environment and do not establish that these services are unavailable on every machine.

## 1. Environment and quality checks

| Check | Expected result | Actual result | Status |
|---|---|---|---|
| `uv run ruff check .` | No lint errors | All checks passed | Passed |
| `uv run ruff format --check .` | All files formatted | 114 files already formatted | Passed |
| `git diff --check` | No whitespace errors | No whitespace errors; LF-to-CRLF warnings reported for two files | Passed with line-ending warnings |
| `uv run mypy app` | No type errors | Success: no issues found in 79 source files | Passed |
| `uv run pytest` | Tests pass; service-dependent tests run when configured | 92 passed, 37 skipped, 0 failures | Passed with skips |
| `uv run pytest tests/test_consent.py -v` | Consent behavior and access controls pass | 4 passed in the previously recorded run | Passed |
| `uv run python check_openapi.py` | OpenAPI responses and examples are present | `OPENAPI SCHEMA AUDIT PASSED` | Schema/example audit passed |

These results are from the current working tree, not a verified fresh clone. The full test suite did not run all service-dependent tests because the required test-service URLs were not configured.

The latest test run completed in 32.76 seconds. The skip messages identify missing `TEST_DATABASE_URL` for PostgreSQL tests and missing `TEST_DATABASE_URL` and `TEST_REDIS_URL` for the real Redis broker test.

## 2. Full-stack setup

**Expected:** Start the Compose services, confirm service health, and verify API readiness.

**Actual:** The repository's `compose.yaml` was inspected. It defines PostgreSQL, Redis, migrations, the API, a worker, and a scheduler. The Docker CLI was unavailable during the setup attempt, so the Compose stack and its health checks were not verified.

The following checks were performed:

- `docker --version` — PowerShell reported that `docker` was not recognized.
- `Get-Service *postgres*` — no matching PostgreSQL Windows service was returned.
- `Test-NetConnection localhost -Port 5432` — `TcpTestSucceeded: False`.
- `Test-NetConnection localhost -Port 6379` — `TcpTestSucceeded: False`.

The local API was started separately using Uvicorn. This did not establish that the full Compose stack was operational.

**Status:** Blocked.

**Follow-up:**

- Install or enable Docker Desktop, if available in the environment.
- Confirm `docker --version` and `docker compose version` work.
- Record the Docker version and actual startup and health-check results.
- Verify the API and dependencies through the documented Compose setup.

## 3. Database migrations and seed idempotency

**Expected:** Apply migrations and execute the documented seed command twice against the same disposable PostgreSQL database. Confirm the second run creates no duplicate logical records and preserves all documented scenarios.

**Actual:** The local PostgreSQL connection check to `localhost:5432` failed. A registration attempt against the locally running API returned HTTP 500 because the database connection was refused. PostgreSQL integration tests were skipped because `TEST_DATABASE_URL` was not configured.

A successful two-run seed check against PostgreSQL has not been established. The existing seed tests passed, but those tests do not establish PostgreSQL seed repeatability.

**Status:** Blocked / not verified.

**Follow-up:**

1. Configure a disposable PostgreSQL database reserved for testing.
2. Apply the documented migrations.
3. Run the documented seed command twice against the same database.
4. Record both commands, their outputs, and relevant table counts before and after the second run.
5. Confirm all six scenarios remain consistent with [Demo Seed Scenarios](seed-scenarios.md).
6. Record blockers rather than marking this check passed.

The seed dataset must contain exactly one estimated savings record for the seeded downgrade scenario. Do not fabricate a verified savings record. An estimate is not evidence of realized savings; verification requires a completed action and confirming post-change billing evidence.

## 4. Authentication and protected requests

**Expected:** Register an account, log in, obtain the access token from the login response, and make an authenticated request to a protected endpoint.

**Actual:** The local API was running, but a registration attempt returned HTTP 500 because the PostgreSQL connection was refused. A successful registration, login, and authenticated protected request have not been established in this walkthrough.

An unauthenticated `GET /api/v1/consents` request returned HTTP 401 with `Content-Type: application/problem+json` and a Problem Details response body. This verifies the observed unauthenticated response only; it does not verify the authenticated consent flow.

**Status:** Partially verified; successful authentication flow blocked by database availability.

**Follow-up:** Once a suitable database is available, record the exact requests and observed status codes for registration, login, and an authenticated protected request. Registration returns user data, not access tokens. Obtain `tokens.access_token` from the login response. Never record passwords or live tokens in this document.

## 5. Background worker smoke check

**Expected:** Follow [Background Jobs](../backend/docs/background-jobs.md), run its documented harmless probe or status check, and verify the resulting job status and worker logs.

**Actual:** The Compose worker and scheduler were identified in `compose.yaml`, but neither was started or verified in the attempted environment. No worker probe, resulting job status, or worker log evidence has been recorded.

**Status:** Not run; blocked by unavailable Docker/runtime dependencies.

**Follow-up:** Record the probe command, observed job status, relevant worker output, and any blocker. API availability alone does not prove that a background worker is processing jobs.

## 6. Integration tests

**Expected:** Configure separate disposable PostgreSQL and Redis test services and run the database-dependent integration tests.

**Actual:** The latest test run completed with 92 passed, 37 skipped, and 0 failures. Skip messages identify missing `TEST_DATABASE_URL` for PostgreSQL tests and missing `TEST_DATABASE_URL` and `TEST_REDIS_URL` for the real Redis broker test. Separate connectivity checks confirmed that PostgreSQL and Redis were not accepting connections on their default localhost ports.

**Status:** Partially passed; service-dependent tests outstanding.

**Follow-up:**

- Configure `TEST_DATABASE_URL` for a dedicated, disposable PostgreSQL test database.
- Configure `TEST_REDIS_URL` for the test Redis service required by the tests.
- Apply the required migrations and verify the test settings before running destructive tests.
- Rerun the previously skipped integration tests and record the results.
- Never point destructive test setup at a development or production database.

Do not describe the full integration suite as passed until the required tests have actually run.

## 7. OpenAPI verification

**Expected:** Verify the generated `/openapi.json` for operation-level success and error examples, including Problem Details responses, pagination, UTC timestamps, and the bodyless `204` response. Also verify representative actual HTTP responses.

**Actual:**

- `uv run python check_openapi.py` completed with `OPENAPI SCHEMA AUDIT PASSED`.
- `GET /api/v1/health/live` returned HTTP 200.
- `GET /openapi.json` returned HTTP 200.
- An unauthenticated `GET /api/v1/consents` returned HTTP 401 with `Content-Type: application/problem+json` and a Problem Details response body.
- A registration attempt returned HTTP 500 because the database connection was refused.

These observations verify only the listed paths and outcomes. The schema audit and limited live HTTP checks do not establish that every documented success and error response matches the implementation.

**Status:** Schema/example audit passed; limited live HTTP checks completed; full live-response verification outstanding.

**Follow-up:** Configure a suitable test environment and verify representative successful and failing requests, including registration conflict, login failures, refresh-token errors, validation errors, rate limiting, consent ownership, and subscription responses. Compare actual status codes, content types, and response bodies with the generated OpenAPI contract. Record any database- or service-related blockers rather than treating untested paths as passed.

## 8. Outstanding acceptance checklist

- [x] Record the Git version: `2.54.0.windows.1`.
- [ ] Complete a fresh-checkout walkthrough or explicitly document why it remains blocked.
- [ ] Verify Docker Compose startup and health checks.
- [ ] Verify migrations and run the seed command twice against PostgreSQL.
- [ ] Record seed idempotency evidence and relevant table counts.
- [ ] Verify successful registration, login, and an authenticated request.
- [ ] Verify the documented background worker smoke check.
- [ ] Configure disposable PostgreSQL and Redis test services and rerun the skipped tests.
- [ ] Verify representative live HTTP responses against the generated OpenAPI contract.
- [x] Record available quality-check results, observed HTTP responses, tool versions, and known blockers.

Do not mark a blocked or unrun item as passed without recording the corresponding command and observed result.

The pull request should remain in Draft until the outstanding acceptance requirements and required integration evidence have been addressed.


## Maintainer handoff for independent validation

The earlier attempt above remains historical evidence, not a completed acceptance check.
Fill this section after a different contributor follows the updated runbook:

- Contributor: `FRESH_CONTRIBUTOR_HANDLE`
- Date: `WALKTHROUGH_DATE`
- Checked-out commit: `WALKTHROUGH_COMMIT`
- OS/tool versions: `WALKTHROUGH_ENVIRONMENT`
- Exact commands, expected/actual outcomes, fixes and service-backed test results: `WALKTHROUGH_RESULTS`

See [handoff instructions](issue-20-handoff.md) for replacements and dependency tracking.
Agent verification is recorded separately in issue-20-verification.md and does not substitute
for this independent human walkthrough.
