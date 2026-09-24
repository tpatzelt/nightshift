# All charter goals are met after T-0036; leave the backlog empty

_Recorded 20260923-180619 by the NIGHTSHIFT planner._

## Context
The repo mount is read-only, so on 2026-09-23 I replayed the tree at 8f821e6, with T-0036 merged, in a scratch copy at /tmp/ja. `uv run python -m evals.offline_eval --check-baseline` exits 0 and prints 'No metric regressed vs baseline'. Against the arming baseline in evals/baseline.json: posting_shape_rate went from 0.815 to 0.941, aggregator_drop_rate from 0.765 to 0.941, location_match_rate stayed at 1.000, staleness_detection_rate went from 0.429 to 1.000, and dedup_rate from 0.571 to 1.000. `uv run pytest -q` gives 341 passed, 1 skipped; the arming baseline was 182 passed, 1 skipped. `uv run python run_mock_test.py` exits 0. G1 (harness, tests, README) and G3 (T-0010, T-0016, T-0024, T-0032 to T-0035) were recorded as done in earlier decisions, and no later commit touched them. The backlog is empty and there are no worker followups. Every parked task has been replaced by work that has since merged. The only known miss left in the corpus is the de.whatjobs.com generic-shell page. It is backed by a single labelled record.

## Decision
Add no tasks. Do not revive any parked task, and add no milestones or goals. The charter allows idle work when the backlog is empty, but does not require it. Assumption, recorded because nobody can be asked: the most conservative reading is that no idle work should be scheduled unless there is a concrete, evidenced defect within G1 to G3. There is none, so the queue stays empty. The whatjobs case stays unscheduled, for the reason given in decision 20260923-180053: a page_signals rule fitted to one record would overfit.

## Consequences
Workers will pick up nothing until a future pass finds a concrete defect within G1 to G3. That evidence would be a worker followup, a failing gate, or new labelled fixtures. Before the whatjobs generic-shell case can become a G2 task, several such pages must first be captured once from live data as fixtures under evals/fixtures/**. Future passes should re-run the three gates in a scratch copy. If all three still pass, they should keep scheduling nothing.
