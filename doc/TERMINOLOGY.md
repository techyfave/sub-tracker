# Subscription Tracker API and Domain Terminology

This glossary defines the canonical names used by the MVP API, domain model, documentation, and code. These spellings are normative.

## Core entities

### User
A person who owns subscription-tracker data and can authenticate to the system.

- Canonical singular: `User`
- Canonical collection: `users`
- API resource: `/users`
- Do not use `Users` as an entity/type name.

### Provider
An external service that supplies subscription, billing, usage, or related data.

- Canonical singular: `Provider`
- Collection: `providers`
- Examples are integration concepts, not domain-specific vendor classes.

### Provider Connection
A user's configured connection to a Provider.

- Canonical singular: `ProviderConnection`
- Collection: `provider_connections`
- It represents the relationship/configuration, not the provider itself.
- Credentials/tokens are integration concerns and are never domain values.

### Plan
The commercial offering published by a provider, such as a monthly or annual tier.

- Canonical singular: `Plan`
- Collection: `plans`
- A Plan describes available terms; it is not the user's purchase/relationship.

### Subscription
A user's active or historical enrollment in a Plan.

- Canonical singular: `Subscription`
- Collection: `subscriptions`
- A Subscription references one User and one Plan.

### Transaction
A monetary event associated with a Subscription.

- Canonical singular: `Transaction`
- Collection: `transactions`
- A Transaction has an explicit amount and currency.
- Do not use `payment` when the domain means a recorded monetary transaction.

### Consent
A versioned grant by a User allowing specified provider data access or processing.

- Canonical singular: `Consent`
- Collection: `consents`
- Revocation ends future use under that grant; it does not rewrite audit history.

### Usage Event
A timestamped factual observation used as analysis evidence, such as activity, a usage count, or a source-reported occurrence.

- Canonical singular: `UsageEvent`
- Collection: `usage_events`
- A bundle or projection of UsageEvents may be called usage evidence in prose, but the persisted/API entity is `UsageEvent`.
- Usage Events are factual input; they are not AI recommendations.

### Analysis
A domain/application result that evaluates subscription value or usage using available evidence.

- Canonical singular: `Analysis`
- Collection: `analyses`
- An Analysis may reference a Subscription and supporting UsageEvents.
- AI-generated reasoning is stored as content associated with the analysis, subject to ADR-004.

### Recommendation
A proposed course of action produced from an Analysis.

- Canonical singular: `Recommendation`
- Collection: `recommendations`
- A Recommendation is advice, not an executed operation.
- It may cite Recommendation Evidence.

### Recommendation Evidence
The evidence or rationale that supports a Recommendation.

- Canonical singular: `RecommendationEvidence`
- Collection: `recommendation_evidence`
- It links the recommendation to observable facts or analysis output.

### Recommendation Decision
The user's chosen outcome after considering a Recommendation.

- Canonical singular: `RecommendationDecision`
- Collection: `recommendation_decisions`
- A RecommendationDecision records what the user decided; it is not the same as a Recommendation.

### Action
An immutable record of a simulated or real operation requested after a RecommendationDecision, such as a cancellation or plan change.

- Canonical singular: `Action`
- Collection: `actions`
- An Action has its own lifecycle and idempotency key.
- Recommendation values such as `keep`, `cancel`, `downgrade`, or `review` use the field `recommended_action`; they are not Action records.

### Savings Record
A calculated or verified monetary benefit associated with a Recommendation or completed Action.

- Canonical singular: `SavingsRecord`
- Collection: `savings_records`
- Estimated and verified savings must remain distinguishable.

### Conversation and Message
A Conversation is the bounded discussion associated with a Recommendation; a Message is one ordered entry in that Conversation.

- Canonical collections: `conversations`, `messages`
- Messages do not replace retained raw AI provider payloads and remain subject to applicable retention rules.

### Prompt Version
Immutable metadata identifying the reviewed prompt contract used for an Analysis.

- Canonical singular: `PromptVersion`
- Collection: `prompt_versions`

### Evaluation Run and Evaluation Result
An EvaluationRun records one execution of a versioned evaluation suite; each EvaluationResult records an individual scored or classified outcome.

