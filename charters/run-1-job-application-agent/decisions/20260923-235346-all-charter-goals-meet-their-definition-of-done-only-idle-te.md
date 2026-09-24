# All charter goals meet their definition of done; only idle test work is scheduled

_Recorded 20260923-235346 by the NIGHTSHIFT planner._

## Context
I replayed the tree at cac026c (T-0050) on a writable copy because /repo is read-only. G1: `uv run python -m evals.offline_eval` exits 0, prints the per-metric table, writes evals/runs/offline/report.json, is covered by tests/test_offline_eval.py, test_offline_metrics.py and test_offline_baseline.py, and README lines 183-207 document it. G2: the TOTAL row is 1.000 on posting_shape, aggregator_drop, location_match, staleness_detection and dedup. The arming baseline (evals/baseline.json, rev b6da8dd) is 0.815/0.765/1.000/0.429/0.571, so both required metrics improved and none regressed. G3: tests/test_bot_service.py asserts the scan-error, dispatch-failure, /run (not set up, started, already queued), no-new-jobs and notify_failed texts at the send boundary; the notified.json ledger (test_notify_ledger.py) and in-run dedup (T-0035) prevent repeat notifications. Full suite: 362 passed, 1 skipped. run_mock_test.py passes. There were no worker followups. Every parked task is superseded by merged work.

## Decision
Add no new feature, goal or milestone work. Schedule one idle-work task (T-0051, tests only), because the notify_failed user message asserts a behaviour that no test pins: undelivered results are marked seen and not resent. Assumption, taken conservatively: if T-0051 finds the claim false, the worker reports blocked rather than editing src/, so any change to user-visible wording or behaviour becomes a separate, deliberate G3 task. Do not revive the parked tasks. Do not re-freeze evals/baseline.json: it stays the arming baseline that G2 is measured against.

## Consequences
The backlog stays near-empty by design once T-0051 lands. Later planner passes should verify the metric table and test count again, and schedule only charter-allowed idle work (tests, docs, small refactors within G1-G3) unless a regression appears.
