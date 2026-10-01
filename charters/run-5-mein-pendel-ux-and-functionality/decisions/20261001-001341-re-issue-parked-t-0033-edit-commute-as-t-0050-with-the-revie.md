# Re-issue parked T-0033 (edit commute) as T-0050 with the reviewer's fixes and repoint its dependents

_Recorded 20261001-001341 by the NIGHTSHIFT planner._

## Context
T-0033 was parked. Attempt 1 ended with no status. Attempt 2 was sent back by the reviewer for two gaps: the edit page still rendered 9-digit stop IDs in commute_new.html's hidden inputs, with no test for it, and the invalid-edit test covered only an out-of-range weekday. The repo's HEAD is T-0032, and app.py has no edit route, so none of the work landed. The charter's G2 done criteria need edit tests. T-0034 (G2 done check), T-0038 (notifications page) and T-0048 (G4 done test) all depended on the parked T-0033, so the G2, G5 and G4 chains were stuck behind it.

## Decision
Add T-0050 as a full re-issue of T-0033 with the same accepted design: GET /commutes/{id}/edit, POST /commutes/{id}, 404 scoping, keep stops and paused, 303 to /commutes, an Edit/Bearbeiten link, DE+EN. It also includes both reviewer fixes explicitly: hidden stop inputs are guarded by `commute_id is not defined`, the retry link points to the edit URL, a no-9-digit-ID assertion covers GET DE/EN and the 400 re-render, and the invalid-edit test is parametrized over weekday, no lines and '25:00'. db.py is protected because update_commute already exists. The budget rises to 60 min / 80 turns and the diff limit to 500 lines. T-0034, T-0038 and T-0048 now depend on T-0050 instead of T-0033. The order is G3 (T-0049), then G2 (T-0050, T-0034), then G5 and G4, following charter priority G1 > G3 > G2 > G5 > G4 (G1 is done). T-0033 stays parked as history. Assumption, carried over: editing does not change origin or destination; the visitor creates a new commute via /stops for other stops.

## Consequences
G2 has a ready path to its definition of done again, and G5 and G4 are unblocked behind it. No migration, dependency, network or fixture change. If the edit page's line-choice fetch fails in tests, the worker reports blocked, and a fixture task follows next round.
