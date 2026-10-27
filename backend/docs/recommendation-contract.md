# Recommendation contract

Code: `app/domain/recommendations/contracts.py`

## Flow
1. AI output (untrusted) -> `parse_recommendation_draft(raw, catalog)` -> `RecommendationDraft`
2. Deterministic savings come from `app/domain/analysis/features.py`.
3. `RecommendationContract(draft, savings, versions)` combines them. Invalid combinations
   cannot be constructed.

## Draft fields (all required, unknown fields rejected)
`recommended_action` (keep | downgrade | cancel | review, exact match), `confidence`
(number 0..1, rounded half-even to 4 places), `uncertainty` (`level` low|medium|high and
`reason` token or null), `evidence_refs`, `missing_information`, `conflicting_information`
(lists of safe tokens, no duplicates, max 20), `rationale` (non-empty, max 2000 chars).
The draft has no savings field: the AI cannot supply money figures.

## Evidence
References may only point at ids in the `EvidenceCatalog`: supplied evidence ids, or
deterministically derived facts, which are prefixed `derived:`.
`RecommendationContract` requires the `EvidenceCatalog` and re-checks every evidence
reference in its own constructor, so grounding cannot be bypassed by constructing a draft
or contract directly.

## Consistency rules
- Any missing or conflicting information -> action must be `review`.
- `review` must state a reason (a gap or an uncertainty reason).
- keep, downgrade and cancel need evidence, uncertainty below `high`, and confidence of at
  least 0.6.
- cancel/downgrade: `is_positive_saving` must be true. keep: savings exactly zero.
  review: savings must be `None` (unknown, never zero).
- A failed calculation (currency mismatch, unsupported cadence) can never back an automatic
  action.
- Savings are estimates; verified savings live in `SavingsRecord`.

## Versions
`prompt_version` and `schema_version` are separate fields. Supported schema versions: `1.0`.

## Errors
Errors carry a stable code and a field name, never the offending value (ADR-004).