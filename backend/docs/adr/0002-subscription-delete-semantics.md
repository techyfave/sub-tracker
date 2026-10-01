# 2. Subscription Delete Semantics

## Status
Accepted

## Context
When a user requests to delete a subscription, we need to decide between hard deleting (permanently removing the record from the database) or soft deleting (marking it with a timestamp).

## Decision
We choose **Soft Deletion** by setting a `deleted_at` timestamp on the `subscriptions` table.

### Rationale:
1. **Audit & Recovery:** Soft deleting preserves historical record data for user analytics and cost optimization tracking without loss of history.
2. **Data Integrity:** Soft-deleted records prevent cascading hard-deletes on historical transaction logs.
3. **Query Filtering:** All default `GET` queries filter out records where `deleted_at IS NOT NULL`.

## Consequences
- Repository queries must always include `deleted_at.is_(None)` checks.
- A background clean-up job can be introduced later if hard-purging GDPR requests require complete data erasure.

## Implementation and downstream history

Migration `39e56c2ba5ef` adds `subscriptions.deleted_at`; migration
`a71e00700001` adds a subscription-to-alternative-plan association table.
DELETE updates `deleted_at` and `updated_at` only. It does not delete the
subscription, its plans, alternative associations, transactions, usage events,
analyses, recommendations, or audit history. Existing foreign-key cascades are
therefore not triggered. GET, PATCH and repeated DELETE return 404 for a deleted
subscription, and list counts exclude it. Foreign-owned IDs also return 404.

Plan changes create new plan records rather than modifying shared catalog rows.
Replacing alternatives removes only their associations, retaining prior plan
records. No hard-delete or background purge is implemented by this issue.
