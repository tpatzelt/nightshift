# Idle-phase G2 gap: home page links to stop search (T-0048)

_Recorded 20260930-060058 by the NIGHTSHIFT planner._

## Context
The backlog is empty and there are no worker followups. G1's definition of done is still blocked because live HAFAS recording does not work in this sandbox. The recording chain T-0016/T-0017/T-0018/T-0020-T-0022 stays parked until a human decides on network access. Reading /repo/mein-pendel showed that src/pendel/templates/index.html links to /today and /notifications but not to /stops. A visitor landing on '/' can only reach stop search, the first step of saving a commute, through the empty-state link on /today.

## Decision
Add T-0048 (G2/M2), limited to index.html, i18n.py and a new tests/test_web_home.py, with a 150-line cap. It reuses the existing 'stops_heading' translation key. Assumptions (the conservative reading): (1) a missing entry link to a G2 route counts as a small usability fix within G2, so it is allowed idle work and nothing new; (2) app.py, the other templates, fixtures and deploy files are protected; (3) the parked live-recording chain is not retried, and synthetic fixtures never count toward G1. No milestone is added. The planner made no live calls. One gap was noted but not scheduled: /today shows raw stop IDs instead of stop names. Fixing it would need a schema or lookup change, which is larger than idle work justifies right now.

## Consequences
A visitor can start the search → save → today flow from the home page, and a test keeps the link there in both languages. Still open, and each needs a human: (1) network access for live HAFAS recording, to unpark T-0020, then T-0016/T-0021/T-0022/T-0017 and T-0018, and meet G1's definition of done, the top-priority goal; (2) confirmation that deploy/verify.sh passes in CI; (3) real Impressum and Datenschutz details in place of the placeholders.
