## Context

The subscription tracker needs authenticated access to user-owned subscriptions, transactions, analyses, recommendations, and decisions. The MVP must identify the caller and enforce ownership without coupling domain logic to a particular authentication vendor.

The backend remains a **modular monolith**. Authentication is an external/infrastructure concern and must be isolated behind a replaceable port/adapter.

## Options considered

1. **Application-managed server sessions**
   - Simple for a traditional web application.
   - Couples clients to server-side session state and a session store.

2. **JWT bearer authentication**
   - Stateless request authentication.
   - Works well for web and API clients.
   - Requires careful signature/issuer/audience validation and token expiry handling.

3. **Vendor-specific authentication SDK throughout the application**
   - Fast initial integration.
   - Creates direct vendor coupling and leaks external concepts into application/domain code.

## Decision

The MVP uses **JWT bearer authentication**.

The application authenticates requests using a provider-neutral `AuthenticationPort`. An infrastructure adapter validates JWTs and exposes a normalized authenticated principal:

```text
AuthenticatedPrincipal
- user_id
- issuer
- token_id (optional)
```

The application/domain layer uses `user_id` and authorization rules only. It does not import an authentication SDK, JWT library, OAuth vendor type, or identity-provider model.

Token requirements:

- Signature must be validated.
- `exp` must be enforced.
- `iss` and `aud` must be validated when configured.
- The authenticated principal must map to an existing application `User`.
- User-owned resources are authorized by that `user_id`.

The MVP may use a configured JWT issuer/key set. Replacing that issuer requires changing only the authentication adapter/configuration, not domain logic.

## Consequences

### Positive

- Clear API authentication contract.
- Stateless request validation.
- External identity providers can be replaced without changing domain models.
- Authorization remains based on the application's `User` entity.
- Preserves the modular-monolith architecture.

### Negative

- JWT validation and key rotation must be implemented/configured correctly.
- Revocation before token expiry is more complex than server-side sessions.
- A concrete identity provider still has to be configured for deployed environments.

## Implementation boundary

```text
HTTP/API
  -> AuthenticationPort
      -> JWT authentication adapter
  -> Application services
  -> Domain modules
```

No authentication SDK or provider-specific identity object may be imported by domain modules.
