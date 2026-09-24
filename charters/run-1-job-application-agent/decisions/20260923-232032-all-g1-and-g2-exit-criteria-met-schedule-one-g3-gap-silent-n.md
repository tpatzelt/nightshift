# All G1 and G2 exit criteria met; schedule one G3 gap (silent notification-delivery failure) and nothing else

_Recorded 20260923-232032 by the NIGHTSHIFT planner._

## Context
The backlog was empty. I replayed the current tree with `python -m evals.offline_eval`, using system python on a /tmp copy because `uv` cannot fetch wheels offline here. It exits 0, prints the table and writes report.json. Every metric in the TOTAL row is 1.000. The frozen baseline in evals/baseline.json is posting_shape 0.815, aggregator_drop 0.765, location 1.000, staleness 0.429 and dedup 0.571, so G2 improved and nothing regressed. The README documents all five metrics. For G3, the ledger (T-0024), within-call dedup (T-0035), the Why: line (T-0046) and send-boundary assertions for dispatch, intake, /run, no-new-jobs, scan-error and chunking (T-0032..T-0034, T-0045) are merged. One path is still silent. `Orchestrator._notify` drops `notify_results`' False return and swallows its exceptions, and `_run_scan` only messages the user on empty results, so when job delivery fails the user hears nothing. Every parked task is a superseded re-issue whose work has since merged. None needs reviving. I could not run pytest because pytest is not installed outside uv's venv, so the green-suite baseline is assumed from the merge gates.

## Decision
Add T-0047 (G3/M3). It counts notification failures in the RunReport and has the bot tell the user that undelivered jobs will be retried, which the ledger already guarantees. Scope is 4 existing files, the diff is capped at 200 lines, and it adds no new metric, dependency or live call. I read 'surface failures as actionable text' as covering a delivery failure that is logged but not raised. That is the conservative reading of G3 as written, and it does not extend it. I add no G1/G2 tasks: every harness metric is already at its ceiling on the labelled corpus, and further triage work would be unmeasurable.

## Consequences
Once T-0047 merges, M1–M3 exit criteria are all met and planning should schedule only the charter's allowed idle work: tests, docs and small refactors within G1–G3. If Telegram is fully down, the follow-up message may also fail. `_safe_send` already swallows that, so the change can only add information and never breaks a scan. The superseded parked tasks stay parked as a record and must not be revived.
