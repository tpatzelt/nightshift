# Close G3's last silent scan-failure path; G1 and G2 are at their definition of done

_Recorded 20260924-030105 by the NIGHTSHIFT planner._

## Context
I replayed the harness read-only: `python -m evals.offline_eval --check-baseline` reports posting_shape 0.815->1.000, aggregator_drop 0.765->1.000, location 1.000->1.000, staleness 0.429->1.000, dedup 0.571->1.000, and no metric regressed. README documents each metric. All parked tasks were superseded by re-issues that have since merged: T-0031 by T-0032/33/34, T-0038/40 by T-0039/42, T-0048 by T-0049, T-0025 by T-0032..34/45. Reading src/bot_service.py, every other user-visible failure path now sends text and is asserted in tests. The exception is BotService._run_scan: an active user whose CV or preferences are missing is skipped with only a log line, so /run replies 'Scanning...' and then nothing ever arrives.

## Decision
Add one small G3/M3 task, T-0051, that sends an actionable message naming what is missing on that path, with tests that fail on the current code. The acceptance entries are shell commands only, because T-0048 failed when prose was run as an acceptance command. No work is scheduled for G1 or G2, and no parked task is revived, since each one's work has already merged under a re-issue. Assumptions: (1) I could not run `uv run pytest` here because the /repo mount is read-only and uv cannot create .venv, so I rely on the merged gates for green status. (2) Missing CV or preferences on an active record counts as a scan failure under G3, which is the conservative reading because it removes a silence and changes nothing else.

## Consequences
Once T-0051 merges, M1, M2 and M3 all meet their exit criteria. Later passes should schedule only the charter's allowed idle work (tests, documentation, small refactors within G1-G3). If the next pass confirms no gaps remain, it should add no new feature tasks.
