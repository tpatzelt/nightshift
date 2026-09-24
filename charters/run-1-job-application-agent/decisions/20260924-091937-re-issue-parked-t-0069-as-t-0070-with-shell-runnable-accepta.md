# Re-issue parked T-0069 as T-0070 with shell-runnable acceptance

_Recorded 20260924-091937 by the NIGHTSHIFT planner._

## Context
The backlog is empty and HEAD is still 8e4db4e. G1 and G2 are met: T-0063 pins all corpus metrics at 1.0. G3 has one open item. T-0069 (exact-text assertions for five intake replies) was parked after two attempts. Both failures came from its acceptance lines, which were English prose that the gate ran as shell commands (bash syntax error, command not found, git ambiguous argument). The worker's actual test work was never judged. I re-read src/intake.py and tests/test_intake.py and confirmed that the five replies are still checked only by substring and that the quoted strings match the code.

## Decision
Add T-0070: the same tests-only scope, limited to tests/test_intake.py. Every acceptance line is now an executable command: pytest, run_mock_test, grep -F for each exact expected literal, and a negated grep proving the old substring check is gone. The notes fix the constant name JOB_PREFS_PROMPT and require single-line string literals so the greps are deterministic. No other work is scheduled. This is allowed idle work within G3.

## Consequences
The acceptance is stricter about formatting. A worker who wraps an expected literal across lines fails the grep even if the test is correct, and the notes say this explicitly. Assumption: the current reply wording is intended, so the tests pin it instead of changing src/. T-0069 stays parked and must not be revived, because T-0070 supersedes it.
