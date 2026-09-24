# Pin the exact text of the job notification and the scan-error message

_Recorded 20260924-084830 by the NIGHTSHIFT planner._

## Context
On 2026-09-24, HEAD is 5c1055a. On a scratch copy of the read-only mount I ran `uv run pytest -q` (385 passed, 1 skipped) and `python -m evals.offline_eval`, which scored 1.000 on all five metrics over 58 records. The arming baseline is posting_shape 0.815 and aggregator_drop 0.765, so G1 and G2 still meet their definition of done. The backlog is empty and there are no followups. I then checked each user-visible send path in src/bot_service.py and src/notifier.py against the tests. Most paths have exact-text assertions. Two do not: the job notification layout (no test covers the ' @ company' suffix; tests check it only with substrings), and _format_scan_error (fragments only; the empty-message branch and the truncation marker are never asserted).

## Decision
Add two independent tasks that change only tests, each limited to 60 lines and one test file: T-0065 (tests/test_notifier.py) and T-0066 (tests/test_bot_service.py). They pin the exact strings I observed at HEAD 5c1055a. This is idle work the charter allows (tests strictly within G3). No src/ change. No live calls. No parked task revived. Assumption: substring checks technically satisfy G3's 'asserting its content'. I still treat these paths as a coverage gap worth closing, because a silent wording regression in the two most common messages would not be caught. If these tasks are rejected as unnecessary, the conservative fallback is an empty backlog.

## Consequences
The default suite gains about three tests. Any future change to the notification or scan-error wording must now update a test on purpose. The two tasks touch different files and have no dependencies, so they can land in either order. After they merge, I see no remaining message path without an exact-text test, and the next pass should return to emitting no ops unless new input arrives.
