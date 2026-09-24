# T-0064 merged at HEAD 5c1055a, all gates re-verified green; backlog stays empty

_Recorded 20260924-084007 by the NIGHTSHIFT planner._

## Context
Planner pass on 2026-09-24. There are no worker followups. HEAD in /repo/job-application-agent is 5c1055a (T-0064), and the working tree is clean. Since the previous ADR the only new input is T-0064 merging. It is a test-only task that pins the notifier's behaviour when the ledger cannot be written. I re-ran all three gates on a scratch copy at /tmp/ja, because /repo is read-only. `uv run pytest -q` gave 385 passed and 1 skipped, up from 384 because of T-0064. `uv run python -m evals.offline_eval` exited 0, printed the per-metric table and wrote evals/runs/offline/report.json. Its TOTAL row scored 1.000 on all five metrics over 58 records with 16 kept, against arming values of 0.815 for posting_shape and 0.765 for aggregator_drop, and no metric regressed. `uv run python run_mock_test.py` exited 0. G1, G2 and G3 all meet their definition of done.

## Decision
This pass schedules no tasks and leaves every parked task parked. Assumptions, recorded because no human can confirm them: (1) The charter allows idle work but does not require it. The previous pass's audit of the G3 message and ledger paths found one gap, and T-0064 has now closed it. No new gap has appeared, and adding tests or docs just to keep workers busy would break the charter's 'Nothing new' clause. (2) Every parked task has a successor that has already merged, so reviving one would duplicate delivered work. (3) The www-stripping inconsistency in canonical_url, noted in ADR 20260924-083611, is still out of scope. dedup_rate is 1.000 on the labelled corpus, which is the charter's measure, so changing it would be new behaviour. (4) I made no live Brave or OpenRouter calls, because none was needed and they cost real money. (5) No op can set a milestone's status, so M1-M3 still read 'planned' even though their exit criteria are met. The human should mark them done on return.

## Consequences
Workers stay idle until something new arrives: a new commit, a worker followup, a failing gate or a change in the pinned corpus totals. When that happens, the next planner pass should re-run pytest, offline_eval and run_mock_test. It should then add one narrowly scoped task that cites the affected goal and milestone, in priority order G1 > G2 > G3.
