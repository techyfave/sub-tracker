# Ingestion Idempotency & Retry Contract

## Transaction Ingestion (`POST /subscriptions/{id}/transactions`)
- **Deduplication Boundary**: Scoped safely to the compound constraint `(user_id, source, external_reference)`.
- **Behavior**: If a matching external transaction signature is submitted consecutively, an atomic PostgreSQL `UPSERT` updates the target record values to reflect the latest tracking payload without throwing unique-constraint crashes.

## Usage Evidence Ingestion (`POST /subscriptions/usage-events`)

- **Deduplication Boundary:** Uniqueness is enforced across `(user_id, source, idempotency_key)`.
- **Behavior:** When a key is provided, repeated submissions with the same user, source, and key are handled atomically using PostgreSQL `ON CONFLICT DO NOTHING`.
- **Optional Key:** When the idempotency key is omitted, the event is stored without key-based deduplication.
- **Retry Safety:** Clients can retry a request with the same key without creating duplicate usage-event records.
