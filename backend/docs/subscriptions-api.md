# Manual subscription and plan API

All five routes require a bearer token. Resource queries are scoped to that
user. The existing catalog supplies provider IDs; provider creation is outside
this API. A provider connection is optional, but must belong to the caller and
the current plan's provider when supplied.

## Create

POST `/api/v1/subscriptions` accepts exactly one of an existing `plan_id` or a
new inline `plan`, plus optional inline `plan_alternatives` (at most 50):

```json
{
  "name": "Streaming",
  "plan": {
    "provider_id": "00000000-0000-0000-0000-000000000001",
    "name": "Standard",
    "amount": "19.1234",
    "currency": "USD",
    "billing_interval": "monthly"
  },
  "plan_alternatives": [],
  "renewal_at": "2026-11-01T00:00:00Z"
}
```

Use an actual catalog provider ID. Amounts use Decimal throughout and the
existing `Numeric(18,4)` plan column: nonnegative, finite, at most four decimal
places and fourteen integral digits. Send decimal strings; responses serialize
amounts as strings. Currency accepts three ASCII letters and normalizes to
uppercase. Cadence accepts daily, weekly, monthly, or yearly (the database's
existing billing_interval column is a string, not an enum). Status uses the
same active/paused/cancelled/expired enum in the API and database.

## Read and update

GET collection returns `items` and shared `pagination` metadata; `page` defaults
to 1, `page_size` to 20 (maximum 100), with optional `status` filtering. Ordering
is descending creation time then ID. GET by ID returns the current `plan`, its
`plan_id`, and `plan_alternatives` along with subscription fields.

PATCH accepts either `plan_id` or a full inline `plan` to replace the current
plan. An inline plan always gets a new ID, preserving shared catalog data.
`plan_alternatives` replaces the entire collection; `[]` clears it. Omitting a
field preserves it. Dates and provider_connection_id accept explicit null to
clear; plan, plan_id, name, status, and plan_alternatives reject null. All input
timestamps must include a timezone. Unknown fields are rejected.

Lifecycle behavior preserves the existing domain rule: cancelled cannot become
paused; other transitions among the four valid statuses are accepted. This API
does not infer ended_at from status changes. Unsupported states return 422 and
the forbidden transition returns 400. Missing plans/providers and foreign or
mismatched provider connections return 422 without partial writes.

## Delete and migrations

DELETE returns 204 and soft-deletes the subscription. Subsequent read/update/
delete return 404. Lists omit it; downstream history remains stored. See
[the deletion ADR](adr/0002-subscription-delete-semantics.md).

Run `uv run alembic upgrade head` before using the API. The new association
migration is reversible; downgrading it removes alternative associations only.
