# Data and API Plan

The following design belongs to the shared product after prototype convergence. The initial scaffold includes only connection and health foundations.

## Principal entities

| Entity | Responsibility |
|---|---|
| `users` | Identity and account state |
| `consents` | Versioned grants, scopes, and revocations |
| `provider_connections` | Future provider connection metadata |
| `subscriptions` | Subscription and billing information |
| `subscription_plans` | Current and alternative plans |
| `transactions` | Normalized financial occurrences |
| `usage_events` | User- or provider-derived usage evidence |
| `analyses` | Analysis job and version state |
| `recommendations` | Validated recommendation snapshots |
| `recommendation_evidence` | Traceable supporting evidence |
| `recommendation_decisions` | Approval, rejection, correction, or defer response |
| `actions` | Simulated or real action lifecycle |
| `savings_records` | Estimated and verified savings |
| `conversations` / `messages` | Bounded recommendation discussion |
| `prompt_versions` | Prompt lifecycle metadata |
| `evaluation_runs` / `results` | Versioned quality measurements |
| `audit_events` | Append-only significant operations |

## Data rules

- Every user-owned row has an enforceable ownership boundary.
- Timestamps are stored in UTC.
- Money stores decimal amount and currency.
- Raw provider payload retention is minimized.
- Recommendations are immutable snapshots.
- Approval references an exact recommendation version.
- Audit events are append-only.
- External syncs and actions are idempotent.
- Deletion and anonymization workflows are defined before live providers.

## Planned API

All routes are versioned under `/api/v1`.

### Identity and consent

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /me`
- `GET|POST /consents`
- `DELETE /consents/{id}`

### Subscription evidence

- `GET|POST /subscriptions`
- `GET|PATCH|DELETE /subscriptions/{id}`
- `POST /subscriptions/{id}/transactions`
- `POST /subscriptions/{id}/usage-events`

### Analyses and recommendations

- `POST /analyses`
- `GET /analyses/{id}`
- `GET /recommendations`
- `GET /recommendations/{id}`
- `POST /recommendations/{id}/decisions`
- `POST /recommendations/{id}/reanalyze`

### Conversation, actions, and savings

- `GET|POST /recommendations/{id}/messages`
- `GET /actions`
- `GET /actions/{id}`
- `POST /actions/{id}/retry`
- `GET /savings`

### Operations

- `GET /health/live`
- `GET /health/ready`
- `GET /version`

## API standards

- Pydantic request and response models;
- consistent problem-details errors;
- pagination and filter conventions;
- correlation IDs;
- ownership checks;
- idempotency for analysis and action creation;
- generated OpenAPI examples;
- rate limits for expensive endpoints;
- database models never returned directly.
