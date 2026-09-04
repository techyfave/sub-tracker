# Open Decisions

These decisions must be made by the relevant phase rather than silently assumed.

## Before Phase 0 ends

1. Initial target market, currency, and locale.
2. Whether participant prototypes live in this monorepo or separate repositories.
3. Exact prototype duration and presentation format.
4. Initial AI provider and model constraints for fair comparison.
5. Evaluation threshold and definition of a critical failure.
6. Whether every prototype must use FastAPI or may use CLI/notebook interfaces.

## Before shared product features begin

1. Shared frontend technology.
2. Authentication approach.
3. Background-job library based on agreed job requirements.
4. Baseline AI provider and whether fallback/multi-provider support is necessary.
5. Prompt and response retention policy.
6. Seed/demo-data shape and supported currency behavior.

## Before sandbox integration

1. Transaction-data provider and target geography.
2. Provider consent and revocation requirements.
3. Webhook security and reconciliation behavior.
4. Data freshness expectations.

## Before pilot

1. Deployment platform.
2. Secret management and encryption approach.
3. Retention, export, deletion, and backup policies.
4. Monitoring and incident ownership.
5. Legal and privacy review requirements.

The current FastAPI scaffold does not settle these product decisions.
