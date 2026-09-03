# Provisional note: authentication approach (pending issue #1 ADR)

**Status:** Provisional — implemented to unblock issue #5, not an accepted ADR.
Issue #1 owns the formal decision and may supersede this note entirely.

## What issue #5 assumes

- **Access tokens:** short-lived JWT (HS256, 15 min default), stateless, carrying only
  the user id. Not persisted, not individually revocable.
- **Refresh tokens:** opaque random strings (`secrets.token_urlsafe`), rotated on every
  use. Only a SHA-256 hash is stored in `refresh_tokens`. Reusing an already-rotated
  token revokes the whole family (reuse/theft detection).
- **Password hashing:** Argon2id via `argon2-cffi`.
- **Storage:** minimal `users` + `refresh_tokens` tables (see migration
  `xxxx_create_users_and_refresh_tokens.py`), scoped to what auth needs — not the full
  entity list from `docs/architecture/data-and-api.md`. Issue #3's migration should
  extend the `users` table (add columns) rather than recreate it.

## Why

- Argon2id is the current OWASP-recommended default for new password storage.
- Rotating opaque refresh tokens + reuse detection is the standard mitigation for
  refresh-token theft, and keeps revocation possible (JWTs alone can't be revoked
  without an allow/deny-list).
- Splitting access vs. refresh tokens lets access tokens stay short-lived and
  stateless (cheap to verify on every request) while session-level control lives in
  the revocable refresh-token table.

## Open for the real ADR (issue #1)

- Whether to keep JWT access tokens or move to fully server-side sessions.
- Access/refresh token lifetimes (currently 15 min / 30 days, both env-configurable).
- Whether refresh tokens should also be scoped per-device/client for finer-grained
  revocation.
