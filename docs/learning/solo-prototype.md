# Phase 1: Solo AI Prototype Guide

## Why this comes first

All seven participants must first experience the core AI-system workflow themselves. The team should not assign AI work to two people while everyone else builds ordinary CRUD features.

Phase 1 starts only after Phase 0 aligns the team on shared schemas, cases, rules, and demonstration format.

## Shared task

> Given a subscription, recent charges, known usage, user preferences, and available plan alternatives, produce a validated recommendation with evidence, uncertainty, confidence, and deterministic savings.

Each participant independently chooses their prompting and orchestration approach. All participants use the same inputs and evaluation cases.

## Required input

- subscription and provider;
- price, currency, and billing interval;
- recent transaction occurrences;
- known usage events or an explicit unknown state;
- renewal date where known;
- user-stated importance and preferences;
- cheaper plan alternatives where known;
- analysis date.

## Required structured output

- `action`: `keep`, `downgrade`, `cancel`, or `review`;
- concise reason;
- evidence used, with source references;
- missing or conflicting evidence;
- confidence score or band;
- deterministic monthly and annual savings;
- follow-up question when evidence is insufficient;
- explicit approval requirement;
- schema, prompt, and model references.

## Required deterministic tools

At minimum:

1. `calculate_savings` normalizes billing periods and computes savings.
2. `summarize_usage` computes usage frequency, recency, or an unknown state.

Optional tools include duplicate detection, plan comparison, renewal urgency, and transaction consistency checks.

The model must not perform authoritative money calculations or invent missing usage.

## Required cases

- frequently used and clearly valuable subscription;
- unused subscription with reliable evidence;
- unknown usage;
- recently paid annual plan;
- duplicate services;
- cheaper plan available;
- low-use but user-designated essential service;
- inconsistent transaction amount;
- trial about to renew;
- savings edge case;
- untrusted instructions embedded in imported text;
- malformed model output.

## Minimum implementation

Each prototype contains:

- Pydantic input and output models;
- at least one model call;
- deterministic tools;
- structured-output validation;
- bounded retry or graceful failure behavior;
- a CLI, notebook, or one small FastAPI endpoint;
- automated evaluation execution;
- a learning report.

Do not build authentication, a database-backed product, a polished interface, or real integrations in this phase.

## Learning report

Each participant records:

- architecture and approach;
- prompt iterations;
- reasons for schema fields;
- deterministic versus model responsibilities;
- failures discovered;
- evaluation results;
- changes they would make;
- remaining questions.

## Completion criteria

A participant completes Phase 1 only if they can explain:

- why structured output is necessary;
- how Pydantic validation protects the system;
- model reasoning versus deterministic business logic;
- tool calling;
- grounding and hallucination detection;
- evaluation design;
- provider and malformed-output failure behavior.

Working code without this understanding is not completion.

## Expected Phase 0 artifacts

Before prototyping, the team will add:

```text
prototypes/
|-- shared/
|   |-- README.md
|   |-- schemas/
|   |-- cases/
|   `-- rubric/
|-- participant-01/
|-- participant-02/
|-- participant-03/
|-- participant-04/
|-- participant-05/
|-- participant-06/
`-- participant-07/
```

Those files are the next planned deliverable; they are not silently defined by the shared FastAPI scaffold.
