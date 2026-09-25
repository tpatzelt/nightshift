# G1 backlog left empty: M1 design work is complete and waiting for orchestrator acceptance

_Recorded 20260924-222513 by the NIGHTSHIFT planner._

## Context
This planning pass found T-0001 to T-0005 all done and merged in tpatzelt.github.io (HEAD 3f4afe6). Nothing is in the backlog or parked, and there are no worker followups. The previous ADR (20260924-215358) said no more G1 work was planned after T-0005. I re-read the mounted repo to check. assets/css/style.css is fully tokenised: an ink background, violet, cyan and pink accents, and a 'ARTSY DARK THEME' header. It has focus-visible states, prefers-reduced-motion and forced-colors handling, and responsive breakpoints at 768px and 480px. The generative background.js and the parallax floating-shapes layer are in place. _layouts/default.html has the neural-net SVG favicon and the theme-color meta tag. cat-cursor.css has no hard-coded colours that clash with the palette. The only visible placeholder left is the 'More info coming soon...' status card in index.html.

## Decision
No tasks are added, updated, parked or reordered. M1 stays the only milestone for G1. G1's definition of done is 'claude orchestrator accepts it', and the planned design scope is delivered, so the next step is acceptance, not more work.

## Consequences
Assumptions: (1) Adding polish tasks with no followup, parked reason or reviewer feedback behind them would be scope invention. The conservative choice is to let the orchestrator judge the current design. (2) The 'More info coming soon' card is still not scheduled. Replacing it needs personal and biographical content that no one can supply while the owner is away, and the charter forbids adding personal data. (3) Small inconsistencies are noted but not scheduled. For example, body paints var(--bg-elevated) (#14172c) as its base while theme-color uses --bg (#0a0b14). A task should come only if the orchestrator's review raises them. (4) The charter's test_cmd is empty and there is no Jekyll build in the sandbox, so nothing new needs to be kept green. If the orchestrator rejects G1 or workers file followups, the next pass should add targeted tasks under M1, or add a new milestone under G1 if the feedback calls for a separate phase. If G1 is accepted, the charter defines no idle work, so the backlog should stay empty.
