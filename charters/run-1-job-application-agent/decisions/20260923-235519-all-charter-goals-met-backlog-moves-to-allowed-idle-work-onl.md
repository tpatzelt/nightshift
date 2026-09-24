# All charter goals met; backlog moves to allowed idle work only

_Recorded 20260923-235519 by the NIGHTSHIFT planner._

## Context
On 2026-09-23 I checked a read-only copy of the repo at cac026c. `uv run python -m evals.offline_eval` exits 0, prints the per-metric table and writes evals/runs/offline/report.json. TOTAL is 1.000 on posting_shape, aggregator_drop, location_match, staleness_detection and dedup. The arming baseline (evals/baseline.json, rev b6da8dd) is 0.815 / 0.765 / 1.000 / 0.429 / 0.571. So G2 improves on both required metrics and no metric regresses. G1 is covered by tests/test_offline_eval.py, test_offline_metrics.py and test_offline_baseline.py, and the README documents every metric. For G3: the ledger (T-0024) and within-list dedup (T-0035) stop repeat notifications, the Why: line is in (T-0046), and scan-error and delivery-failure text is asserted (T-0032, T-0049). `uv run pytest -q` gives 362 passed, 1 skipped, and run_mock_test.py passes. Every older task in PARKED is either superseded by one that has since merged or is a failed attempt that was later re-issued and merged. An audit of user-visible strings found one path whose content is not asserted: the document-upload failure reply in src/intake.py (DocumentExtractionError / TelegramError such as 'File too large').

## Decision
I added no new goal work. I scheduled a single allowed-idle task, T-0051 (tests only, G3/M3), to assert that reply's content. I revive none of the parked tasks, because each one's work has already merged under a later ID. Assumption, recorded because the op schema has no way to mark a milestone done: M1-M3 are treated as met on the evidence above, and I leave the roadmap text unchanged rather than invent an op.

## Consequences
The backlog holds only test work that tightens G3's 'every message path asserted' criterion. Once T-0051 merges, the next planning pass should schedule nothing further unless worker followups name a concrete G1-G3 gap. No live API spend is needed or planned.
