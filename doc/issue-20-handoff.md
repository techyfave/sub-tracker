# Issue #20 handoff

Implementation owner: techyfave. PR #40 remains draft until fresh-contributor validation and
future endpoint dependencies are complete. No successful human walkthrough is fabricated.

## Placeholders requiring a human

| Placeholder | Replace with |
|---|---|
| FRESH_CONTRIBUTOR_HANDLE | GitHub handle of someone other than the runbook author who follows it from a clean clone |
| WALKTHROUGH_DATE | Actual date that contributor performs the walkthrough |
| WALKTHROUGH_COMMIT | Full commit SHA checked out, from `git rev-parse HEAD` |
| WALKTHROUGH_ENVIRONMENT | Their OS and actual Python/uv/Git/Docker/Compose versions |
| WALKTHROUGH_RESULTS | Commands, expected/actual outputs and corrections for Compose health, migrations, two seeds/counts, login/protected request, worker probe and PostgreSQL/Redis tests |

Record these in contributor-walkthrough.md, preserving the earlier blocked attempt as history.
The remaining service URLs use local Compose defaults, not production credentials.
`JOB_ID_FROM_PROBE` in the runbook is a runtime substitution: use the printed probe UUID.
No personal password, live access token, provider secret or private URL belongs in this file.

## Dependency handoff

Issues #13/#15/#16/#17 need endpoint examples once their actual implementations are merged.
These are pending work, not values the user should guess or replace. Issue #11 likewise owns
the final fake/provider execution configuration. Keep #20 open until these contracts and the
fresh-contributor evidence are complete.
