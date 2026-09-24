# Close G3's 'state why a job matched' gap; treat G1 and G2 as met

_Recorded 20260923-231439 by the NIGHTSHIFT planner._

## Context
The backlog was empty. On a copy of the repo at ee6a912, `uv run python -m evals.offline_eval` exits 0 and writes a report. Every metric in its TOTAL row is 1.000. The arming baseline in evals/baseline.json is posting_shape 0.815, aggregator_drop 0.765, location_match 1.000, staleness 0.429, dedup 0.571. Every metric is at or above baseline, so none regressed. README documents all five metrics. `uv run pytest -q` gives 356 passed, 1 skipped. G3's never-notify-twice, scan-error and send-boundary items are done (T-0024, T-0032 to T-0035, T-0045). One gap remains: src/notifier.py drops the 'Why:' line when the evaluator's reason is blank, and a test currently asserts that behaviour.

## Decision
Schedule one small G3 task, T-0046, limited to src/notifier.py and tests/test_notifier.py. It adds an honest fallback 'Why:' line so every job message states why it matched. It does not touch the LLM prompts. No new G1 or G2 work is scheduled because both definitions of done are met on the current harness. Assumption (conservative): the metric table at 1.000 on the committed corpus satisfies G2, so extending the corpus again would be new scope rather than required work.

## Consequences
Once T-0046 merges, all three goals appear to meet their definitions of done. Later passes should schedule only the charter's allowed idle work (tests, documentation and small refactors within G1–G3), and only in response to worker followups or regressions. The old parked tasks stay parked: their re-issues have merged.
