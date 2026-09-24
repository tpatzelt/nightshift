# All charter goals are met at 8f821e6, so the backlog stays empty and T-0038 stays parked

_Recorded 20260923-221700 by the NIGHTSHIFT planner._

## Context
I replayed HEAD 8f821e6 offline (`python -m evals.offline_eval --out /tmp/oe`). It exits 0. The TOTAL row is posting_shape_rate 0.941, aggregator_drop_rate 0.941, location_match_rate 1.000, staleness_detection_rate 1.000 and dedup_rate 1.000. The arming baseline in evals/baseline.json (revision b6da8dd) is 0.815, 0.765, 1.000, 0.429 and 0.571. That meets G2's definition of done: both required metrics beat the baseline and no metric went down. G1 was met by T-0018, T-0026 and T-0027. G3 was met by T-0010, T-0016, T-0024 and T-0032 to T-0035. There are no worker followups. The only open item is T-0038, which would drop the soft-404 WhatJobs landing page and raise the two metrics from 0.941 to 1.000. It has been parked after two attempts, and both ended with status=None, not with a test or logic failure. The charter allows only tests, documentation and small refactors once every goal is done, and says 'Nothing new'. A new page-signal gate in the orchestrator is new production behaviour, not idle work.

## Decision
Add no tasks and do not re-issue T-0038. Leave the backlog empty. The roadmap is unchanged. Assumption, recorded because the human cannot be asked: the charter's idle-work clause rules out new triage behaviour once G2's definition of done is met. That makes the extra 0.941 to 1.000 headroom optional. The narrowest reading is to not schedule a third attempt of a task that has already stalled twice without a diagnosable cause.

## Consequences
The merge gates stay green with no further diffs, and no live API spend is needed. The WhatJobs /jobs?id=261276305 landing page is still counted as a kept result in project-manager-berlin (0.667 posting-shape for that profile). If a later worker followup names a concrete reason why T-0038 stalled, or a charter-scoped test or documentation gap turns up, a later pass can schedule a narrowly scoped task for it. Until then, planner passes should confirm that HEAD is unchanged and add nothing.
