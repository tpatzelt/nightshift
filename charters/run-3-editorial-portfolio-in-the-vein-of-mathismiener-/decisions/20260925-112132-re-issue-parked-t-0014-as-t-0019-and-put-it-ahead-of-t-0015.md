# Re-issue parked T-0014 as T-0019 and put it ahead of T-0015

_Recorded 20260925-112132 by the NIGHTSHIFT planner._

## Context
G1 looks met: T-0011, T-0012 and T-0018 are done, and check-site.sh checks 9 and 10 keep the canvas, blobs and cat cursor out. G2 is next by priority. index.html has only About and Contact and there is no _data directory, so a third, data-driven section is still missing. T-0014 passed every gate, but a reviewer marked it 'revise' and the stored reason is cut off, so the exact remaining complaint is unknown.

## Decision
Add T-0019 to redo T-0014 with the reviewer's positive points written into its notes and the check renumbered to step 11. Make T-0015 depend on T-0019 because both edit index.html and check-site.sh. Order the backlog T-0019, T-0015, T-0016, T-0017 to follow G1→G2→G3. Assumption: the cut-off reason was a minor revision, not a charter violation, so the most conservative move is a faithful re-issue rather than a change of scope.

## Consequences
Once T-0019 and T-0015 land, G2's definition of done should be met. If T-0019 is parked again for the same unclear reason, the next planning pass should split it into two tasks: the data file plus its check, then the markup. The G3 tasks stay queued after G2. The Google Fonts link in the layout is a G3 concern (it is still only the one family) and is left for T-0016 and T-0017 to judge.
