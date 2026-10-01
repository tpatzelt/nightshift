# All goals are done and the idle work is covered; the backlog stays empty this turn

_Recorded 20261001-070354 by the NIGHTSHIFT planner._

## Context
The backlog is empty and there are no worker followups. Every goal has a finished definition-of-done task: G1 T-0006, G3 T-0049, G2 T-0034 (with T-0031 midnight/DST and T-0017..T-0019), G5 T-0040, and G4 T-0045/T-0046/T-0051/T-0052. The idle milestones M7 (README, T-0054), M8 (a11y labels, T-0055) and M9 (recorded platform-change fixture, T-0056) are done too. Each parked task (T-0015, T-0016, T-0033, T-0039, T-0048) was replaced by a re-issue that is now done, so they stay parked as history. I copied the read-only repo to /tmp and ran uv run pytest -q there: 490 passed, offline. The only output besides the results was one StarletteDeprecationWarning about httpx in TestClient. There are recorded fixtures for undisturbed, cancellation, delay (at a child stop), replacement service, construction, generic 'Störung.' warning, partial cancellation, platforms and a platform change, plus the stop-search responses. The 360px layout, manifest, status-label, contrast and form-label tests cover every page.

## Decision
Add no tasks and no milestones. Under 'Allowed idle work' more work is optional, not required. The remaining candidates are low value: more fixtures would mostly repeat disruption kinds that are already recorded, and would use the rate-limited public API. Small refactors or extra docs would risk the 'no restructuring not required by a task' non-goal and gain no charter outcome. Assumption: the charter allows an empty backlog once the idle work has been covered, and leaving it empty is the most conservative choice. Assumption: the httpx deprecation warning is not a failure, and changing dependencies to silence it would be unasked-for work, so it is only recorded here.

## Consequences
The workers stay idle, the code does not change, and no requests are sent to HAFAS or any messaging service. If a followup, a test regression or a parked reason shows up later, the next planner can queue a small task under the matching goal's milestone. The next task id is T-0057.
