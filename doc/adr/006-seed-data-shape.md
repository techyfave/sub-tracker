# ADR-006: Seed Data Shape

**Status:** Accepted

## Context

The MVP needs predictable data for local development, API testing, demos, and integration tests. Earlier task-tracker concepts such as `Tracker -> Project -> Task -> Subtask` do not belong to the subscription-tracker domain.

The seed model must represent the actual MVP entities while remaining small enough to understand and reset.

The backend remains a **modular monolith**. Seed data must use domain/application interfaces rather than importing external provider SDKs or making live provider calls.

## Options considered

1. **Large production-like fixture**
   - High coverage.
   - Hard to maintain and difficult to reason about.

2. **Minimal deterministic relational seed**
   - Small and predictable.
   - Covers the relationships needed by the MVP.

3. **Randomized/generated seed data**
   - Produces variety.
   - Makes tests and demos non-reproducible.

## Decision

The MVP uses a **deterministic, minimal, relationally valid, idempotent, development-only seed dataset**.

### Canonical entities and relationships

```text
User
 ├── Consent
 ├── ProviderConnection
 └── Subscription
       ├── Plan
       ├── Transaction
       ├── UsageEvent
       └── Analysis
              └── Recommendation
                     └── RecommendationEvidence

Recommendation
 ├── RecommendationDecision
 │     └── Action
 ├── SavingsRecord
 └── Conversation
       └── Message

PromptVersion
 └── Analysis

EvaluationRun
 └── EvaluationResult

AuditEvent
```

More precisely:

- `User 1 -> many Subscription`
- `Plan 1 -> many Subscription`
- `Subscription 1 -> many Transaction`
- `Subscription 1 -> many UsageEvent`
- `Subscription 1 -> many Analysis`
- `Analysis 1 -> many Recommendation`
- `Recommendation 1 -> many RecommendationEvidence`
- `Recommendation 1 -> zero or many RecommendationDecision` over time, with the initial seed using one decision per seeded recommendation where useful.
- `User 1 -> many ProviderConnection`
- `User 1 -> many Consent`
- `RecommendationDecision 1 -> zero or many Action`
- `Recommendation or Action 1 -> zero or many SavingsRecord`
- `Recommendation 1 -> zero or one Conversation -> many Message`
- `PromptVersion 1 -> many Analysis`
- `EvaluationRun 1 -> many EvaluationResult`
- `AuditEvent` references the relevant actor/resource without becoming mutable domain state.
- A `ProviderConnection` identifies an external integration configuration; it does not replace `Provider`.

### Minimum seeded dataset

The seed should contain at least:

- 2 Users
- 2 Providers
- 2 ProviderConnections
- 3 Plans
- 4 Subscriptions covering different statuses
- 4 Transactions using NGN
- 4 UsageEvent records
- 3 Analyses covering meaningful outcomes
- 3 Recommendations
- 3 RecommendationEvidence records
- 2 RecommendationDecisions
- 2 Consents covering granted and revoked states
- 2 Actions covering simulated success and pending execution
- 2 SavingsRecords distinguishing estimated and verified savings
- 1 Conversation with 2 Messages
- 1 PromptVersion referenced by the seeded Analyses
- 1 EvaluationRun with representative EvaluationResults
- representative append-only AuditEvents

Exact fixture IDs and timestamps must be fixed rather than generated randomly.

### Seed rules

- **Deterministic:** same seed produces the same logical records.
- **Minimal:** include only data needed for development and demonstrations.
- **Idempotent:** running the seed repeatedly does not create duplicate logical records.
- **Relationally valid:** foreign keys and domain invariants are satisfied.
- **Development-only:** seed credentials and data must never be treated as production data.
- **No live external calls:** providers, AI services, and job brokers are represented through local fixtures/fakes.
- **NGN demo currency:** seeded monetary values use NGN as required by ADR-005.

## Consequences

### Positive

- API and integration tests have stable fixtures.
- Developers can reproduce bugs using the same data.
- The seed reflects the actual subscription-tracker domain.
- Re-running setup is safe.
- External providers remain behind replaceable adapters.

### Negative

- The dataset does not represent every production edge case.
- Developers must add explicit fixtures when testing unusual cases.
- Seed evolution requires updating dependent tests when domain relationships change.
