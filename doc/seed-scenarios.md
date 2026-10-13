# Demo Seed Scenarios

This document defines the deterministic demo scenarios used by the backend seed data.

The seed data must be safe to run repeatedly and must produce the same expected records and recommendation outcomes each time.

## Currency and Locale

* Currency: Nigerian Naira (NGN)
* Locale: Nigeria
* All identities and account information are fictional demo data.
* No real personal information should be used in seed records.

## Schema and ADR-006

These scenarios define the expected business cases and recommendation
outcomes for the deterministic demo seed data.

The scenarios are implemented using the current PostgreSQL schema and the
relationships defined by ADR-006 (`doc/adr/006-seed-data-shape.md`).

The database implementation must preserve the expected behavior described
in this document. Changes to database entities or relationships must not
change the documented recommendation outcomes without updating the
corresponding tests and documentation.

## Required Scenarios

### 1. Keep

A user has a subscription that remains useful and should be retained.

**Expected recommendation:** Keep

**Expected action:** No cancellation or downgrade action.

**Expected monthly savings:** NGN 0

**Expected annual savings:** NGN 0

The seed data should contain sufficient evidence of continued usage/value to
support the recommendation.

### 2. Downgrade

A user has a subscription that is still useful, but the current plan provides
more capacity or features than the user's demonstrated usage requires.

**Expected recommendation:** Downgrade

**Expected action:** Downgrade to the lower-tier plan.

**Expected monthly savings:** NGN 4,000

**Expected annual savings:** NGN 48,000

**Savings status:** Estimated until the downgrade is executed and confirmed
by post-change billing evidence.

The seed data should provide enough usage evidence to support the downgrade
recommendation. A savings record marked as verified must not be created
without completed action evidence and confirming post-change billing data.

### 3. Cancel

A user has a subscription that should no longer be retained.

**Expected recommendation:** Cancel

**Expected action:** Cancel the subscription.

**Expected monthly savings:** The seeded recurring subscription cost.

**Expected annual savings:** The seeded recurring subscription cost multiplied
by 12.

The seed data should contain evidence supporting cancellation.

### 4. Review

The available evidence does not provide enough confidence for an automatic
keep, downgrade, or cancel recommendation.

**Expected recommendation:** Review

**Expected action:** No automatic subscription-changing action.

**Expected monthly savings:** Uncertain

**Expected annual savings:** Uncertain

The scenario should demonstrate that uncertain evidence results in a review
recommendation rather than an unsupported action.

### 5. Missing Usage

A subscription exists, but the expected usage information is unavailable or
incomplete.

**Expected recommendation:** Review

**Expected action:** No automatic subscription-changing action.

**Expected monthly savings:** Uncertain

**Expected annual savings:** Uncertain

Missing usage data must not be interpreted as proof that the subscription is
unused.

The seed data and tests must distinguish missing/unknown usage from confirmed
zero usage.

### 6. Conflicting Evidence

The available evidence points in different directions. For example, usage may
suggest cancellation while another record indicates recent or continued value.

**Expected recommendation:** Review

**Expected action:** No automatic subscription-changing action.

**Expected monthly savings:** Uncertain

**Expected annual savings:** Uncertain

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
