# Re-issue planned T-0068 as T-0069: exact-text assertions for the remaining mid-setup intake replies

_Recorded 20260924-091324 by the NIGHTSHIFT planner._

## Context
The backlog is empty. HEAD is 8e4db4e and the working tree is clean. Decision 20260924-091232 found that all three goals meet their definition of done except for a few intake replies that are still asserted only by substring, and it planned T-0068 to pin them. T-0068 never reached /plan/backlog, which is the same planned-but-never-landed pattern seen with T-0037, T-0047, T-0051, T-0054, T-0059 and T-0062. This pass re-read src/intake.py and tests/test_intake.py at 8e4db4e and confirmed the gap: the motivation-received reply, the job-prefs prompt after /skip, and the /status replies in the awaiting_cv, awaiting_motivation and unknown states are checked with `in` only. There are no worker followups. Every parked task has been superseded by a re-issue that has since merged.

## Decision
Add one test-only task, T-0069, restricted to tests/test_intake.py and citing G3/M3. Each test's substring checks are replaced by one equality assertion against the exact text quoted in the task, so a wording regression fails the default suite. No src/ change, no new behaviour, no new milestone, and no parked task is revived. Assumptions, choosing the most conservative reading: the current reply wording is intended, and the pytest baseline of 388 passed and 1 skipped comes from decision 20260924-091147, because this pass could not re-run the gates (the repo mount is read-only, so uv cannot create .venv).

## Consequences
Once T-0069 merges, every intake reply path has an exact-text assertion, which closes the last known G3 coverage gap. After that there is no identified work. Later passes should add nothing unless HEAD moves, a followup arrives or a gate fails. If T-0069 also fails to appear in the backlog, a person should look at why add_task ops are dropped rather than a planner re-issuing it again.
