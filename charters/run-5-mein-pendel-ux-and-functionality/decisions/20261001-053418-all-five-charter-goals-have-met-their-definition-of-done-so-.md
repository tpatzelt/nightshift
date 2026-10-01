# All five charter goals have met their definition of done, so only a single idle documentation task is queued

_Recorded 20261001-053418 by the NIGHTSHIFT planner._

## Context
The backlog is empty. The definition-of-done tasks are all done: G1 T-0006, G3 T-0049, G2 T-0034, G5 T-0040, and G4 T-0045/T-0046/T-0051/T-0052. A read-only copy of the repo passes uv run pytest -q (481 passed, offline). The code has every route the charter names: /commutes/new, /commutes with edit, pause, resume and delete, /today, and /notifications with unlink and test. Migrations 0001–0003 are present, along with the manifest, icons and the dark-mode block. There are no worker followups. Parked T-0015, T-0016, T-0033, T-0039 and T-0048 were each superseded by a done re-issue (T-0049, T-0031, T-0050, T-0053, T-0051/T-0052). README.md still labels the processes with goal numbers from an earlier charter ('G2: the web app', 'G3: the scheduler', 'charter G4'). It also does not describe the visitor flows the run built.

## Decision
Under 'Allowed idle work', schedule only documentation. Add milestone M7 [G1] and one small task, T-0054. It fixes the stale goal labels in the README and adds a short 'Using Mein Pendel' section covering the guided setup (G1) and the /commutes, /today and /notifications pages. A test in tests/test_readme.py guards both changes. src/** and everything else are protected. No new features. No fixture recording, because that would need the rate-limited public API, and documentation is the cheapest safe idle work. The parked tasks stay parked as history. Assumption: a docs task that covers several goals' pages may cite G1 alone, since the charter allows one goal per task and the guided setup is its main subject. Assumption: goal labels inside test-file docstrings are left alone, to avoid restructuring that no task requires.

## Consequences
The queue holds one low-risk, test-backed docs task that cannot change runtime behavior. When it is done and no followups arrive, the next planner can queue further idle work (recorded fixtures of other real disruption kinds, accessibility checks) or leave the backlog empty. No migration, dependency, network or channel contact is involved.
