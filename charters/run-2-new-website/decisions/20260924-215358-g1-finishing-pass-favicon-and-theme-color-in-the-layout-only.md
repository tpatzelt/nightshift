# G1 finishing pass: favicon and theme-color in the layout only

_Recorded 20260924-215358 by the NIGHTSHIFT planner._

## Context
All four planned M1 tasks are done: palette tokens (T-0001), generative canvas background (T-0002), pointer parallax layer (T-0003) and hero typography with interaction states (T-0004). I read the repo. style.css is fully tokenised. cat-cursor.css and cat-cursor.js contain no hard-coded colours that clash. Focus and reduced-motion styles are present. The one visible gap left in the design is browser chrome: _layouts/default.html has no favicon and no theme-color. There are no worker followups and nothing is parked.

## Decision
Add one small task, T-0005, under M1/G1. It adds an inline data-URI SVG favicon with a neural-net motif in the palette colours, plus <meta name="theme-color" content="#0a0b14">. The worker edits only _layouts/default.html. Acceptance commands are grep checks that also confirm the existing scripts and {{ content }} are still there. No new milestone is added: M1 covers G1 until the orchestrator accepts the design.

## Consequences
Assumptions: (1) The favicon goes inline as a data URI so the task edits only an existing file, because allowed_paths must name existing files. (2) The theme-color value is hard-coded to the current --bg (#0a0b14); if the palette changes, this tag must change with it. (3) The charter's test_cmd is empty and Jekyll is not in the sandbox, so acceptance stays structural. (4) As before, content changes such as replacing the 'More info coming soon' card are still not scheduled, because they would need personal data that no one can supply while the owner is away. After T-0005 no further G1 work is planned. The next planning pass should treat G1 as ready for orchestrator acceptance unless feedback or followups come in.
