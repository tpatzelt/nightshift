# Re-issue T-0040 as T-0041 with a test that can only pass because of the landing gate

_Recorded 20260923-224216 by the NIGHTSHIFT planner._

## Context
The backlog is empty. The G1 harness is merged. G3's done-criteria are covered by merged tasks: T-0010, T-0016, T-0024, T-0032, T-0033, T-0034 and T-0035. On today's tree, replaying offline_eval gives TOTAL posting_shape_rate 0.941 and aggregator_drop_rate 0.941, against arming baselines of 0.815 and 0.765. The other three metrics are at 1.000. The last kept non-posting is the whatjobs record https://de.whatjobs.com/jobs?id=261276305, and the merged find_landing_marker (T-0039) already detects it. T-0040 was the task that wired this signal into the orchestrator and the replay. The reviewer parked it only because its replay_keep test would still pass with the gate removed. The production and replay changes themselves were approved.

## Decision
Add T-0041 as a direct re-issue of T-0040 with depends_on: []. It keeps the approved scope, including the ImportError fallback needed by evals/rebaseline.py. Its acceptance now requires a POSTING-shaped, location-matching record with landing text that is dropped, next to a control record with the same URL that is kept, so the new gate is the only possible cause of the drop. Assumptions, chosen conservatively: evals/baseline.json and evals/fixtures/** are listed as protected so the measuring stick cannot move in the same change. max_diff_lines is set to 250, well under 800. No other tasks are scheduled this pass, because the remaining work is this one G2 slice and the charter allows only idle work beyond it.

## Consequences
If T-0041 merges, the replay should reach 1.000 on posting_shape_rate and aggregator_drop_rate. That is my prediction from replaying the corpus, not a verified result. No metric should regress, and G2's done-criteria would then be met by a margin. After that, only the charter's allowed idle work should be scheduled: tests, docs and small refactors within G1–G3. T-0040 stays parked and must not be revived alongside T-0041.
