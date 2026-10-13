# ADR-007: Application-Managed Credentials and Refresh-Token Rotation

**Status:** Accepted

**Refines:** [ADR-001 Authentication Approach](001-authentication-approach.md)

## Context

ADR-001 decided that the MVP authenticates API requests with JWT bearer tokens behind a replaceable authentication boundary. It deliberately left open *who owns user credentials* and *how a session is renewed and revoked*, noting that "revocation before token expiry is more complex than server-side sessions" and that a concrete identity provider might be configured later.

Issue #5 implements registration, login, refresh, and current-user resolution. That requires concrete decisions ADR-001 did not record. This ADR records them so the ADR remains the source of truth for the implementation.

## Decision

The MVP backend is **its own credential authority**. There is no external identity provider in the MVP.

### Passwords

- The application stores and verifies passwords itself.
- Passwords are hashed with **Argon2id** (library defaults, self-describing hash format so parameters can be raised later and old hashes verified/upgraded).
- Emails are normalized (trimmed, lower-cased) before lookup and storage.
- Login failures for an unknown email and for a wrong password are indistinguishable in the response, and an unknown email still performs a dummy hash verification to keep timing comparable.

### Access tokens

- Short-lived, stateless **JWT** access tokens (default 15 minutes), signed with an application secret (HS256 in the MVP).
- Claims: `sub` (user id), `iat`, `exp`, and `type = "access"`. Only the pinned algorithm is accepted on decode; tokens whose `type` is not `access` are rejected.
- Access tokens are not stored and cannot be revoked individually. Their short lifetime bounds exposure.

### Refresh credentials

- Refresh credentials are **opaque random values** (not JWTs), generated with a cryptographically secure source (384 bits).
- Only a **SHA-256 hash** is persisted. The raw value is returned to the client once and never stored, so a database read cannot yield a usable credential.
- Credentials are **single-use and rotated**: every successful refresh consumes the presented credential and issues a replacement (default lifetime 30 days).
- **Rotation must be atomic.** Consuming the presented credential and persisting its replacement happen as one database operation in one transaction: a conditional update that revokes the credential only if it is still unrevoked, returning whether this caller won. When multiple requests present the same credential concurrently, at most one succeeds; the rest are treated as replays. This is required for correctness and is verified by a PostgreSQL concurrency test.
- **Replay detection:** presenting a credential that is already revoked (whether by an earlier request or by losing a concurrent race) is treated as possible theft. All of that user's refresh credentials are revoked, and the caller must sign in again. This revocation is committed immediately and must survive the request that reports the error.
- Expired credentials and credentials belonging to deactivated users are revoked and rejected.

### Authorization

- Requests are authenticated by a reusable current-user dependency that resolves the bearer token to an existing, active application `User`.
- Resource-level authorization is by owner: an owned resource is accessible only when its owner id equals the authenticated user's id, via one shared ownership check that returns a Problem Details 403 on mismatch.
- Authentication endpoints (register, login, refresh) are rate limited per client (default `5/minute`, configurable).

## Relationship to ADR-001

The decision in ADR-001 stands: JWT bearer authentication, isolated behind a replaceable boundary, with authorization keyed on the application `User`. The implementation differs from ADR-001's wording in these deliberate ways:

| ADR-001 wording | Implementation |
|---|---|
| `AuthenticationPort` returning an `AuthenticatedPrincipal` (`user_id`, `issuer`, `token_id`) | The port is `AccessTokenIssuer` in `app/application/auth/ports.py`, and the API layer resolves it to a `User` in the current-user dependency. Only `user_id` is carried; `issuer` and `token_id` are not needed while the app is the sole issuer. |
| `iss` and `aud` validated "when configured" | Not configured, because the application is the only issuer and audience. If an external identity provider is introduced, `iss`/`aud` validation must be added in the adapter. |
| "Configured JWT issuer/key set" | A single symmetric application secret (HS256) supplied via configuration. Moving to asymmetric keys or an external issuer changes only the adapter and configuration. |

Domain code still imports no JWT library, hashing library, or web framework. Password hashing, refresh-token generation/hashing, and access-token issuing are all ports implemented in the infrastructure layer.

## Consequences

### Positive

- Self-contained MVP with no external identity dependency.
- Refresh theft and replay are detected, and concurrent replay cannot mint two live sessions.
- A database leak exposes neither passwords nor usable refresh credentials.
- Adapters remain replaceable, preserving the modular monolith.

### Negative

- The application is responsible for password storage, rotation correctness, and rate limiting.
- Access tokens remain valid until expiry even after a session is revoked (bounded by their short lifetime).
- Replay detection can sign out a legitimate user whose client submits the same refresh credential twice (for example a double-submit or a retry after a lost response). Clients must serialize refresh calls and never retry with a rotated credential.
- HS256 uses a shared secret, so it must be provided securely per environment and rotated deliberately.
