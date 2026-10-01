# Idle work while G1 stays blocked: scheduler DST tests (T-0042) and positive-only PENDEL_CHECK_LEAD_MIN (T-0043)

_Recorded 20260930-034256 by the NIGHTSHIFT planner._

## Context
The backlog is empty and T-0041 (deploy/verify.sh plus the CI verify job) is done, so G4's checks now run in CI. G2, G3 and G5 meet their definitions of done in code and tests. G1 still needs at least five recorded real disruption kinds, and live HAFAS recording is blocked in this sandbox (T-0016/T-0017/T-0018/T-0020-T-0022 parked). Only the charter's allowed idle work can be scheduled. Reading the repo found two small G3 gaps. (1) The charter requires DST transitions to be tested, and commute/engine/alternatives have DST tests, but tests/test_scheduler.py has none, even though Scheduler._due_commute converts the Berlin window plus the lead time to UTC. (2) scheduler._lead_minutes_from_env accepts 0 or negative values, although deploy/.pendel.env.example says the value must be a positive integer.

## Decision
Add T-0042 (G3/M3): DST tests for the scheduler on 2026-03-29 and 2026-10-25, including a window in the non-existent spring-forward hour. A minimal scheduler.py fix is allowed only if a test exposes a bug. Add T-0043 (G3/M3, depends on T-0042 because both edit tests/test_scheduler.py): reject a lead of zero or less with a ValueError at construction, mirroring the ratelimit env validation. Assumptions, taking the conservative reading: both are 'tests' and 'small refactors strictly within G1-G5' under the allowed idle work. Neither adds a feature, dependency or fixture. An empty PENDEL_CHECK_LEAD_MIN keeps raising, as the env example documents. No milestone is added, since M3 covers both. Synthetic fixtures still never count toward G1.

## Consequences
After these two tasks, scheduler timing is covered across DST, and a bad lead value fails at startup instead of silently delaying checks. Still open and needing a human: (1) network access for live HAFAS recording, which would unpark T-0020, then T-0016/T-0021/T-0022/T-0017 and T-0018, for G1, the top-priority goal; (2) confirming that deploy/verify.sh passes in CI, since the sandbox cannot run Docker; (3) real Impressum details in place of the placeholders. Until (1) is resolved, only further allowed idle work remains.
