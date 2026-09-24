# Re-issue the lost T-0062 as T-0063: pin the achieved G2 corpus totals in the default test suite

_Recorded 20260924-082450 by the NIGHTSHIFT planner._

## Context
Planner pass on 2026-09-24 at HEAD 638ad58, with a clean tree. The previous pass (20260924-082315) planned T-0062, but it is absent from the backlog, done and parked, so it never landed. That pattern is already recorded for T-0037, T-0041, T-0044, T-0047, T-0051, T-0054 and T-0059. I made a scratch copy and verified: `uv run pytest -q` gives 383 passed, 1 skipped; run(DEFAULT_CORPUS_DIR) totals are records=58 and kept=16 with all five metrics at 1.0; no existing test asserts those achieved values. G1, G2 and G3 meet their definition of done. There are no worker followups, and every parked task has a merged successor.

## Decision
Add T-0063, a single test-only idle task in tests/test_offline_baseline.py that pins the achieved totals. It carries a new id, following the earlier practice of never reusing a planned id that did not land. Assumptions: (1) This counts as allowed idle work ('tests ... strictly within G1–G3') and is not a new goal. It cites G2/M2 because it guards G2's 'no metric regressing' clause. (2) evals/baseline.json is protected and not re-frozen, so the arming reference stays intact. (3) Acceptance entries are shell-runnable commands only, because prose acceptance killed T-0048. (4) Parked tasks stay parked, because each one is superseded by merged work. (5) I made no live API calls, because none was needed. (6) No op can change milestone status, so M1–M3 stay 'planned' in ROADMAP.md.

## Consequences
Once T-0063 merges, any change that lowers a corpus metric below 1.000, or changes the kept count, fails `uv run pytest -q` and names the metric. It does so even when the lower score still beats the arming baseline. A legitimate extension of evals/fixtures/** must update the pinned numbers in the same diff. If T-0063 also fails to appear in the backlog, the next pass should re-issue it under a fresh id. After T-0063, the backlog should stay empty unless new input appears.
