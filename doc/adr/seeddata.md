# ADR-006: Seed Data Shape


The `sub-tracker` MVP requires predictable and reproducible data for local
development, automated testing, API development, and demonstrations.

Without an agreed seed-data structure, individual developers may createdifferent users, trackers, tasks, subtasks, statuses, or other records. This
can result in inconsistent development environments and make it difficult toreproduce bugs or demonstrate the same application workflow across
environments.

The seed-data decision must therefore define the minimum set of records and relationships required to represent the core `sub-tracker` workflow. The seed dataset should reflect the actual task-tracking domain rather than
introducing data structures belonging to unrelated projects.

The seed data must also remain compatible with the modular-monolith
architecture defined by the backend ADRs.

## Decision Drivers

The following factors drive the decision:

1. Reproducibility across development environments.
2. Simplicity of the MVP dataset.
3. Representation of the core `sub-tracker` workflow.
4. Stable relationships between records.
5. Easy database initialization.
6. Compatibility with automated tests.
7. Safe repeatability.
8. Avoidance of unnecessary demo data.
9. Clear separation between development data and production data.

## Options Considered

### Option 1: No predefined seed data

Developers manually create records whenever they need data.

#### Advantages

* No seed implementation required.
* Developers can create exactly the data they need.

#### Disadvantages

* Every developer starts with a different dataset.
* API testing becomes inconsistent.
* Demonstrations become difficult to reproduce.
* Bugs depending on specific relationships are harder to reproduce.
* New developers have a less predictable development environment.

This option is rejected.

---

### Option 2: Large realistic demo dataset

Create a large dataset containing many users, trackers, tasks, subtasks,
statuses, and other records.

#### Advantages

* Provides a realistic-looking environment.
* Useful for demonstrating larger datasets.
* Can expose performance issues early.

#### Disadvantages

* More difficult to maintain.
* More difficult to understand.
* Slower database initialization.
* Creates unnecessary coupling between tests and demo data.
* Increases the likelihood of stale or invalid seed records.

This option is rejected for the MVP.

---

### Option 3: Deterministic minimal seed dataset

Create a small, deterministic dataset that represents the core application
workflow and its important relationships.

#### Advantages

* Easy to understand.
* Reproducible.
* Fast to initialize.
* Suitable for demonstrations.
* Suitable as a development baseline.
* Easier to maintain as the domain evolves.

#### Disadvantages

* Does not represent every possible real-world scenario.
* Must be updated when domain requirements change.
* Developers may still need specialized fixtures for complex tests.

This option is selected.

## Decision

The MVP will use **deterministic, minimal, relationally valid seed data**.

The seed dataset will represent the core `sub-tracker` workflow using the
actual domain entities defined by the application.

The seed data should be sufficient to demonstrate the lifecycle of tracked
work without attempting to reproduce a production-sized dataset.

The seed dataset should be safe to recreate in local development and
development/demo environments.

## Core Seed Shape

The conceptual seed relationship is:

```
User
  |
  +-- Tracker / Project
          |
          +-- Task
                |
                +-- Subtask
```

Where the implementation uses different names for these concepts, the
canonical terminology defined in the API/domain terminology document takes
precedence.

The important relationship is that tracked work belongs to an appropriate
parent context and subtasks belong to their parent task.

## User

The seed dataset should contain at least one deterministic development user.

The user exists to demonstrate ownership and authentication-related
workflows.

Conceptually:

```
Demo User
```

The seeded account must be clearly identified as development/demo data.

If authentication uses credentials, seeded credentials must only be valid in
development/test environments.

Production deployments must not automatically receive the development seed
user or its credentials.

## Tracker / Project

The seed dataset should contain at least one tracker/project/workspace
record, using the canonical domain term selected by the API/domain
terminology ADR.

The record should be owned by or associated with the seeded development
user.

Example conceptual data:

```
Backend MVP Tracker
```

The tracker should provide the parent context in which tasks and subtasks can
be demonstrated.

## Task

The seed dataset should contain a small number of representative tasks.

At minimum, the dataset should demonstrate tasks in different lifecycle
states where those states are part of the agreed domain model.

For example:

```
Backend authentication
API contract documentation
Database setup
```

The exact task names are not architecturally significant. What matters is
that the records are valid according to the task model.

Each task should belong to the appropriate tracker/project context.

## Subtask

The seed dataset should contain representative subtasks associated with at
least one parent task.

For example:

