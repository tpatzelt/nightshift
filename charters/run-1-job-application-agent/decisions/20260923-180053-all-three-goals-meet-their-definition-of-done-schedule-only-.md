# All three goals meet their definition of done; schedule only one small in-goal G2 fix

_Recorded 20260923-180053 by the NIGHTSHIFT planner._

## Context
I replayed the working tree on 2026-09-23 in a scratch copy, because the repo mount is read-only. `uv run python -m evals.offline_eval --check-baseline` exits 0. Against the arming baseline: posting_shape_rate 0.815->0.889, aggregator_drop_rate 0.765->0.882, location_match_rate 1.000->1.000, staleness_detection_rate 0.429->1.000, dedup_rate 0.571->1.000, with no regression. `uv run pytest -q`: 340 passed, 1 skipped. `run_mock_test.py` passes. The README documents every metric. On G3, T-0024 and T-0035 (duplicate notifications), T-0016 (scan-failure text) and T-0032/33/34 (the three slices of parked T-0031) are merged. A per-record replay found two remaining misses, both in project-manager-berlin. (1) meinestadt /berlin/jkl/<id> is a 571-result category page, but url_heuristics treats 'jkl' as a posting segment. (2) de.whatjobs.com/jobs?id=261276305 has a posting-shaped URL but renders the generic search shell. Telling that apart needs a page-content rule.

## Decision
Add only T-0036, a URL-rule fix for meinestadt /jkl/. It stays inside G2's named file, is covered by an existing labelled record, and is tested offline. The whatjobs case is not scheduled. A rule based on a page's 'generic landing' wording fitted to one record would be overfitting and could drop real postings. Assumption, recorded because nobody can be asked: G2's definition of done is already met, so further G2 work counts as the charter's allowed idle work. It must be small, stay inside existing goals, and add nothing new. No new milestones and no new goals. Parked tasks stay parked: each one is superseded by merged work.

## Consequences
The backlog holds one ready task. Once it merges, the backlog should stay empty unless new worker followups or corpus evidence show a concrete defect in G1-G3 scope. Future passes should only schedule tests, docs or small refactors. Before scheduling the whatjobs generic-shell case, get more labelled examples, captured once from live data as fixtures under evals/fixtures/**, so a page_signals rule can be validated on more than one record.
