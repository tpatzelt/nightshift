# All three charter goals meet their definition of done; the backlog now holds only allowed idle work

_Recorded 20260923-234504 by the NIGHTSHIFT planner._

## Context
The backlog was empty. I checked the current tree in a scratch copy of /repo/job-application-agent. `uv run python -m evals.offline_eval` exits 0, prints the per-metric table, writes evals/runs/offline/report.json, and shows TOTAL posting_shape_rate, aggregator_drop_rate, location_match_rate, staleness_detection_rate and dedup_rate all at 1.000. The arming baseline in evals/baseline.json (rev b6da8dd) is 0.815 / 0.765 / 1.000 / 0.429 / 0.571, so every metric improved or held and none regressed. The README documents each metric. `uv run pytest -q` gives 362 passed, 1 skipped, and `uv run python run_mock_test.py` passes. G3 is covered: the 'Why:' line is always present (T-0046), the notification ledger and in-list dedup stop repeat notifications (T-0024, T-0035), scan failures and delivery failures produce text naming the cause (T-0032, T-0049), and the send-boundary replies are asserted (T-0032/33/34/45). A grep for untested user-visible strings found one gap: the intake reply '⚠️ {exc}\n\nPlease try another file.' (src/intake.py:322) and the 'File too large' TelegramError text behind it are never asserted.

## Decision
Add one test-only task, T-0051, for G3/M3, to close that last gap. It changes no production code. Every parked task stays parked: each one is either superseded by merged work or has been re-issued and merged under a later ID. No new milestones and no new goals. Assumptions recorded: (a) evals/runs/** does not exist in the repo, and the recorded corpus lives under evals/fixtures. Earlier passes accepted that as the corpus for G1 and I keep that reading. (b) G1–G3 count as done on this evidence. Any further work is limited to the charter's allowed idle work: tests, documentation and small refactors within G1–G3.

## Consequences
Once T-0051 merges, every message path in the code I checked has a content assertion, and the planner should keep the backlog empty unless a worker followup reports a real defect within G1–G3. No live API calls are needed or scheduled. Future passes should not invent new metric or corpus work: the harness is saturated at 1.000, and more corpus work would count as 'new', not idle.
