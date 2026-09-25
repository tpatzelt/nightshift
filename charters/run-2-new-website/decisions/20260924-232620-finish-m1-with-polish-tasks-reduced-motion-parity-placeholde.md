# Finish M1 with polish tasks: reduced-motion parity, placeholder copy, and token consistency

_Recorded 20260924-232620 by the NIGHTSHIFT planner._

## Context
T-0001 to T-0005 delivered the palette, the generative canvas, parallax shapes, the typography and the favicon. Reading the repo turned up three gaps. main.js ignores prefers-reduced-motion. index.html still has placeholder copy ('More info coming soon...'). The body base colour (--bg-elevated) doesn't match theme-color/--bg, and style.css has a dead .greeting rule. The charter test_cmd is empty and there is no Jekyll/bundle in the sandbox, so acceptance can only use node --check and grep.

## Decision
Add three small tasks, T-0006 to T-0008, each limited to one file under M1/G1. new_tests_required is false because the repo has no test harness and adding tooling would go beyond the charter. Assumptions: G1's done condition ('claude orchestrator accepts it') is not met until these gaps are closed. Microcopy must stay non-factual so it adds no personal data.

## Consequences
M1 should be ready for orchestrator acceptance once these land. No new milestone is added. If the orchestrator accepts G1 after this batch, later planning rounds should schedule only allowed idle work.
