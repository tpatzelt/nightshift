# Re-issue T-0036, the missing meinestadt /jkl/ fix; all goals otherwise stay at done

_Recorded 20260923-180130 by the NIGHTSHIFT planner._

## Context
The repo mount is read-only, so I replayed today's tree with `python3 -m evals.offline_eval --out <tmp>`. TOTAL is 58 records, 18 kept: posting_shape_rate 0.889, aggregator_drop_rate 0.882, location_match_rate 1.000, staleness_detection_rate 1.000, dedup_rate 1.000. The arming baseline in evals/baseline.json is 0.815 / 0.765 / 1.000 / 0.429 / 0.571, so G2's definition of done holds and no metric regressed. G1 (harness, tests, README) and G3 (T-0010, T-0016, T-0024, T-0032 to T-0035) were done as of the previous decision. Decision 20260923-180053 scheduled T-0036, but no T-0036 exists in backlog, done or parked, so that op was never applied. src/url_heuristics.py:309 still treats `jkl` as a posting segment. There are no worker followups.

## Decision
Re-issue T-0036 as the only ready task. It is a narrowly scoped G2/M2 fix in src/url_heuristics.py, covered by the already-labelled fixture record project-manager-berlin.jsonl:4, with an offline test that must fail without the change and a --check-baseline gate. I am not scheduling the whatjobs generic-shell miss (de.whatjobs.com/jobs?id=...), for the reason already recorded: a page_signals rule fitted to one record would overfit. No new milestones or goals. Parked tasks stay parked because each is superseded by merged work. Assumption, recorded because nobody can be asked: since G2's definition of done is already met, this counts as the charter's allowed idle work (a small change strictly within G2), not new scope.

## Consequences
Once T-0036 merges, the backlog should stay empty unless new worker followups or new labelled corpus evidence show a concrete defect within G1 to G3. If a future pass finds T-0036 missing again, that points to a planner-op application problem, not a need for new work. Before the whatjobs case can be scheduled, more live-captured fixtures of that shape are needed under evals/fixtures/**.
