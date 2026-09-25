# G1 backlog stays empty after T-0008: M1 is delivered and waits for orchestrator acceptance

_Recorded 20260924-235721 by the NIGHTSHIFT planner._

## Context
I found T-0001 to T-0008 all done. The backlog is empty, nothing is parked and there are no worker followups. I re-read the mounted repo tpatzelt.github.io. assets/css/style.css is fully tokenised and body now uses var(--bg) as its base, matching theme-color and the favicon. The dead .greeting rule is gone. prefers-reduced-motion and forced-colors are handled in style.css, background.js and main.js. index.html has ML-flavoured microcopy ('status: training · epoch ∞ …', 'Compiled with ♥ and gradient descent') with no placeholders left. _layouts/default.html has the neural-net SVG favicon and the theme-color meta tag. One small gap remains. cat-cursor.js runs its requestAnimationFrame flying loop, which sets an inline rotate transform, even when the user prefers reduced motion. cat-cursor.css pins left/top in that case but does not override transform, so the cat stays in place but keeps rotating.

## Decision
I added, updated, parked and reordered no tasks. M1 stays the only milestone for G1. The previous ADR (20260924-232620) said M1 would be ready for acceptance once T-0006 to T-0008 landed, and they have. G1's definition of done is 'claude orchestrator accepts it', so the next step is acceptance, not more work.

## Consequences
Assumptions: (1) Adding tasks with no followup, parked reason or reviewer feedback behind them would be scope invention. The conservative choice is to let the orchestrator judge the current design. (2) The cat-cursor.js reduced-motion rotation gap is recorded here but not scheduled. If the orchestrator or a followup raises it, the right fix is one task limited to assets/js/cat-cursor.js, modelled on T-0006: check matchMedia('(prefers-reduced-motion: reduce)') and skip the flying rAF loop, with node --check and grep as acceptance. (3) The charter's test_cmd is empty and the sandbox has no Jekyll/bundle, so there is nothing more to keep green. (4) The charter defines no idle work. If G1 is accepted, the backlog stays empty. If G1 is rejected, the next pass should turn the rejection reasons into small tasks under M1, or under a new G1 milestone if the feedback calls for a separate phase.
