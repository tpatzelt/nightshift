# All goals met at HEAD 017296a; schedule one docs-only idle task to list the landing-page gate in the README

_Recorded 20260923-225030 by the NIGHTSHIFT planner._

## Context
The backlog is empty and there are no worker followups. I verified HEAD 017296a on a /tmp copy because /repo is read-only. `python -m evals.offline_eval --check-baseline` exits 0 with TOTAL posting_shape_rate 1.000 (baseline 0.815), aggregator_drop_rate 1.000 (0.765), location_match_rate 1.000 (1.000), staleness_detection_rate 1.000 (0.429) and dedup_rate 1.000 (0.571), and no metric regressed. `uv run pytest -q` gives 347 passed, 1 skipped, against the arming floor of 182/1. G1 (T-0018, T-0026, T-0027), G2 (T-0028–T-0030, T-0036, T-0039, T-0042) and G3 (T-0016, T-0024, T-0032–T-0035) meet their definitions of done. One remaining gap: T-0042 added a landing-page gate to replay_keep, but the README paragraph that lists the replay's drop rules in production order (README.md:180-182) was not updated, so the G1 documentation no longer matches the harness.

## Decision
Add T-0043, a docs-only task limited to README.md with max_diff_lines 20, which adds the landing-page gate to the documented drop-rule list. Parked tasks are not revived: all have been superseded by merged re-issues. Assumptions, recorded because the human cannot be asked: (1) with every goal done, the charter permits only idle work (tests, docs, small refactors within G1–G3), and a doc that misdescribes the harness is the narrowest real gap; (2) the task cites G1/M1 because the README documentation is part of G1's definition of done; (3) protected_paths covers everything except README.md and does not shrink any earlier list for the files it names; (4) no live API calls are needed or authorised for this task.

## Consequences
Once T-0043 merges, the README matches the replay's gate order. After that, later planner passes should add nothing unless a worker followup, a new labelled record showing a miss, or a concrete untested message path or documentation gap turns up. Merge gates and live-API spend are unaffected.
