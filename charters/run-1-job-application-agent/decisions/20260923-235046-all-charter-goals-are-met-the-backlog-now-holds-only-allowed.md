# All charter goals are met; the backlog now holds only allowed idle work

_Recorded 20260923-235046 by the NIGHTSHIFT planner._

## Context
The backlog was empty with no worker followups. I replayed a copy of the current tree. `uv run python -m evals.offline_eval` exits 0, prints the per-metric table, writes evals/runs/offline/report.json, and shows TOTAL 1.000 on every metric (arming baseline: posting_shape 0.815, aggregator_drop 0.765, staleness 0.429, dedup 0.571, location 1.000). The README documents each metric and how to run the harness (README.md:183-207). `uv run pytest -q` gives 362 passed, 1 skipped, and run_mock_test.py passes. G3 work has merged: the delivery ledger (T-0024), in-list dedup (T-0035), a Why: line on every job message (T-0046), notify-failure and scan-error texts (T-0032, T-0049), and assertions on the send-boundary, intake and chunking text (T-0033, T-0034, T-0045). Every remaining parked task was superseded by one of those, and none should be revived.

## Decision
Treat G1, G2 and G3 as done and add no new feature work. Schedule one idle-work task (T-0051): a test that pins the achieved G2 scores on the committed corpus, because the only existing guard compares against the much lower arming baseline and would not catch a partial regression. Assumptions: (1) the '1.000 on all metrics' state is the intended G2 result, and evals/baseline.json stays the untouched arming baseline; (2) the plan has no op for marking milestones done, so M1-M3 remain 'planned' in the roadmap text even though their exit criteria are met; (3) I made no live API calls, because the idle work doesn't need them.

## Consequences
Any future change that lowers a quality metric below today's level fails the default test suite, not just --check-baseline. If a later corpus extension legitimately changes totals, T-0051's exact-value assertions will need updating in the same change. Once T-0051 merges, the backlog will be empty again, and later passes should add only tests, documentation or small refactors within G1-G3.