- Canonical collections: `evaluation_runs`, `evaluation_results`

### Audit Event
An append-only record of a significant security, decision, or action event.

- Canonical singular: `AuditEvent`
- Collection: `audit_events`
- Audit Events cannot be updated through normal repositories.

## Processing concepts

### Job
An asynchronous unit of backend work.

- Canonical singular: `Job`
- Collection: `jobs`
- Job execution is infrastructure/application behavior and must not expose Celery-specific concepts to domain logic.

### Job Status
The lifecycle state of a Job.

Allowed values:
- `queued`
- `running`
- `succeeded`
- `failed`
- `cancelled`

Do not use `pending`, `complete`, or `error` as alternate API values.

### Analysis Status
The lifecycle state of an Analysis.

Allowed values:
- `queued`
- `running`
- `completed`
- `failed`

`completed` means the analysis produced a usable result. `succeeded` is reserved for Job Status.

## AI concepts

### AI Provider
An external model/service capable of generating structured AI output.

- Canonical singular: `AIProvider`
- It is an integration concept behind the application port defined in ADR-003.

### AI Adapter
An infrastructure implementation of the provider-neutral `AIProvider` port.

- Canonical singular: `AIAdapter`
- Examples may include Gemini, Groq, or another provider adapter.
- Vendor names must not appear in domain types.

### AI Prompt
The application instruction sent to an AI Provider.

### AI Response
The provider response received by the application after an AI Prompt.

### Provider Connection vs AI Provider
A Provider Connection belongs to a user's external data integration. An AI Provider is the service used to perform AI generation. They are distinct concepts.

## Money

### Money
A monetary value represented by an exact decimal amount plus an explicit Currency.

- Canonical fields: `amount`, `currency`
- `amount` uses an exact decimal database/application type, never binary floating point.

### Currency
An ISO 4217 currency code.

- Canonical field: `currency`
- MVP seed/demo currency: `NGN`
- USD or another currency may be stored when the real source transaction/plan is denominated in that currency. No implicit conversion is performed.

### Demo Currency
The currency used by deterministic development seed data.

- Canonical value: `NGN`

## Relationship rules

- User -> Subscription: one User can have many Subscriptions.
- Plan -> Subscription: one Plan can have many Subscriptions.
- Subscription -> Transaction: one Subscription can have many Transactions.
- Subscription -> UsageEvent: one Subscription can have many UsageEvent records.
- Subscription -> Analysis: one Subscription can have many Analyses over time.
- Analysis -> Recommendation: an Analysis can produce zero or more Recommendations.
- Recommendation -> RecommendationEvidence: a Recommendation can have zero or more supporting evidence records.
- Recommendation -> RecommendationDecision: a user may record a RecommendationDecision based on a Recommendation.
- RecommendationDecision -> Action: an accepted RecommendationDecision may result in one or more idempotent Actions.
- Recommendation/Action -> SavingsRecord: savings remain traceable to their source.
- Recommendation -> Conversation -> Message: follow-up discussion remains bounded to its recommendation.
- Analysis -> PromptVersion: each run records the prompt version used.
- EvaluationRun -> EvaluationResult: a run contains one or more results.
- Significant domain operations -> AuditEvent: security-sensitive and state-changing operations emit append-only audit history.
- User -> ProviderConnection: one User can have many ProviderConnections.

These relationships are the agreed MVP vocabulary and should be reflected consistently in API schemas, database models, tests, and documentation.

## Cross-cutting invariants

- Every user-owned record has an explicit `user_id` ownership key and an ownership-query index.
- Persisted timestamps are UTC-aware; API timestamps use ISO 8601 with an explicit UTC offset.
- Recommendation records are immutable snapshots. Corrections or reanalysis create new versions rather than updating a snapshot through a normal repository.
- AuditEvent records are append-only and cannot be updated or deleted through normal repositories.
- External authentication, job, AI, financial-data, and future exchange-rate integrations remain infrastructure adapters behind application-owned ports.
- All modules remain within one deployable modular monolith unless a later ADR supersedes that decision.
