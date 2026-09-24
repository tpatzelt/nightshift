# All three goals are met; schedule only test-only idle work for G3's remaining substring-only intake assertions

_Recorded 20260924-091232 by the NIGHTSHIFT planner._

## Context
The backlog is empty. evals/baseline.json holds the arming baseline: posting_shape 0.815, aggregator_drop 0.765, staleness 0.429, dedup 0.571. T-0063 pins the achieved totals at 1.0 for every metric, so G1 and G2 meet their definition of done. For G3, T-0049 through T-0067 covered the never-notify-twice ledger, delivery and scan-failure text, and exact-text assertions for most message paths. A read of src/intake.py against tests/test_intake.py and tests/test_bot_service.py found a few mid-setup replies that are still asserted only by substring: the motivation-received reply, the job-prefs prompt, and the /status and /start resume prompts for each setup step.

## Decision
Add one test-only task, T-0068, restricted to tests/test_intake.py, that pins those replies exactly. It adds no new behaviour and changes nothing in src/. Worker followups were empty, so there was nothing new to adopt. The parked tasks have all been superseded by re-issued tasks that have since merged, so none are revived. Assumption recorded: the current reply wording is intended, and any wording that looks wrong is reported as a followup instead of being changed.

## Consequences
Once T-0068 merges, every intake reply path has an exact-text assertion. Further planner passes should schedule only the charter's allowed idle work (tests, documentation and small refactors within G1–G3), or nothing at all, rather than inventing new scope.
