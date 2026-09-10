use JWT authentication
  JSON web Token 
 use this authentication because its widely use and it accept multiple user at a time. I will prescribe this authentication method because its the most use and it issues a signed access token after successful authentication. Morealso, the authentication logic will remain isolated from the application/domain modules so that the authentication mechanism can be replaced later without changing business logic.

 pros:
 -Well suited to REST APIS
 -Stateless authentication 
 -Easy for frontend and mobile clients to consume.

 Cons:
 - Token revocation requires additional handling
 - Tokens must be stored securely by clients.

 We can also consider Third-party authentication if we ever use an external API for the project.

 PROS:
 - Less authentication code to maintain
 - can support social login

CONS:
- Adds external dependency
- More configuration for the MVP
- Authentication becomes coupled to a provider

The authentication module will issue signed access tokens after successful
authentication.

Protected API endpoints will require:

    Authorization: Bearer <token>

The authenticated user's identity will be available to the application through
a request authentication context.

Authentication concerns will remain inside the authentication module. Domain
modules must not contain JWT-specific logic.

The domain/application layer should depend on the concept of an authenticated
user rather than directly depending on JWT implementation details.

## Token Policy

The exact expiration values may be configured separately, but the
implementation must support:

- Token expiration.
- Signature validation.
- User identity extraction.
- Rejection of malformed tokens.
- Rejection of expired tokens.
- Rejection of invalid signatures.

Refresh tokens may be introduced later if required. They are not required to
block the MVP.

## Authorization

Authentication and authorization are separate concerns.

Authentication answers:

    "Who is making this request?"

Authorization answers:

    "Is this user allowed to perform this operation?"

Every user-owned resource must be associated with an owner/user identity.

For example:

    User
      |
      +-- Project
            |
            +-- Asset
            |
            +-- Job

Application services must verify ownership before allowing operations user-owned resources.