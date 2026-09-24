# G1 and G2 met; schedule the last unasserted onboarding reply as G3 tests-only work

_Recorded 20260924-080725 by the NIGHTSHIFT planner._

## Context
The backlog was empty. In a scratch copy of the current agent/integration tree (HEAD 65c3351), `uv run python -m evals.offline_eval` exits 0 with TOTAL posting_shape, aggregator_drop, location_match, staleness_detection and dedup all at 1.000. The committed arming baseline (evals/baseline.json, rev b6da8dd) is 0.815 / 0.765 / 1.000 / 0.429 / 0.571. `uv run pytest -q` gives 382 passed, 1 skipped, and run_mock_test.py passes. For G3, the notify ledger, the delivery-failure message, the scan-error message, the missing-profile message and the empty-scan explanation are all merged and asserted. I searched the tests for every reply string in src/intake.py, src/bot_service.py and src/notifier.py. The only user-visible reply with no content assertion is IntakeManager._finalize's 'You're all set!' message, which includes the _format_schedule text.

## Decision
Add one small tests-only task, T-0061 (G3/M3), allowed to touch only tests/test_intake.py, with src/** protected. It asserts the finalize reply with == for the LLM path and the fallback path, and proves the configured scan hour and timezone reach the message. Its grep acceptance strings were computed from today's src output, so the work is achievable. No G1/G2 tasks were added: both are at their ceiling on the current corpus, and anything new there would be new scope, not idle work. Assumption, taken conservatively: the ROADMAP milestone statuses still read 'planned', but this op set has no way to mark a milestone done, so I left the roadmap unchanged rather than adding a duplicate milestone.

## Consequences
Once T-0061 merges, every user-visible message path found in src has a content-asserting test, and the backlog falls back to the charter's allowed idle work (tests, docs, small refactors within G1–G3). Parked tasks stay parked: each was superseded by a merged re-issue (T-0026..T-0036, T-0039, T-0042, T-0049), and reviving any of them would duplicate merged work.
