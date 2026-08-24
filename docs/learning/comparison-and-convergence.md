# Phase 2: Prototype Comparison and Convergence

## Purpose

The seven prototypes are experiments, not competing complete products. The team runs every prototype against the same cases, discusses failures openly, and combines the best supported decisions into one shared specification.

## Demonstration process

1. Freeze the shared evaluation dataset before presentations.
2. Run each prototype on the same cases.
3. Collect machine-readable results and cost/latency information.
4. Demonstrate successful and failed cases.
5. Score using the previously agreed rubric.
6. Discuss architecture and learning notes.
7. Record shared decisions as architecture decision records.

## Suggested scorecard

| Dimension | Weight |
|---|---:|
| Recommendation correctness | 25% |
| Factual grounding | 20% |
| Savings correctness | 15% |
| Uncertainty handling | 10% |
| Structured-output reliability | 10% |
| Safety and approval behavior | 10% |
| Explanation quality | 5% |
| Maintainability and clarity | 5% |

Weights must be approved before results are reviewed.

## Review questions

- Which schema expressed evidence and uncertainty best?
- Which prompt generalized rather than memorized examples?
- Which solution overused the model?
- Which tools were stable and testable?
- Who handled missing evidence honestly?
- Which errors could cause the most user harm?
- Were confidence values meaningful?
- How did retries and provider failures behave?
- Which cases exposed hidden assumptions?
- Which approach will be easiest to evaluate and operate?

## Required outputs

- shared domain vocabulary;
- canonical input contract;
- versioned recommendation schema;
- selected deterministic tools;
- baseline prompt and prompt-management approach;
- versioned evaluation dataset and scoring runner;
- architecture decisions with evidence;
- shared-system backlog.

## Exit criterion

The team must be able to defend the shared design using prototype results. The shared system is not simply the most polished participant prototype renamed.

Only after this exit criterion is met should the team implement product features in the shared FastAPI application.
