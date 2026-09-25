# G1 artsy redesign: CSS tokens first, then generative background, parallax and typography

_Recorded 20260924-212302 by the NIGHTSHIFT planner._

## Context
The repo is a single-page Jekyll site: index.html, _layouts/default.html, style.css, main.js and cat-cursor.js. Its current theme is a deliberately plain black-and-white one. main.js computes parallax CSS variables that no CSS uses, and the .floating-shapes markup is hidden. The charter's test_cmd is empty, and Ruby/Jekyll are not available in the sandbox, so a full site build cannot be the acceptance gate. G1's definition of done is that the orchestrator accepts the design.

## Decision
Split G1 into four small tasks under M1. T-0001 adds palette and design tokens and is the base for the rest. T-0002 adds a generative ML-motif canvas background in a new file, assets/js/background.js. T-0003 wires the existing --bg-x/--bg-y/--bg-rot parallax variables into CSS. T-0004 art-directs the hero typography and interaction states. Acceptance uses only grep, test, node --check and python3 static checks, run from the repo root. new_tests_required is false because the charter defines no test harness and adding one does not serve G1. Protected paths: _config.yml (holds existing contact data), the CV, the cat sprite, CI/deploy files (deployment is a non-goal) and the Gemfiles.

## Consequences
["Acceptance commands are structural proxies (tokens exist, JS parses, braces balance, reduced-motion is honoured). They cannot judge aesthetics; that judgement stays with the orchestrator under G1's definition of done.", 'Assumptions: acceptance commands run with cwd set to the repo root, and node and python3 are available to workers.', 'T-0002, T-0003 and T-0004 all depend on T-0001, and T-0003 and T-0004 both edit style.css, so they should run one after the other.', "Content changes beyond decoration, such as new bio text or replacing the 'More info coming soon' card, are deliberately not scheduled: they would need personal data the charter forbids adding and that no one can supply while the owner is away."]
