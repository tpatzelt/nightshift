# Idle-phase G4 documentation: README covers running, configuration and test policy (T-0047)

_Recorded 20260930-054919 by the NIGHTSHIFT planner._

## Context
The backlog is empty and there are no worker followups. G1's definition of done is still blocked because live HAFAS recording does not work in this sandbox (T-0002, T-0015 and T-0020 each came back blocked twice). The recording chain T-0016/T-0017/T-0018/T-0020-T-0022 stays parked until a human decides on network access. G2-G5 already have their definition-of-done tests. Reading /repo/mein-pendel showed that README.md has only 11 lines: it names neither the uvicorn entrypoint, the scheduler runner or the Telegram poller, nor any of the eight variables in deploy/.pendel.env.example.

## Decision
Add T-0047 (G4/M4), limited to README.md and a new tests/test_readme.py with a 250-line cap. The test keeps the README's variable list in sync with the env example and checks that the three process entrypoints and DEPLOY.md are mentioned. Assumptions (the conservative reading): (1) this is documentation within G4, so it counts as allowed idle work and is nothing new; (2) the README must not claim that recorded real fixtures exist; (3) source, deploy files and fixtures are protected, so any discrepancy the worker finds becomes a followup rather than an edit; (4) the parked live-recording chain is not retried, and synthetic fixtures never count toward G1. No milestone is added. The planner made no live calls.

## Consequences
An operator can run and configure the app from the README alone, and the test catches a newly added env variable that is not documented there. Still open, and each needs a human: (1) network access for live HAFAS recording, to unpark T-0020, then T-0016/T-0021/T-0022/T-0017 and T-0018, and meet G1's definition of done, the top-priority goal; (2) confirmation that deploy/verify.sh passes in CI, since the sandbox cannot run Docker; (3) real Impressum and Datenschutz details in place of the placeholders.
