# Re-issue parked T-0039 (send test message) as T-0053 with the reviewer's fix, and unblock the stalled G5/G4 queue

_Recorded 20261001-050216 by the NIGHTSHIFT planner._

## Context
All three ready tasks were effectively blocked. T-0040, the G5 done test, depends on T-0039, which is parked. T-0051 depends on T-0040, and T-0052 depends on T-0051. So no task could start. The code confirms that the send-test-message action is still missing: app.py has no get_channels dependency and no /notifications/channels/{id}/test route. Its only POST routes under /notifications/channels are the unlink route. T-0039 attempt 1 was reviewed as correct except for one blocking issue: an async handler calling a blocking httpx channel send on the event loop. Attempt 2 ended without a status, most likely because it ran out of budget.

## Decision
Add T-0053. It re-issues T-0039 with a step-by-step spec built from the code as it is now: an lru_cached get_channels built from runner.build_channels (runner does not import app, so there is no import cycle), and a plain-def route so the send runs in the threadpool. It also names the exact DE/EN strings and the test cases, and gets a larger budget (60 min / 80 turns). T-0040 now depends on T-0053 instead of T-0039, and its notes name the route and the override. T-0051 drops its ordering-only dependency on T-0040, so G4's test-only work is not blocked if G5 stalls again. Charter priority is still enforced by the queue order T-0053, T-0040, T-0051, T-0052. T-0039 stays parked as history. G1, G3 and G2 already have their definition-of-done tasks done (T-0006, T-0049, T-0034), so no work is needed there. Assumption: 502 is an acceptable status for a failed test send (the attempt-1 reviewer accepted it). Assumption: removing a dependency that only set ordering does not violate the priority order, because rank still orders the queue.

## Consequences
The G5 chain can move again: T-0053 adds the feature, then T-0040 proves G5's definition of done. G4's two test-only tasks can run without waiting on G5. No migration, dependency, fixture or network change. Real channels are never constructed in tests, and Telegram and ntfy are never contacted. If T-0053 parks again, the next planner should split it into (a) get_channels plus the route with its tests and (b) the template button and status/alert messages.
