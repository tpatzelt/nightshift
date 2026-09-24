# G1 and G2 met; schedule the last confirmed G3 silence gap

_Recorded 20260923-231921 by the NIGHTSHIFT planner._

## Context
Replaying the current tree gives 1.000 on every TOTAL metric: posting_shape, aggregator_drop, location_match, staleness and dedup. The arming baseline in evals/baseline.json was 0.815 / 0.765 / 1.000 / 0.429 / 0.571. The offline harness exits 0 and writes its report, the README documents the metrics, and the suite shows 357 passed, 1 skipped. On G3, the durable ledger (T-0024), within-call dedup (T-0035), the fallback 'Why:' line (T-0046), scan-error text (T-0032) and reply assertions (T-0033/34/45) are all merged. Reading the code turned up one path left: Orchestrator.run caches URLs before notifying and ignores notify_results' False return, and BotService._run_scan says nothing when results is non-empty. A Telegram delivery failure is therefore silent and the jobs are never retried.

## Decision
Add one small G3/M3 task, T-0047. The notifier exposes which results it could not deliver, and the bot sends one actionable message naming them. No G1/G2 work is scheduled because those goals meet their definition of done. Assumption, taking the conservative reading: the parked tasks were all re-issued and merged under later IDs, so none is revived. I am also not adding a message for the case where every result was suppressed by the ledger, because it is not a failure and the charter only requires failures to be surfaced.

## Consequences
Once T-0047 merges, every G3 definition-of-done item is covered, and later passes should schedule only the charter's allowed idle work (tests, docs, small in-scope refactors). The cache-before-notify ordering stays as it is, so the jobs are reported to the user but still not retried automatically. Changing that would alter orchestrator behaviour beyond this task.
