# Re-issue parked T-0048 as T-0049 with acceptance entries that are shell commands only

_Recorded 20260923-233058 by the NIGHTSHIFT planner._

## Context
The backlog is empty. T-0048 is the last open G3/M3 gap: undelivered job notifications are silent. I re-checked HEAD fc06634. src/orchestrator.py `_notify` (lines 277-283) still drops notify_results' False return and swallows exceptions, and src/bot_service.py `_run_scan` still messages the user only when results is empty. T-0048 was parked after two attempts, and both failed at the gate before any worker ran. Its gate output shows that each acceptance entry is executed as a bash command, and T-0048's prose entries failed with exit codes 2 and 127. The parked reason describes a malformed task, not a problem with the work itself. G1 and G2 were recorded as met by earlier passes. I did not re-run the harness in this pass.

## Decision
Add T-0049 with the same scope, files and 250-line cap as T-0048. Every acceptance entry is now a runnable command: the full test suite, the mock end-to-end run, the offline harness baseline check, `pytest -k notify_failed` on both test files (exit 5 if no such test exists), and greps for the fixed counter key `notify_failed` in run_report, orchestrator and bot_service. The behaviour spec moves to notes. I fixed the counter name as `notify_failed` so the acceptance can check it mechanically; this was one of T-0048's suggested options. Conservative choices kept from T-0048: no automatic-retry promise in the message, and report.save() is not reordered before _notify. T-0048 is not revived because it would fail at the same gate. It stays parked as superseded.

## Consequences
Once T-0049 merges, every G3 definition-of-done item has a test, and later passes should schedule only the charter's allowed idle work. Future tasks must keep acceptance to shell commands and put prose criteria in notes. If Telegram is fully down, the failure message itself may not arrive. `_safe_send` already swallows that, so the scan never breaks. Because report.save() runs before _notify, the runs.json history will not record notify_failed. Only the in-memory last_report does. Changing that ordering is left out of scope.