```
Task:
    Backend authentication

Subtasks:
    Define authentication contract
    Implement authentication middleware
    Add authentication tests
```

This demonstrates the core purpose of `sub-tracker`: breaking larger pieces
of work into smaller trackable units.

Subtasks must reference valid parent tasks.

A subtask must not exist without the parent relationship required by the
domain model.

## Status Data

If task/subtask statuses are represented as persisted domain records, the
seed dataset should include the minimum valid status set required by the
application.

For example, where these are the agreed statuses:

```
TODO
IN_PROGRESS
DONE
```

The seed data should include records that demonstrate the lifecycle without
creating unnecessary status variants.

If statuses are represented as application enums rather than database
records, the seed process should use the canonical enum values instead.

The ADR does not mandate whether statuses are implemented as enums or
database records; that decision belongs to the relevant domain/API contract.

## Optional Assignment Data

If the MVP supports assigning tasks or subtasks to users, the seed dataset
may associate the demo tasks with the deterministic development user.

For example:

```
Demo User
    |
    +-- Backend authentication
    +-- API contract documentation
```

Assignment data should only be seeded if assignment is part of the agreed
MVP domain.

The seed dataset must not introduce assignment functionality merely for the
purpose of making the demo data look realistic.

## Labels, Tags, or Metadata

If labels, tags, priorities, or similar metadata are part of the MVP domain,
the seed dataset may contain a small number of representative values.

For example:

```
Priority:
    High
    Medium
```

or:

```
Labels:
    backend
    documentation
    testing
```

These values must remain minimal and deterministic.

If a feature is not part of the agreed MVP domain, it must not be introduced
solely as seed data.

## Determinism

Seed records must have predictable relationships.

Where stable identifiers are useful for development, documentation, or
integration tests, deterministic IDs may be used.

The seed process must not depend on:

* Random values that tests must discover dynamically.
* Current timestamps when they affect test assertions.
* External APIs.
* External task-management services.
* External authentication providers.
* External AI providers.
* External services that are not required to initialize the application.

Dates and timestamps that are required by the domain should be deterministic
where possible.

## Idempotency

The seed operation must be safe to run repeatedly.

Running the seed process multiple times must not create uncontrolled duplicate
users, trackers, tasks, subtasks, or other records.

The implementation should use one of the following strategies:

1. Detect existing deterministic records and avoid duplication.
2. Recreate the development dataset.
3. Use another database-supported idempotent mechanism.

The exact implementation mechanism is left to the database/infrastructure
layer.

The important requirement is that repeated seeding produces a predictable
result.

## Referential Integrity

Seed data must respect the same relationships as production data.

For example:

```
User
  |
  +-- Tracker
         |
         +-- Task
                |
                +-- Subtask
```

A task must reference an existing parent tracker/project where required.

A subtask must reference an existing parent task.

An assigned user must exist before an assignment references that user.

Seed data must not bypass foreign-key constraints or domain invariants simply
to simplify database initialization.

## Seed Data and Domain Rules

Seed records must satisfy the same basic validation and domain rules expected
from normal application data.

The seed process must not create records that the public API itself would
consider invalid.

This provides an additional verification that the domain model and database
constraints are aligned.

## Environment Scope

Seed data is intended for:

* Local development.
* Development environments.
* Demo environments.
* Automated integration testing where appropriate.

Production environments must not automatically execute development seed
operations.

If production requires initial/reference data, that data should be defined
separately from development/demo seed data.

## Test Fixtures vs Seed Data

Seed data and test fixtures are different concepts.

### Seed data

Seed data provides a predictable baseline environment for developers and
demonstrations.

### Test fixtures

Test fixtures provide data required for a specific test scenario.

Tests should not depend on unrelated seed records.

For example, a test for deleting a subtask should create or reference only
the records required to test deletion rather than depending on an unrelated
demo task.

This keeps tests isolated and prevents changes to demo data from breaking
unrelated tests.

## Recommended MVP Dataset

The minimum recommended seed dataset is:

### Users

* 1 deterministic development/demo user.

### Tracker/Project

* 1 tracker/project owned by the demo user.

### Tasks

* 2–3 representative tasks.

### Subtasks

* 2–4 subtasks distributed across the seeded tasks.

### Statuses

* The minimum canonical statuses required by the MVP.

### Optional metadata

* Minimal priorities, labels, or assignments only where those concepts are
  already part of the MVP domain.

The exact number is intentionally kept small.

