# Re-issue the last G3 silent-failure fix (undelivered job notifications) as T-0048; G1 and G2 remain met

_Recorded 20260923-232126 by the NIGHTSHIFT planner._

## Context
The backlog is empty. Two earlier planner passes recorded an ADR scheduling T-0047 for this same gap, but T-0047 is not in /plan/backlog, /plan/done or /plan/parked, so like T-0037, T-0041 and T-0044 it never reached the backlog. I re-read the current tree (HEAD fc06634). src/orchestrator.py `_notify` still drops notify_results' False return and swallows exceptions, and src/bot_service.py `_run_scan` still sends a message only for empty results, so the gap is still open. Orchestrator.run also saves seen URLs to the cache before `_notify`, so undelivered jobs are not re-found on a later scan. I could not re-run the offline harness in this pass: uv cannot create a .venv on the read-only mount. Earlier passes recorded the TOTAL row at 1.000 on every metric against the frozen baseline in evals/baseline.json (posting_shape 0.815, aggregator_drop 0.765, location 1.000, staleness 0.429, dedup 0.571), and no src change has merged since except T-0046, which touches only notifier formatting. I rely on those recorded results.

## Decision
Add one G3/M3 task, T-0048, under a new ID so it cannot collide with the missing T-0047. The orchestrator counts notification failures in its RunReport, and the bot sends one message naming Telegram delivery as the failure. Conservative choice: the message must not promise an automatic retry, because the cache ordering means none happens, and changing that ordering would change orchestrator behaviour beyond this task. The scope is 5 existing files, the diff is capped at 250 lines, and there is no new dependency or live call. No G1 or G2 task is added because both meet their definition of done, and every parked task is a superseded re-issue whose work has since merged, so none is revived.

## Consequences
Once T-0048 merges, every G3 definition-of-done item has a test, and later passes should schedule only the charter's allowed idle work: tests, docs and small in-scope refactors. If Telegram is fully down, the failure message may fail too. `_safe_send` already swallows that, so a scan can never break. If T-0048 also fails to appear in the backlog, the next pass should report that as a planner/runner integration problem instead of re-issuing it a third time.
