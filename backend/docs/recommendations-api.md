# Recommendations API

Read-only endpoints for immutable recommendation snapshots. All routes live under `/api/v1`, require a bearer access token, and return only the caller's own data.

## GET /api/v1/recommendations

Returns a page of the caller's recommendations, newest first.

| Query parameter   | Type    | Default | Meaning                                                        |
| ----------------- | ------- | ------- | -------------------------------------------------------------- |
| `page`            | integer | 1       | Page number, starting at 1.                                    |
| `page_size`       | integer | 20      | Items per page, 1 to 100.                                      |
| `status`          | enum    | none    | Analysis state: `queued`, `running`, `completed` or `failed` (as defined in doc/TERMINOLOGY.md). Any other value returns 422. |
| `action`          | enum    | none    | `keep`, `downgrade`, `cancel` or `review`.                     |
| `subscription_id` | UUID    | none    | Only recommendations about this subscription.                  |

An invalid filter value returns 422 Problem Details.

The response is `{"items": [...], "pagination": {...}}`, using the same pagination envelope as subscriptions.

## GET /api/v1/recommendations/{id}

Returns one recommendation. A missing id, and an id owned by another user, both return the same 404 Problem Details response, so ids cannot be probed.

## Response fields

| Field                | Meaning                                                                       |
| -------------------- | ----------------------------------------------------------------------------- |
| `id`                 | Recommendation id.                                                            |
| `recommended_action` | `keep`, `downgrade`, `cancel` or `review`.                                    |
| `rationale`          | Plain-language explanation.                                                   |
| `versions`           | `recommendation_version`, `prompt_version`, `schema_version`.                 |
| `analysis`           | `analysis_id`, `subscription_id`, `status` (public analysis state), `completed_at`. |
| `uncertainty`        | `confidence` (0 to 1), `level` and `reason`. Both are short public codes, or null. |
| `savings`            | `monthly` and `annual`, each `{amount, currency}`.                            |
| `evidence`           | List of `{id, evidence_type, source_table, source_id, snapshot, created_at}`. `snapshot` is an allowlisted summary. |
| `created_at`         | When the snapshot was created.                                                |

## Behaviour

- Snapshots are immutable. These endpoints never write. A correction or re-analysis creates a new version through a different path.
- Savings are the stored deterministic values. This API does not recompute them.
- A `review` recommendation with high uncertainty is a normal, expected result. Missing usage data is not treated as proof of non-use.
- The response schema is an explicit allowlist. Internal analysis fields (`idempotency_key`, `attempt_count`, `failure_code`) and `user_id` are never returned.

## Public projection

Stored uncertainty and evidence JSON can contain internal values, so the API publishes only an allowlist:

- uncertainty: only `level` and `reason`, and only as short simple tokens.
- evidence snapshot summaries: sessions, value_signal, supports, lower_tier_suitable, requires_review, usage_available, reason, usage_signal, billing_signal, conflict. Values must be null, a boolean, a whole number or a short simple token. The additional billing/usage/plan fields and their stricter validation are documented below. Nested objects and lists are never published.
- Anything else, including unknown keys, is omitted without an error.
- New public keys must be added to the allowlist deliberately, with a test.

## Analysis states

The API publishes the states from doc/TERMINOLOGY.md. The stored worker status `succeeded` is published as `completed`, and the status filter is translated back to the stored value.

Recommendations whose analysis is in a stored state the public vocabulary cannot express (currently `cancelled`) are not published: they are omitted from lists and return 404 on detail. This is an interim rule until issue #13 defines how such analyses are represented.

## Errors

| Status | When                                                      |
| ------ | --------------------------------------------------------- |
| 401    | Missing, invalid or expired bearer token.                 |
| 404    | Recommendation does not exist or belongs to another user. |
| 422    | Invalid filter or path value.                             |

## Assumptions pending issue #13

- The `status` filter and the `analysis.status` field use the public analysis states from doc/TERMINOLOGY.md.
- Issue #13 will persist analyses and recommendations through the existing models. If its contract changes the stored shape, the response schema is adjusted before final integration.
## Typed billing, usage and plan evidence (issues #10/#11/#13/#14)

The analysis writer and recommendation list/detail readers use the following
additional flat snapshot fields. This is also the evidence contract for AI
pipeline adapters in #10/#11; adapters cite source IDs and must not substitute
model-generated amounts for stored plan/evidence values.

| Source table | Public fields | Validation |
| --- | --- | --- |
| `transactions` | `amount`, `currency`, `occurred_at` | Non-negative decimal string, three uppercase currency letters, timezone-aware ISO timestamp |
| `usage_events` | `kind`, `is_unknown`, `quantity`, `occurred_at` | Short token, strict boolean, non-negative decimal string or null, timezone-aware ISO timestamp |
| `plans` | `amount`, `currency`, `billing_interval` | Non-negative decimal string, three uppercase currency letters, daily/weekly/monthly/yearly |

Decimal strings preserve the stored `Numeric(18,4)` precision (up to 14 integer
and 4 fractional digits); floats, exponents, non-finite and negative values are
not published. `quantity: null` and `is_unknown: true` preserve unknown usage;
unknown is never converted to zero. The writer normalizes timezone-naive database
timestamps to UTC. Existing summary fields remain supported under their original
validation rules. `source_table` and `source_id` continue to identify the original
row, and the stored snapshot remains immutable.

These additions are validated field by field. Unknown keys, nested objects and
lists, provider credentials, and model traces remain excluded from both list and
detail responses. Raw ingestion metadata is never copied into public evidence.
