# Re-issue the unreached idle task T-0059 as T-0060: exact-text assertions for the missing-profile scan message

_Recorded 20260924-044001 by the NIGHTSHIFT planner._

## Context
On 2026-09-24 HEAD is still e49369b. I re-ran the gates on a writable /tmp copy (dependencies downloaded normally). `uv run pytest -q` gives 382 passed, 1 skipped. `python -m evals.offline_eval` exits 0 with TOTAL 1.000 on all five metrics, against arming values of 0.815, 0.765, 1.000, 0.429 and 0.571. G1-G3 meet their definition of done. The previous pass decided to schedule T-0059, which replaces substring checks with exact-text assertions on the missing-profile scan message. It is not in /plan/backlog, /plan/done or /plan/parked, so like T-0037, T-0041, T-0044, T-0047, T-0051 and T-0054 it never reached the backlog. I confirmed the gap is real: tests/test_bot_service.py:708-811 assert only substrings of the text built by src/bot_service.py:63-75.

## Decision
Add T-0060, a tests-only task limited to tests/test_bot_service.py (max 120 diff lines). It asserts the full message text for the CV-only, preferences-only and both-missing cases, at the formatter and at the send boundary. It uses a new ID so it cannot collide with the planned T-0059. Assumptions, each the conservative reading: (1) with every goal done, only charter-allowed idle work is scheduled, and only for a verified gap; (2) the milestones' 'planned' status is left alone because no op changes it; (3) I made no live Brave or OpenRouter call because no open question needed one.

## Consequences
One small, independently testable idle task is ready, and no src/, evals/ or README change is authorised. If T-0060 finds the message text itself is wrong, that comes back as a followup rather than a src edit. After T-0060 merges, later passes should stay idle unless HEAD moves, a followup arrives or a gate regresses.
