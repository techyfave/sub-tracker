# Ingestion Idempotency & Retry Contract

## Transaction Ingestion

Endpoint: `POST /api/v1/subscriptions/{id}/transactions`

The deduplication boundary is `(user_id, source, external_reference)`.

- When the reference is absent, each accepted request creates a transaction.
- Repeating the reference for the same subscription updates the existing transaction's amount, currency, and occurrence time. The latest payload wins.
- Reusing the same reference for a different subscription owned by the same user returns HTTP 409 Conflict. The original record remains unchanged.
- A different user has a separate deduplication boundary.
- The conflict update is guarded by the target subscription ID so cross-subscription reuse cannot modify another subscription's record.

## Usage Event Ingestion

Endpoint: `POST /api/v1/subscriptions/usage-events`

The deduplication boundary is `(user_id, source, idempotency_key)`.

- When the key is absent, accepted events are stored without key-based deduplication.
- Replaying the same key for the same subscription with the same occurrence instant, quantity, and unknown flag returns success without adding another event.
- Reusing a key for a different subscription returns HTTP 409 Conflict.
- Reusing a key on the same subscription with a changed occurrence instant, quantity, or unknown flag returns HTTP 409 Conflict.
- Conflict responses do not modify the existing usage event.
- Different users have separate deduplication boundaries.

## Numeric and Provenance Contract

Amounts and quantities must be finite, non-negative, and representable by `Numeric(18, 4)`. Sources are limited to 50 characters. Currency codes contain exactly three ASCII letters and are normalized to uppercase.

Usage events preserve the source, ingestion method, ingestion timestamp, and supplied idempotency key in their evidence metadata.