# Split blocked T-0011 into an offline harness (T-0012) and a HAFAS client (T-0013), and decouple the G1 engine chain from the client

_Recorded 20260929-081840 by the NIGHTSHIFT planner._

## Context
T-0011 (HAFAS client plus offline harness) was blocked twice, and no reason was recorded. A planner check in a scratch copy of the repo showed that `uv sync` and `uv run pytest -q` work and that zoneinfo resolves Europe/Berlin, so the environment itself is not the obvious cause. One possible cause is a conflict between the note 'make no live network calls' and running `uv sync` as an acceptance command. Another is that the task bundled too much. T-0002 and T-0004 depended on parked T-0011, which stalled the whole G1 chain. The engine (T-0004) is a pure function and does not need the client.

## Decision
T-0011 stays parked, since IDs are never reused. Two smaller tasks replace it. T-0012 builds the socket guard and replay transport in tests/conftest.py. T-0013 builds the client with a bounded TTL cache and backoff, and depends on T-0012. `uv sync` is left out of their acceptance, because neither task changes dependencies. Their notes say explicitly that running uv and pytest is fine and that HTTP calls are not allowed. Both tasks ask the worker to report the exact blocking command and its error. T-0002 now depends on T-0012 only. T-0004 depends on T-0002 and T-0003 only. T-0009 now depends on T-0013 as well. Order: T-0003, T-0012, T-0002, T-0013, then the rest of M1, then M3, then M2. Assumptions, taking the conservative reading: the cause of the two blocks is unknown, so this is a re-scope, not a fix; and the harness lives in conftest.py so no tests package is needed.

## Consequences
M1's definition of done (fixtures, commute model, engine, alternative) no longer waits on the client. If T-0012 blocks as well, the report should include the exact error, which will show whether the sandbox or the pipeline is the cause. The G3 scheduler still needs T-0013 before it can start.
