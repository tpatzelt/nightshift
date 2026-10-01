# Re-issue parked T-0015 as T-0049 and unblock the G2 chain

_Recorded 20260930-192654 by the NIGHTSHIFT planner._

## Context
T-0015 (G3 done test) was parked twice because the worker reported no status, which suggests it ran out of budget rather than hit a real failure. T-0019 depended on T-0015, so the whole G2 chain T-0019 → T-0020 → T-0032..T-0034 was blocked, and the G4 done test T-0048 behind it too. The code already renders stop names and all four status labels with text, the engine already falls back to cleaned remark text (tested in test_engine_recorded.py), and the today template renders planned and real-time <time> elements. The fixtures confirm that departures_undisturbed.json has U8 planned 07:18 with real-time 07:19, and departures_warning.json has RB32 07:46 with the generic summary 'Störung.'.

## Decision
Add T-0049 as a narrower re-issue of T-0015: one new test function, exact fixture lines and times, a warning about the nested-</li> pitfall in _card_block, a larger budget (45 min, 60 turns) and an explicit instruction to always report a status. Remove T-0015 from T-0019's depends_on. T-0019 is G2 work and only needs T-0018 (done); both edit tests/test_web_today.py, so T-0049 is ordered first to avoid conflicts. G3 comes before G2 in charter priority, so it goes to the front of the backlog. T-0015 stays parked as history. Assumption: a stop ID is treated as any 9-digit number starting with 9, matching the charter's examples.

## Consequences
G3 has a ready path to done again, and G2 no longer depends on a parked task. If T-0049 finds a real production bug, it reports blocked with the failing assertion, and a fix task gets planned next round. No production code, migration, dependency or network change.
