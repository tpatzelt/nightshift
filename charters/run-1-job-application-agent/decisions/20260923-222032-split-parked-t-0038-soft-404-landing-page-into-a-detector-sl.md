# Split parked T-0038 (soft-404 landing page) into a detector slice and a wiring slice

_Recorded 20260923-222032 by the NIGHTSHIFT planner._

## Context
The backlog is empty. Replaying HEAD 8f821e6 offline on 2026-09-23 (in a /tmp copy; the mount is read-only) gives TOTAL posting_shape_rate 0.941 and aggregator_drop_rate 0.941 against an arming baseline of 0.815 and 0.765, with location, staleness and dedup at 1.000. The full suite shows 341 passed and 1 skipped, and run_mock_test.py and --check-baseline pass. G1 and G3 appear to meet their definitions of done: the harness, tests and README exist; the ledger (T-0024), in-list dedup (T-0035), scan-error text (T-0016/T-0032) and send-boundary assertions (T-0032..T-0034) are merged. The only remaining corpus miss is the WhatJobs landing page at project-manager-berlin.jsonl line 5. T-0038 targeted it and was parked after two attempts that both ended with worker status=None, with no gate or test failure. That points to exhausted time or turns, not a wrong approach.

## Decision
Keep T-0038's approach, which was verified correct against the code (the URL shape stays POSTING and the fix is a page-text signal). Re-issue it as two smaller tasks. T-0039 adds find_landing_marker to src/page_signals.py, with a corpus-wide negative test against every kind=posting record. T-0040, which depends only on T-0039, wires the signal into Orchestrator._process_url, the run-report counter label and evals/offline_eval.replay_keep. Each slice has a tighter diff and turn budget. The dependency is one level deep and needed only because T-0040 calls T-0039's function. Assumption: status=None means the worker exhausted time or turns; this is recorded rather than verified. No live API calls were made for this planning pass.

## Consequences
If both land, the G2 metrics should reach 1.000 on every column, the corpus has no headroom left, and later passes should schedule only charter idle work (tests, documentation, small in-scope refactors). T-0038 stays parked and must not be revived, because T-0039 and T-0040 carry its work. If T-0039 also ends with status=None, the next pass should treat the problem as an environment or runner issue, not task size, and report it rather than slicing further.
