# Initial backlog: G1 engine first, then G3 notification pipeline, then G2 app skeleton

_Recorded 20260929-080717 by the NIGHTSHIFT planner._

## Context
The repository is greenfield: a package stub, one smoke test, fastapi and httpx as dependencies. The backlog, done and parked lists are empty, and there are no followups. The charter priority is G1 > G3 > G2 > G4 > G5. G1 depends on real HAFAS response shapes, and the charter requires offline, fixture-replayed tests.

## Decision
The HAFAS client and offline fixture-replay harness (with a socket guard) come first. The commute model (DST-tested) and real fixture recording follow, then the pure disruption engine and alternative suggestion (M1). G3 follows: SQLite+SQL migrations (placed under G3 because the scheduler needs persisted commutes and notification state), the channel interface with fakes, a once-per-disruption tracker, and the simulated-morning scheduler (M3). One G2 app skeleton task is queued last so it is ready when the higher-priority work drains. Assumptions, chosen conservatively: (1) a disruption kind not observable live may be represented only by a minimal, clearly labelled edit of a real recorded response; otherwise it is reported as a gap rather than invented. (2) Fixture files count against max_diff_lines, so the recorder must trim responses. (3) The Telegram /start linking flow is deferred until the app skeleton exists. (4) jinja2 and uvicorn are added only in the app-skeleton task, with justification.

## Consequences
M1 can meet its definition of done after T-0001 to T-0005, provided enough real disruption kinds are recorded. A gap will come back as a followup, and a follow-up fixture task will be scheduled. G3 still needs a Telegram deep-link linking task once T-0010 lands. G2 routes, G4 and G5 are planned in later cycles.
