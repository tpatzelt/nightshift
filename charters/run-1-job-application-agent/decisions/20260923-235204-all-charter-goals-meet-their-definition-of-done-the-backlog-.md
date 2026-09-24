# All charter goals meet their definition of done; the backlog stays empty and no idle work is scheduled

_Recorded 20260923-235204 by the NIGHTSHIFT planner._

## Context
The backlog had no ready tasks. I checked the tree in a scratch copy of /repo/job-application-agent at cac026c, because the mount is read-only. `python -m evals.offline_eval` exited 0, printed the per-metric table and wrote evals/runs/offline/report.json. TOTAL over 58 records: posting_shape_rate, aggregator_drop_rate, location_match_rate, staleness_detection_rate and dedup_rate are all 1.000. The arming baseline in evals/baseline.json (rev b6da8dd) is 0.815, 0.765, 1.000, 0.429 and 0.571. `--check-baseline` exits 0. `uv run pytest -q` gives 362 passed, 1 skipped, up from 182 passed and 1 skipped at arming. `uv run python run_mock_test.py` passes. README documents each metric and how to run the harness (README.md:183-207), and the harness has tests in tests/test_offline_eval.py, test_offline_metrics.py and test_offline_baseline.py. G3's items landed as T-0024 (durable ledger of delivered postings), T-0035 (repeats within one list), T-0032/T-0033/T-0034/T-0045 (asserting each message path at the send boundary), T-0046 (the Why: line) and T-0049 (delivery-failure text), with README coverage in T-0050. Every parked task has been superseded by a merged re-issue. No worker followups are pending.

## Decision
Add no tasks and do not revive any parked task. G1, G2 and G3 all meet the charter's definition of done on the current tree. Idle work is optional under the charter. Every metric is already at 1.000 and the charter forbids new work and changes not needed by a task, so the most conservative choice is to leave the backlog empty rather than create work to fill it. Assumptions: (1) the milestone status in ROADMAP is stale bookkeeping, and there is no op for marking a milestone done, so I did not touch it. (2) My runs happened in a scratch copy of the repo under /tmp. The report and venv were written there, not to the read-only mount.

## Consequences
The runners stay idle until the charter or tree changes. If a later change regresses a metric, `--check-baseline` will catch it, and the next planning pass should then schedule a fix under G2. If a new user-visible message path appears without a test, schedule a test-only task under G3 as allowed idle work.
