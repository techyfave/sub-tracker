# ADR-003: AI Provider Boundary

**Status:** Accepted

## Context
The subscription tracker will use an AI provider to turn usage evidence into an **analysis**, and analyses into **recommendations**. Three candidate
providers were evaluated:

- **Gemini** — hosted, strong general capability, usage-based pricing.
- **Groq** — hosted, very low latency inference, limited model catalog,
  competitive pricing.
- **Jan** — local/self-hosted, strongest privacy story (no data leaves the
  host), but variable output quality and requires local compute the demo
  environment doesn't reliably have.

Previously this decision listed all three options without choosing one,
which left the analysis workflow (and ADR-002's `run-analysis` job)
unimplementable. This revision makes the decision and defines the
integration boundary.

## Options Considered
See the three providers above. Evaluated against MVP priorities: fast
integration, predictable hosted latency for a live demo, no dependency on
local GPU/CPU resources, and low operational overhead.

## Decision
- **MVP baseline provider: Groq.** It gives the lowest, most predictable
  latency for a live demo, requires no local compute, and its hosted API
  is simple to integrate.
- **Configuration** is entirely environment-driven, so the provider can be
  changed without a code deploy:
  - `AI_PROVIDER` — `groq` (default) | `gemini` | `jan`
  - `AI_API_KEY` — credential for the selected hosted provider (unused for
    `jan`)
  - `AI_MODEL` — model identifier for the selected provider
  - `AI_BASE_URL` — override endpoint (used for `jan`, which runs locally)
  - `AI_REQUEST_TIMEOUT_MS` — per-call timeout (default `30000`)
- A **provider-neutral application port** is defined; recommendation
  generation depends only on the structured invocation interface, never on
  a specific vendor SDK:

  ```
  interface AIProvider {
    generate_structured({
      system_prompt, context, output_schema, prompt_version, repair_feedback
    }): Promise<StructuredOutput>
  }
  ```

  The application builds a bounded context from allowlisted facts and omits
  user identifiers and contact data. Imported text is marked and treated as
  untrusted data. The model's strict output schema contains recommendation
  fields only; deterministic savings, prompt/schema versions, and action
  completion status are owned by the application, not the model.

- A generated result is not persistence-ready until structured validation,
  evidence ID/path/source grounding, and deterministic business-policy checks
  all pass. Invalid output and transient provider failures have separate
  classifications. Repair/retry is bounded to at most three calls, and
  downstream persistence must consume only the resulting validated contract.
- `FakeAIProvider` implements the same port for deterministic unit and
  contract tests. Provider adapters must map their own failures to the
  provider-neutral transient or permanent error types.

- `GroqAdapter` can implement `AIProvider` for the MVP. Additional adapters,
  such as `GeminiAdapter` or `JanAdapter`, may be added when those providers
  are supported. Selection happens in composition/wiring code based on
  `AI_PROVIDER`; domain and application modules never branch on provider
  identity.
- The `run-analysis` background job (ADR-002) calls `AIProvider`, not
  a specific vendor client.

## Consequences

### Positive
- Analysis and recommendation features are unblocked: there is one live
  default provider and a concrete configuration mechanism.
- Switching providers — including for cost, latency, or privacy reasons —
  is a config change plus (if needed) a new adapter, not a rewrite of
  analysis logic.
- Local/offline development or privacy-sensitive deployments can select
  `jan` without any application-code change.

### Negative
- The structured output contract must be kept provider-neutral, which means
  some provider-specific capabilities (e.g., a feature unique to one vendor's
  API) can't be exposed to callers without widening the port for everyone.
- Behavioral differences between providers (quality, latency, failure
  modes) are real and not fully hidden by the interface; adapters must
  normalize errors and timeouts consistently so callers see uniform
  failure semantics.
- Every supported provider adds an adapter and a provider-specific contract
  test suite that must be maintained.

## Architectural boundary

The AI integration remains infrastructure inside the **modular monolith**.
It does not introduce a separate AI service or allow provider SDK types to
cross into application or domain modules.
