# Full backlog to the charter's definition of done: G3 today cards, then G2 midnight windows and management, G5 notifications, G4 design

_Recorded 20260930-141012 by the NIGHTSHIFT planner._

## Context
G1 is done (T-0001 to T-0006), and so are the G2 paused flag and CRUD helpers (T-0007) and the G3 generic-remark fallback (T-0008). Only T-0009 and T-0010 were queued. What the code still needs: /today shows stop IDs, ignores paused and never shows departures or alternatives. suggest_alternative rejects child-stop arrivals. Commute rejects windows crossing midnight. There are no my-commutes, edit, pause or delete routes. Tracker messages carry only the reasons. The notifications page has no unlink or test message. The CSS has no custom properties, and there is no manifest.

## Decision
Queue T-0011 to T-0030 in charter priority order G3 > G2 > G5 > G4. Tasks that touch the same files, or build on another task's output, depend on it. Assumptions: (1) the child-stop alternative is proven with a labelled synthetic /journeys fixture, modelled on the real 900003200/900003201 pair, so no journeys request is recorded. (2) A window with end < start crosses midnight, and its weekdays refer to the start day. No maximum length is invented, so the a11y test's '08:00-07:30' invalid example becomes a malformed time. (3) The today statuses are ok/disrupted/paused/failed, plus the existing labelled 'inactive'. (4) The notification link is PENDEL_PUBLIC_URL + '/today', or bare '/today' when unset. deploy/ stays untouched, and the variable is reported as a followup. (5) The resolved message names the kind and line taken from the stored disruption key, so no migration is needed. (6) The test message goes through an overridable get_channels dependency and is only ever exercised with FakeChannel. (7) Migrations 0002 and 0003 are now protected alongside 0001.

## Consequences
20 new tasks ordered by priority, with dependencies only where tasks share files or build on each other, each at most 450 diff lines. The G3 definition of done lands at T-0015, G2 at T-0022, G5 at T-0026 and G4 at T-0030. No task makes live HAFAS requests except T-0009, which is already queued. None contacts a messaging service. PENDEL_PUBLIC_URL will need a human to add it to the deploy env after the run.
