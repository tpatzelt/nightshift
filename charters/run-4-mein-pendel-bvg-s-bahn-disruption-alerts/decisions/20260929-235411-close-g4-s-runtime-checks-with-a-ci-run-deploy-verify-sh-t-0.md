# Close G4's runtime checks with a CI-run deploy/verify.sh (T-0039); G1 stays blocked on live recording

_Recorded 20260929-235411 by the NIGHTSHIFT planner._

## Context
The backlog was empty. G2, G3 and G5 meet their definitions of done in code and tests: routes are tested with TestClient and have 360px viewport tests, the simulated-morning scheduler test includes the resolved message, the Telegram linking flow is tested against a fake, the legal pages are linked in the footer, and delete and 429 are tested. G1 is still blocked. Its definition of done needs at least five recorded real disruption kinds, and live HAFAS recording fails in this sandbox (T-0016/T-0017/T-0018/T-0020–T-0022 parked). G4 has static text tests only. Nothing builds the image, checks the container's healthcheck, runs compose config or parses the workflow as YAML. The NIGHTSHIFT guard blocks every Docker call and every command that mentions Docker for agents, including this planner.

## Decision
Add T-0039 (G4/M4). It adds deploy/verify.sh, which runs compose config against a temp copy of the example env, parses YAML with PyYAML pulled in only at script runtime (no new project dependency), builds the image, and waits for the container to report healthy with no host ports and all channel variables empty. A `verify` CI job runs it and gates build-and-push. DEPLOY.md documents it, and static tests guard it. Assumptions, taking the conservative reading: a check run in GitHub Actions or by the human does not literally meet 'inside the sandbox', but it is the closest thing the sandbox allows, and the gap is reported rather than worked around. PyYAML is kept out of pyproject.toml because the charter prefers minimal dependencies and workers may not be able to reach PyPI. No synthetic fixture is allowed to count toward G1.

## Consequences
Once T-0039 lands, every G4 check runs on each push to main and blocks publishing if it fails. The human can also run the same script locally. Still open and needing a human: (1) network access for live HAFAS recording, which would unpark T-0020, then T-0016/T-0021/T-0022/T-0017 and T-0018 for G1, the top-priority goal; (2) confirming that deploy/verify.sh passes, since the sandbox cannot run Docker; (3) filling in real Impressum details in place of the placeholders. After T-0039, and until (1) is resolved, only the charter's allowed idle work remains.