The goal is to demonstrate relationships, not to simulate a production
database.

## Example Conceptual Dataset

The following is an example of the intended shape, not a mandatory literal
database schema:

```
User
└── Demo User
    │
    └── Backend MVP Tracker
        │
        ├── Task: Authentication
        │   ├── Subtask: Define authentication contract
        │   └── Subtask: Add authentication tests
        │
        ├── Task: API Documentation
        │   ├── Subtask: Document API terminology
        │   └── Subtask: Document endpoint contracts
        │
        └── Task: Database Setup
            └── Subtask: Create initial database schema
```

This structure demonstrates the hierarchical nature of the tracker without
introducing unrelated entities.

## Stable Development Data

Where practical, the seed process should use recognizable deterministic
values.

For example:

```
User:
    demo@example.invalid

Tracker:
    Backend MVP Tracker

Task:
    Authentication

Subtask:
    Define authentication contract
```

The example email above is illustrative only. The implementation should use
the repository's agreed development-user convention.

Development credentials must never be reused as real credentials.

## Data Volume

The MVP seed dataset should remain intentionally small.

The purpose of seed data is to provide:

* A valid starting state.
* A reproducible development environment.
* A useful demonstration.
* A foundation for manual API testing.

It is not intended to benchmark database performance or represent production
scale.

Large-volume performance testing should use dedicated test-data generation
tools or fixtures.

## Consequences

### Positive

* Every developer can initialize a predictable environment.
* API demonstrations become reproducible.
* Task/subtask relationships are immediately available.
* Integration testing becomes easier.
* Bugs involving parent/child task relationships are easier to reproduce.
* New developers can understand the domain quickly from the seed dataset.
* The dataset remains small enough to maintain.

### Negative

* Seed data must be updated when the domain model changes.
* The seed dataset cannot represent every possible task-management scenario.
* Developers still need specialized fixtures for complex tests.
* Development seed data requires protection from accidental production use.

## Data Quality Requirements

The seed dataset must satisfy:

* Referential integrity.
* Domain validation.
* Required-field constraints.
* Ownership rules.
* Status constraints.
* Parent/child relationships.
* Any uniqueness constraints defined by the domain.

For example:

* Every task must belong to its required parent context.
* Every subtask must reference a valid parent task.
* Every assigned user must exist.
* Every status must be a valid canonical status.
* Every seeded record must satisfy required validation rules.

## Architectural Constraint

Seed data is a development/infrastructure concern within the **modular
monolith**.

The seed process must not introduce a separate data service.

The application should continue to use the same domain models, repositories,
validation rules, and persistence mechanisms used by the normal application.

The seed mechanism should initialize the database through appropriate
application/database infrastructure rather than directly creating an
alternative data model.

## Relationship to Other ADRs

This decision depends on the terminology defined by the backend API/domain
documentation.

Seed data must use the canonical names for:

* Users.
* Trackers/projects.
* Tasks.
* Subtasks.
* Statuses.
* Assignments.
* Other domain entities.

If another ADR changes the domain model, this ADR must be reviewed to ensure
the seed dataset still represents the canonical model.

## Future Considerations

Future versions may introduce:

* Larger demo datasets.
* Multiple development users.
* Multiple trackers/projects.
* More complex task hierarchies.
* Scenario-specific fixtures.
* Synthetic high-volume datasets.
* Importing sample data from external systems.

These should remain separate from the minimal MVP seed dataset unless they
become necessary for the core application.

## Implementation Impact

The implementation must provide:

1. A documented seed command/process.
2. A deterministic development/demo user.
3. A deterministic tracker/project using the canonical domain terminology.
4. Representative tasks.
5. Representative subtasks.
6. Required canonical status data.
7. Valid parent/child relationships.
8. Safe repeatability/idempotency.
9. Environment protection against accidental production seeding.
10. Documentation explaining how developers initialize the seed data.

## Acceptance Criteria

This ADR is considered implemented when:

* A developer can initialize the database with one documented command/process.
* The resulting dataset is deterministic.
* A demo user exists in development environments.
* A tracker/project exists for the demo user.
* Representative tasks exist.
* Representative subtasks exist.
* Parent/child relationships are valid.
* Status values follow the canonical domain contract.
* Running the seed process repeatedly does not create uncontrolled duplicates.
* Production cannot accidentally receive development seed credentials/data.
* The seed structure matches the terminology defined by the backend
  documentation.
