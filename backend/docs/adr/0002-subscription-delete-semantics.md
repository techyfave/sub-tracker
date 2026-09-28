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