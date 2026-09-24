# All charter goals met; schedule G3 idle hardening only

_Recorded 20260923-175315 by the NIGHTSHIFT planner._

## Context
I ran `python -m evals.offline_eval` against the read-only tree. It prints TOTAL posting_shape 0.889 (baseline 0.815), aggregator_drop 0.882 (0.765), location 1.000 (1.000), staleness 1.000 (0.429) and dedup 1.000 (0.571), so G2 is met. The only crash was the report write, which failed because the mount is read-only. G1's harness, tests and README section exist (T-0005, T-0018, T-0026, T-0027). G3's items are merged: T-0010 (the why-matched line), T-0016 (a failed scan says what failed), T-0024 (the ledger), and T-0032, T-0033 and T-0034, which split parked T-0031. Backlog is empty and there are no followups.

## Decision
Schedule no new goal work. Add one idle task, T-0035, inside G3. It makes 'never notify twice' hold at the notifier itself, by deduplicating a single results list by canonical URL, instead of relying on the orchestrator's seen_urls. The remaining project-manager-berlin headroom (posting_shape 0.500, aggregator_drop 0.750) is left alone: G2's definition of done is already met, and more heuristic work would be new work, not idle work. Parked tasks T-0007 to T-0031 stay parked. They were all superseded by merged re-issues. Assumptions: (1) the harness replays evals/fixtures rather than evals/runs/**, and I treat that as meeting G1 because the definition of done, which requires only the command, table, report path, tests and README, is met; (2) I could not run uv run pytest here because the mount is read-only, so I rely on the merge gates' record for the suite state.

## Consequences
The backlog holds one small, test-first, G3-only task, capped at 120 diff lines. It touches only src/notifier.py and one test file, and protects the orchestrator, the evals and the other G3 modules. When it merges, the backlog will be empty again, and later passes should add only tests or documentation strictly inside G1–G3.
