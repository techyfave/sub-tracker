# Shared-System Architecture

## Style

The shared MVP uses a modular monolith with a separate frontend and background worker. It provides realistic boundaries without premature microservices.

```mermaid
flowchart TB
    Browser --> Frontend[Thin web frontend]
    Frontend --> API[FastAPI API]
    API --> Application[Application services]
    Application --> Domain[Domain logic]
    Application --> Repositories[Repository interfaces]
    Repositories --> Postgres[(PostgreSQL)]
    API --> Redis[(Redis)]
    Worker[Python worker] --> Redis
    Worker --> Application
    Application --> AI[AI provider adapter]
    Application --> Data[Transaction and usage adapters]
    Application --> Actions[Simulation and action adapters]
    API --> Telemetry[Logs, metrics, traces]
    Worker --> Telemetry
```

Redis and a worker become active shared-system dependencies only when asynchronous analysis is implemented. The initial scaffold does not fake worker behavior.

## Responsibilities

### Frontend

- subscription and usage management;
- analysis progress and recommendation inbox;
- evidence, uncertainty, and savings presentation;
- follow-up conversation;
- approval, rejection, correction, and postpone controls;
- action and savings history.

### FastAPI

- versioned HTTP API and OpenAPI documentation;
- authentication and authorization;
- input validation and consistent errors;
- idempotency and rate-limit boundaries;
- application-service orchestration;
- health and readiness checks.

### Domain and application

- domain invariants and state machines;
- use-case orchestration and transaction boundaries;
- savings rules;
- approval policy;
- repository and provider interfaces;
- audit-event creation.

### Agent service

- bounded context construction;
- prompt and schema version selection;
- tool calls;
- model invocation;
- structured-output validation;
- grounding, policy, and quality checks;
- bounded repair and retry behavior.

### Worker

- long-running analysis;
- scheduled reanalysis;
- simulated or provider actions;
- notifications;
- retries and dead-letter behavior.

## Analysis flow

```mermaid
flowchart LR
    A[Subscriptions, transactions, usage, preferences] --> B[Normalize and validate]
    B --> C[Calculate deterministic features]
    C --> D[Build bounded model context]
    D --> E[Structured model call]
    E --> F{Schema valid?}
    F -->|No| G[Bounded repair or retry]
    G --> E
    F -->|Yes| H[Grounding and business checks]
    H --> I{Pass?}
    I -->|No| J[Fail or request review]
    I -->|Yes| K[Persist recommendation and evidence]
    K --> L[Present conversationally]
```

## Approval sequence

```mermaid
sequenceDiagram
    actor User
    participant UI
    participant API as FastAPI
    participant DB as PostgreSQL
    participant Queue
    participant Worker
    participant Agent
    participant Action

    User->>UI: Request analysis
    UI->>API: POST /api/v1/analyses
    API->>DB: Store queued job
    API->>Queue: Enqueue analysis
    API-->>UI: 202 + analysis ID
    Worker->>Agent: Analyze normalized data
    Agent->>DB: Store validated recommendation
    UI->>API: Retrieve completed analysis
    API-->>UI: Recommendation and evidence
    User->>UI: Approve exact recommendation version
    UI->>API: Submit decision
    API->>DB: Record explicit approval
    API->>Queue: Enqueue action
    Worker->>Action: Execute simulation/provider action
    Action-->>Worker: Result
    Worker->>DB: Store action, audit event, and savings
```

## Failure principles

- Retries are bounded and classified.
- Incomplete evidence differs from provider failure.
- Actions use idempotency keys.
- Approval is tied to an immutable recommendation version.
- Redis is not the source of truth for domain state.
- The model cannot mark an action successful.
