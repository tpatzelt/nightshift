# All charter goals meet their definition of done; the backlog moves to allowed idle work only

_Recorded 20260924-043840 by the NIGHTSHIFT planner._

## Context
On 2026-09-24 the planner replayed a read-only copy of job-application-agent at e49369b. `uv run python -m evals.offline_eval --check-baseline` exits 0 with 'No metric regressed vs baseline'. Against evals/baseline.json (revision b6da8dd), posting_shape_rate went from 0.815 to 1.000, aggregator_drop_rate from 0.765 to 1.000, location_match_rate stayed at 1.000, staleness_detection_rate went from 0.429 to 1.000, and dedup_rate from 0.571 to 1.000. `uv run pytest -q` gives 382 passed, 1 skipped (baseline 182 passed, 1 skipped), and run_mock_test.py passes. G1 was delivered by T-0001 to T-0005 and T-0018. G2 was delivered by T-0006, T-0009, T-0026 to T-0030, T-0036, T-0039 and T-0042. G3 was delivered by T-0010, T-0016, T-0024, T-0032 to T-0035, T-0045, T-0046, T-0049, T-0052 and T-0055 to T-0057. That covers the durable notified.json ledger, a 'Why:' line in every job message, and scan-error, delivery-failure, search-failure and missing-profile messages that each name what failed. Every other parked task was superseded by a re-issue that has since merged. None of them is revived.

## Decision
Treat M1, M2 and M3 as met. Add no new goals, milestones or features. Schedule only the charter's allowed idle work, one small tests-only task at a time. The first is T-0059, which replaces substring checks with exact-text assertions on the one message path that has them, the missing-profile scan message. Assumptions, recorded because they could not be confirmed: (1) M1-M3 have no status op, so their roadmap status is left as it is rather than edited outside the op set. (2) evals/runs/offline/ is not in the read-only mount; the harness writes its report there at run time, so its absence is not treated as a G1 gap. (3) The planner made no live Brave or OpenRouter calls, because no open question needed one.

## Consequences
The backlog stays thin on purpose. Later passes should add only tests, documentation or small refactors inside G1-G3, and only after they find a real gap in the code. If a merged idle task ever moves a harness metric below the current 1.000 values or breaks the pytest or mock-loop gates, fixing that regression takes priority over any further idle work.
