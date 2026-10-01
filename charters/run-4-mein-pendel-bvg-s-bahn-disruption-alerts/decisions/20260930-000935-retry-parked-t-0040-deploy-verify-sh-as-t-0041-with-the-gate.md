# Retry parked T-0040 (deploy/verify.sh) as T-0041, with the gate's pipe-true rule stated so no diff line trips it

_Recorded 20260930-000935 by the NIGHTSHIFT planner._

## Context
The backlog is empty. T-0040 was parked after two attempts. Both failed the same gate check, and on a test line, not the script: `assert "|| true" not in VERIFY_SH`. The gate pattern-matches every added diff line, so a test meant to prove the forbidden sequence is absent tripped the gate itself. The repo confirms nothing from T-0039/T-0040 landed: there is no deploy/verify.sh, ci.yaml has only the test and build-and-push jobs, and the DEPLOY.md intro still says 'steps 6 and 7' and that a human must run the Docker checks. G2, G3 and G5 are done in code and tests (T-0023–T-0038). G1 is still blocked on live HAFAS recording (T-0016/T-0017/T-0018/T-0020–T-0022 parked).

## Decision
Add T-0041 (G4/M4). It has T-0040's scope, paths and budget (max_diff_lines 350). The first note now explains the gate rule and says three things: never write the sequence anywhere in the diff, including tests, do not test for its absence, and self-check with `git diff | grep -F`. The cleanup uses `set +e` and an `if docker inspect` guard instead of `||`. Assumptions, taking the conservative reading: dropping the absence test loses no charter coverage, since the gate already enforces the rule. Running the checks in CI or by the human is the closest the sandbox allows to 'inside the sandbox', and the gap is reported rather than worked around. PyYAML stays an ephemeral tool of the script, not a project dependency. Synthetic fixtures never count toward G1.

## Consequences
Once T-0041 lands, every G4 check runs in CI and gates publishing. Still open and needing a human: (1) network access for live HAFAS recording, which would unpark T-0020, then T-0016/T-0021/T-0022/T-0017 and T-0018, for G1, the top-priority goal; (2) confirming that deploy/verify.sh passes, since the sandbox cannot run Docker; (3) real Impressum details in place of the placeholders. After T-0041, and until (1) is resolved, only the charter's allowed idle work remains.
