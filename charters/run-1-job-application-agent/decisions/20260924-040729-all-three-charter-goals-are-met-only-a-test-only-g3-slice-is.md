# All three charter goals are met; only a test-only G3 slice is scheduled

_Recorded 20260924-040729 by the NIGHTSHIFT planner._

## Context
Replayed on a read-only copy of the repo at 8417268 (2026-09-24). `uv run python -m evals.offline_eval --check-baseline` exits 0 and reports 1.000 on all five metrics against the frozen baseline: posting_shape 0.815, aggregator_drop 0.765, location 1.000, staleness 0.429, dedup 0.571. Nothing regressed. The default run writes evals/runs/offline/report.json, and the README documents every metric. `uv run pytest -q` gives 369 passed, 1 skipped (arming baseline 182/1). `uv run python run_mock_test.py` exits 0. On G3, the notification ledger (T-0024/T-0035), the Why: line (T-0010/T-0046), scan-error, notify-failed and missing-profile texts, and every bot_service _safe_send text are asserted by tests. A sweep of src/intake.py found one remaining gap: the unreadable-document, failed-download and 'please upload' replies from _document_or_text are only checked by substring or not at all, and never in the motivation or job-prefs states. The backlog is empty and there are no worker followups.

## Decision
Add one test-only task, T-0054 (G3/M3, tests/test_intake.py only, max_diff_lines 200, no dependencies), to close the last unasserted user-visible message path. No new G1 or G2 work: every G2 metric is already at 1.000, the ceiling, so any further triage work would be new scope rather than a measured improvement. Nothing parked is revived, because every parked item has been re-issued and merged or superseded. Assumptions: milestones M1-M3 are effectively done, but the op set has no way to mark a milestone status, so the roadmap is left as it is. The acceptance entries are shell commands because a prose acceptance made T-0048 fail its gate.

## Consequences
When T-0054 merges, every G1-G3 definition-of-done item has test evidence, and the planner should schedule only the charter's allowed idle work: tests, docs and small refactors within G1-G3. Because the harness is at its ceiling, any future G2 change has to add labelled corpus records under evals/fixtures that show a real failure before it can claim an improvement.
