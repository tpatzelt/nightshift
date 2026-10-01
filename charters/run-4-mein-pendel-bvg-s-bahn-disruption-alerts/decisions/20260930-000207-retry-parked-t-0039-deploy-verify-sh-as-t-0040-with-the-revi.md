# Retry parked T-0039 (deploy/verify.sh) as T-0040 with the reviewer's DEPLOY.md step-reference fix; G1 stays blocked on live recording

_Recorded 20260930-000207 by the NIGHTSHIFT planner._

## Context
The backlog is empty. T-0039 was parked after its second attempt. The reviewer approved the script, the CI gating and the tests, and found one defect: after a verify step was inserted, the DEPLOY.md intro still said the homelab snippets are in 'steps 6 and 7'. The repo confirms none of T-0039 landed: there is no deploy/verify.sh and ci.yaml has no verify job. G2, G3 and G5 meet their definitions of done in code and tests (per the 20260929-235411 ADR, and T-0038 is now done). G1 still needs at least five recorded real disruption kinds, and live recording is blocked in this sandbox (T-0016/T-0017/T-0018/T-0020–T-0022 parked).

## Decision
Add T-0040 (G4/M4). It is T-0039 with the same scope, allowed and protected paths, plus explicit notes: fix the intro step references, add a test that keeps them in sync with the numbered Caddy/cloudflared steps, make the Docker-by-human sentence truthful, and repeat the no-'|| true' gate rule from attempt 1. max_diff_lines goes from 300 to 350 to fit the extra test. No other tasks are added. Assumptions, taking the conservative reading: a check run in CI or by the human is the closest the sandbox allows to 'inside the sandbox', and the gap is reported rather than worked around. PyYAML stays a runtime-only tool of the script, not a project dependency. Synthetic fixtures never count toward G1.

## Consequences
Once T-0040 lands, every G4 check runs in CI and gates publishing. Still open and needing a human: (1) network access for live HAFAS recording, which would unpark T-0020, then T-0016/T-0021/T-0022/T-0017 and T-0018, for G1, the top-priority goal; (2) confirming that deploy/verify.sh passes, since the sandbox cannot run Docker; (3) real Impressum details in place of the placeholders. After T-0040, and until (1) is resolved, only the charter's allowed idle work remains.
