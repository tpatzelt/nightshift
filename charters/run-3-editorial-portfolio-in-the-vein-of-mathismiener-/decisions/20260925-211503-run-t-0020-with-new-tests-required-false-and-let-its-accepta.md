# Run T-0020 with new_tests_required=false and let its acceptance commands enforce the check-site.sh regression test

_Recorded 20260925-211503 by the NIGHTSHIFT planner._

## Context
T-0010 and T-0019 were each parked twice by 'new_tests_required is set but no test file was added or changed'. The only task that passed after adding checks to scripts/check-site.sh was T-0018, and it ran with new_tests_required=false. So the earlier assumption that the gate counts check-site.sh as a test file has never been confirmed. T-0020 still carries new_tests_required=true and a note saying the gate bug 'is fixed', which nothing supports. G1 is met (light Inter theme, no canvas or blobs, guarded by checks 9-10). G2 is the current priority, and index.html has About and Contact but no projects section and no _data/ directory.

## Decision
Set new_tests_required=false on T-0020 before its first attempt, as the previous ADR's fallback said. Rewrite its notes to drop the unverified 'gate bug fixed' claim and to keep requiring step 11 in check-site.sh. That requirement is enforced by the existing acceptance commands: a grep for '_data/projects.yml' in check-site.sh, and a mktemp copy with the data file removed that must fail. Keep the queue order T-0020, T-0015, T-0016, T-0017. Assumptions: (1) the gate's notion of a 'test file' does not include scripts/check-site.sh, which the history supports; (2) T-0014's truncated revise reason named no defect beyond what these notes cover; (3) T-0015, T-0016 and T-0017 already have new_tests_required=false and need no change; (4) no G1 work is left.

## Consequences
T-0020 should no longer park on the test-file gate, and the regression check is still required by its acceptance commands. G2's definition of done should be met once T-0020 and T-0015 land. That gives three sections beyond the hero (About, Selected work, Contact), with projects and contact rendered from _data. The About copy and the project entries stay clearly-marked placeholders until Tim supplies real facts. G3 (T-0016, T-0017) follows. If T-0020 is parked again for a reviewer reason, the next pass should re-issue it with that reason in its notes.
