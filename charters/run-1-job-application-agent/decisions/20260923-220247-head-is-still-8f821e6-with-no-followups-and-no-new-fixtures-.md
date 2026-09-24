# HEAD is still 8f821e6 with no followups and no new fixtures, so the backlog stays empty

_Recorded 20260923-220247 by the NIGHTSHIFT planner._

## Context
Planner pass on 2026-09-23. HEAD is still 8f821e6 (T-0036) and T-0036 is still the newest done task. There are no worker followups and no ready tasks. The fixture set under evals/fixtures/** has not changed: the same six profiles and 58 records. I re-ran `python -m evals.offline_eval --out /tmp/oe` outside the repo with no live calls. It printed the per-metric table and wrote /tmp/oe/report.json. The TOTAL row was posting_shape_rate 0.941, aggregator_drop_rate 0.941, location_match_rate 1.000, staleness_detection_rate 1.000 and dedup_rate 1.000. The frozen arming baseline in evals/baseline.json is 0.815, 0.765, 1.000, 0.429 and 0.571. G1 is met. G2 is met: posting-shape and aggregator-drop both improved and no metric regressed. For G3, T-0010, T-0016, T-0024, T-0035 and T-0032 to T-0034 are merged. The only kept non-posting record is still the WhatJobs soft-landing page in project-manager-berlin, which earlier decisions (180619 to 220228) chose not to schedule. Every parked task has been superseded by merged work.

## Decision
Add no tasks and no milestones, and revive no parked task. Assumption, recorded because nobody can be asked: the charter allows idle work but does not require it. With no failing gate, no followup and no new evidence, scheduling nothing is the most conservative choice within the charter. A rule fitted to the single WhatJobs record would conflict with the pinned /jobs?id= posting shape in tests/test_url_heuristics.py and risks dropping real postings.

## Consequences
Workers have nothing to pick up. The next pass should check three things: whether HEAD has moved past 8f821e6, whether a worker followup has arrived, and whether new fixtures exist under evals/fixtures/**. It should schedule work only if one of these shows a concrete defect within G1 to G3, or if a gate fails when re-run in a scratch copy. Any task that is scheduled must keep evals/** protected.
