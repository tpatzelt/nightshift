# Re-issue the planned T-0054 intake-reply test task as T-0055; nothing else is scheduled

_Recorded 20260924-040814 by the NIGHTSHIFT planner._

## Context
HEAD is still 8417268. The backlog is empty and there are no worker followups. The previous pass (20260924-040729) found that all G1 and G2 definition-of-done items are met: every TOTAL metric scores 1.000 against the arming baseline (posting_shape 0.815, aggregator_drop 0.765, location 1.000, staleness 0.429, dedup 0.571). That pass also planned T-0054 to close the last unasserted G3 message path, but T-0054 is absent from /plan/backlog, done and parked, so it never reached the backlog, the same thing that happened to T-0037, T-0041, T-0044, T-0047 and T-0051. I checked the gap again on the tree. No test asserts 'Please try another file', the 'Please upload a document…' reply is checked only by a lowercase substring in the CV state, and neither reply is tested in the motivation or job-prefs states.

## Decision
Add one test-only task, T-0055 (G3/M3, allowed_paths tests/test_intake.py only, max_diff_lines 200, no dependencies), with shell-runnable acceptance commands. I used a fresh ID instead of T-0054 so it cannot collide with any stray T-0054 record. I added no G1 or G2 work: the harness is at its 1.000 ceiling, so any further triage change would be new scope, not a measurable improvement. No parked task is revived, because each one has been re-issued and merged or superseded. Assumptions, taken conservatively: (1) the charter's G3 definition of done counts these intake replies as user-visible message paths; (2) M1-M3 are effectively done but stay 'planned' because no op can change a milestone's status; (3) I could not run pytest here (read-only mount) and am relying on the merge gates of the merged tasks.

## Consequences
When T-0055 merges, every G1-G3 definition-of-done item has test evidence. Later passes should schedule nothing unless a followup, a parked reason or a regression shows a concrete gap, and then only the charter's allowed idle work. If T-0055 is also missing from the backlog on the next pass, the planned-task-to-backlog path itself is failing, and the planner should report that rather than re-issue the task a third time.
