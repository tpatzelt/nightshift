# All goals are done; queue one test-only accessibility guard as idle work

_Recorded 20261001-060045 by the NIGHTSHIFT planner._

## Context
The backlog is empty, and every goal's definition-of-done task is recorded as done (G1 T-0006, G3 T-0049, G2 T-0034, G5 T-0040, G4 T-0045/46/51/52). T-0054 has documented the visitor flows in the README. There are no worker followups. Parked T-0015, T-0016, T-0033, T-0039 and T-0048 have each been superseded by a done re-issue and stay parked as history. I read the templates: the form controls in commute_new.html, stops.html and notifications.html have labels (label-for or a wrapping label, with checkbox groups in a fieldset and legend). tests/test_web_a11y.py only covers role=alert and the footer nav's aria-label, so nothing guards the labels. I could not run the suite this turn because /repo is read-only and uv cannot create .venv there. The previous planner reported 481 passed, offline.

## Decision
Under 'Allowed idle work' (tests, accessibility), add milestone M8 [G4] and one task, T-0055. It only adds tests to tests/test_web_a11y.py, asserting that every visible form control on /stops, /commutes/new, the edit page and /notifications is labelled, in DE and EN. src/** and the fixtures are protected. If the test finds a real gap, the worker marks it xfail and reports a followup; it does not edit templates. No fixture recording, because it needs the rate-limited public API and a cheaper safe test task exists. Assumption: label coverage counts as G4 accessibility work rather than a new feature. Assumption: the test should not cover /today, because its cards hold no form controls.

## Consequences
The queue holds one low-risk task that cannot change runtime behavior. If it raises a followup about an unlabelled control, the next planner can schedule a small template fix under G4. After that the backlog may stay empty, or take further idle work such as recorded fixtures of other disruption kinds.
