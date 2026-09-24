# Re-issue the soft-404 landing-page gate as T-0038, with protected_paths that do not conflict with allowed_paths

_Recorded 20260923-220518 by the NIGHTSHIFT planner._

## Context
Decision 20260923-220409 scheduled T-0037 (a soft-404 landing-page gate), but T-0037 is not in backlog, done or parked, so the add was not applied. That ADR says it protected the corpus and baseline 'for this task'. An earlier planner decision (180053, cited in T-0036) also never reached the backlog. I replayed HEAD 8f821e6 offline to /tmp; it printed the table and wrote the report, with no live calls. TOTAL: posting_shape 0.941 (arming 0.815), aggregator_drop 0.941 (0.765), location 1.000 (1.000), staleness 1.000 (0.429), dedup 1.000 (0.571). G1 is met and G2's definition of done is met. The G3 slices (T-0010, T-0016, T-0024, T-0032..T-0035) are merged. The only remaining corpus miss is the WhatJobs landing page at a posting-shaped URL. All fixture texts are under 800 chars, so mirroring the production min_job_text_chars gate in the harness would not help: it would drop every record.

## Decision
Add one G2/M2 task, T-0038, with the same intent as T-0037. It is a page-text landing signal in src/page_signals.py, wired into Orchestrator._process_url after the stale gate and mirrored in evals/offline_eval.replay_keep. Assumptions: (a) I use a fresh ID, T-0038, in case T-0037 is held somewhere I cannot see. (b) The earlier add was most likely rejected because allowed_paths (evals/offline_eval.py) overlapped a broad protected evals/**. So this task protects only evals/fixtures/**, evals/baseline.json, evals/metrics.py and evals/corpus.py. That does not shrink any existing task's protected set, and it keeps the measure frozen. (c) No roadmap status changes: no op exists for them. Parked T-0007..T-0031 stay parked because each was superseded by merged work.

## Consequences
If T-0038 lands, both headline metrics reach 1.000 and the corpus has no known G2 headroom left. After that, only the charter's idle work is valid until new labelled records are captured. The risk is a detector that drops real postings. The negative tests on real posting texts and --check-baseline guard against it. If this add is also not applied, the next pass should not re-issue it a third time. It should record 'blocked: planner add_task ops for this task are not being applied' instead.
