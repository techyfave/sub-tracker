# Demo Seed Scenarios

This document defines the deterministic demo scenarios used by the backend seed data.

The seed data must be safe to run repeatedly and must produce the same expected records and recommendation outcomes each time.

## Currency and Locale

* Currency: Nigerian Naira (NGN)
* Locale: Nigeria
* All identities and account information are fictional demo data.
* No real personal information should be used in seed records.

## Schema Dependency

The scenarios in this document define the expected business cases and
recommendation outcomes independently of the final database schema.

When Issue #3 establishes the PostgreSQL models and relationships, each
scenario will be mapped to the corresponding entities, fields, and
relationships without changing the expected scenario behavior.

## ADR-006 Reconciliation

ADR-006 (`doc/adr/seeddata.md`) currently describes seed data using a
User -> Tracker/Project -> Task -> Subtask relationship.

Issue #4 requires subscription recommendation scenarios covering:

- Keep
- Downgrade
- Cancel
- Review
- Missing Usage
- Conflicting Evidence

These scenarios depend on the subscription, usage, recommendation, evidence,
and related entities being established by Issue #3.

Therefore, this document treats the Issue #4 scenarios as the expected
business scenarios and recommendation outcomes, while the exact database
relationships and fields will follow the schema established by Issue #3.

ADR-006 should be reconciled with the Issue #3 schema and Issue #4 requirements
before the final seed implementation is merged.

## Required Scenarios

### 1. Keep

A user has a subscription that remains useful and should be retained.

**Expected recommendation:** Keep

**Expected savings:** NGN 0

The seed data should contain sufficient evidence of continued usage/value to support the recommendation.

---

### 2. Downgrade

A user has a subscription that is still useful, but the current plan provides more capacity or features than the user's demonstrated usage requires.

**Expected recommendation:** Downgrade

**Expected savings:** The difference between the current plan cost and the recommended lower-tier plan cost.

The seed data should provide enough usage evidence to support the downgrade recommendation.

---

### 3. Cancel

A user has a subscription that should no longer be retained.

**Expected recommendation:** Cancel

**Expected savings:** The recurring cost that would be avoided by cancelling the subscription.

The seed data should contain evidence supporting cancellation.

---

### 4. Review

The available evidence does not provide enough confidence for an automatic keep, downgrade, or cancel recommendation.

**Expected recommendation:** Review

**Expected savings:** Not automatically determined.

The scenario should demonstrate that uncertain evidence results in a review recommendation rather than an unsupported action.

---

### 5. Missing Usage

A subscription exists, but the expected usage information is unavailable or incomplete.

**Expected recommendation:** Review

**Expected savings:** Not automatically determined.

Missing usage data must not be interpreted as proof that the subscription is unused.

---

### 6. Conflicting Evidence

The available evidence points in different directions. For example, usage may suggest cancellation while another record indicates recent or continued value.

**Expected recommendation:** Review

**Expected savings:** Not automatically determined.

Conflicting evidence must not produce an overconfident automatic recommendation.

## Determinism Requirements

Seed data must be deterministic.

Running the seed command multiple times against the same database must not create duplicate demo records or change the expected recommendation outcomes.

The scenarios should use stable identifiers and fixed demo values rather than randomly generated identities or timestamps.

## Testing Expectations

Tests should verify that:

1. All required scenarios can be loaded.
2. Running the seed operation repeatedly is idempotent.
3. Demo identities are fake and deterministic.
4. The agreed currency and locale are used.
5. Each scenario produces its documented expected recommendation.
6. Expected savings are deterministic where applicable.
7. Missing and conflicting evidence result in the expected `Review` outcome.