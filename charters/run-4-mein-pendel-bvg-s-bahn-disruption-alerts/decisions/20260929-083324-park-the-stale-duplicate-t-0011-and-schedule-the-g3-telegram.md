# Park the stale duplicate T-0011 and schedule the G3 Telegram linking flow (T-0014)

_Recorded 20260929-083324 by the NIGHTSHIFT planner._

## Context
The previous planner cycle split T-0011 into T-0012 and T-0013, and its ADR says T-0011 stays parked. It was still in the backlog as ready at rank 0, though, with the same paths as T-0012 and T-0013. The repo still has only the package stub, and there are no done tasks and no followups. Every remaining piece of G3's definition of done has a task except the Telegram /start linking flow, which the initial ADR deferred until the app skeleton exists.

## Decision
Park T-0011 as superseded. Add T-0014, a pure linking module (create_link and handle_update) over the channels table and the Channel interface. It depends on T-0006 and T-0007, not on the G2 app, and is tested end-to-end with FakeChannel and hand-made update dicts. Order: T-0003, T-0012, T-0002, T-0013, the rest of M1, then M3 including T-0014, then T-0010 (G2). This follows the charter priority G1 > G3 > G2. Assumptions, taking the conservative reading: (1) 'tested end-to-end against a fake' means driving deep-link creation, the /start update and the confirmation send through fakes, with no web route. (2) How updates are received in production (webhook or polling) is left to a later G2/G4 task and is not invented here. (3) The bot username comes from an env var so no real identifiers go into the repo.

## Consequences
Workers no longer see two ready tasks that edit the same files. All G3 definition-of-done items now have tasks. Once T-0010 lands, a later G2 task will expose the link URL on the page and attach the update receiver. G4 and G5 are still unplanned and will be scheduled when the higher-priority work drains.
