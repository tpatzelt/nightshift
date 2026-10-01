# Retry the parked HAFAS client T-0013 as T-0019 with the blocking TTL test specified exactly, and repoint T-0009 at it

_Recorded 20260929-094047 by the NIGHTSHIFT planner._

## Context
T-0013 (HAFAS client) was parked after attempt 2. The reviewer found the implementation correct and the attempt-1 gaps closed, but gave one blocking issue: the TTL test refetched a different cache key, so it would pass even if TTL lookups were broken. The reviewer also listed non-blocking hardening: negative or NaN Retry-After, an unencoded trip_id, naive datetimes, TransportError and bad JSON not wrapped in HafasError, and mutable cached values. Nothing from T-0013 was merged; /repo/mein-pendel has no src/pendel/hafas. T-0009 (scheduler) still depended on the parked T-0013, so it could never become runnable. The worker followup list was empty.

## Decision
Add T-0019 with T-0013's scope and allowed_paths. Its notes spell out the exact TTL test (same key: 1 request before the TTL, 2 after, len(cache)==1) and add the cheap hardening items, each with a test. max_diff_lines rises from 450 to 500 to make room for them, still under the 800 cap. T-0009 now depends on T-0019 instead of T-0013. T-0009's fixture write access is narrowed from tests/fixtures/hafas/** to tests/fixtures/hafas/scheduler/**, which enforces its existing note not to edit recorded fixtures. T-0019 is ranked first; every other task keeps its relative order. Assumptions (conservative): T-0013 stays parked and its ID is not reused. Naive datetimes are rejected rather than silently localised, because the charter says Europe/Berlin throughout and guessing a zone could shift times across DST. T-0019 is ranked above fixture recording (T-0015) because it needs no network access and unblocks the G3 scheduler.

## Consequences
The client can land in one attempt if the worker follows the spelled-out test. The G3 scheduler is no longer blocked by a parked dependency. The hardening makes T-0019's diff somewhat larger than T-0013's. If T-0019 is also parked, the next planner should move the hardening into its own task and keep only the core client. G4 and G5 remain unplanned until higher-priority work drains.
