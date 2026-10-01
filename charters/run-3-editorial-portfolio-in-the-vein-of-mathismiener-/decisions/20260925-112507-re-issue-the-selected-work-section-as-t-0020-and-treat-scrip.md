# Re-issue the Selected work section as T-0020, and treat scripts/check-site.sh as the repo's test file

_Recorded 20260925-112507 by the NIGHTSHIFT planner._

## Context
T-0014 and T-0019 (projects from _data/projects.yml) are parked. T-0019 failed the new_tests_required gate because no test file changed, and T-0010 failed the same way earlier. The repo has no test suite other than scripts/check-site.sh. T-0018, which did add checks to check-site.sh, passed. G1's definition of done looks met: the page is light, set in Inter, and has no canvas or blobs, with checks 9 and 10 guarding that. G2 is the next priority. There is no _data/ directory yet.

## Decision
Re-issue the projects section as T-0020 with explicit notes. Adding a numbered check 11 to scripts/check-site.sh is required. Placeholder entries must be clearly marked and must leave out the optional keys. The section sits between About and Contact with h2/h3 headings. T-0015 (contact from data) gets the same instruction and depends on T-0020, because both edit index.html and check-site.sh. Queue order is T-0020, T-0015, T-0016, T-0017. Assumptions: (1) the gate counts a change to scripts/check-site.sh as a test change, as T-0018's pass suggests; (2) T-0014's truncated revise reason did not name any defect beyond what these notes cover; (3) no G1 work is left, so no new M1 task is added.

## Consequences
If the gate does not count check-site.sh as a test file, T-0020 will park again. The next planning pass should then set new_tests_required=false for this repo's data-rendering tasks and rely on the acceptance commands, which already include a mktemp negative test. G2 is done once T-0020 and T-0015 land (About, Selected work and Contact, with projects and contact rendered from data). G3 work (T-0016, T-0017) follows.
