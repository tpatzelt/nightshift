# Idle-phase G2 gap: a visible language switch in the footer (T-0045)

_Recorded 20260930-044621 by the NIGHTSHIFT planner._

## Context
The backlog is empty and there are no worker followups. G1's definition of done is still blocked. Live HAFAS recording has failed in this sandbox (T-0002, T-0015 and T-0020 were each blocked twice), and the recording chain T-0016/T-0017/T-0018/T-0020–T-0022 stays parked until a human decides on network access. G3, G2, G4 and G5 have their definition-of-done tests in place, and T-0044 closed the two-step stop search. Reading /repo/mein-pendel turned up one more G2 gap. The UI language comes only from ?lang=, a lang cookie or Accept-Language (app.py _language_for), and base.html's footer has no visible way to switch. A visitor whose browser sends a German locale can never see the English UI unless they type a query parameter, which undercuts G2's 'German and English UI'.

## Decision
Add T-0045 (G2/M2). The footer in base.html gets one link to '/?lang=en' or '/?lang=de', with its label in i18n.py, plus a new test file tests/test_web_language.py. The diff is capped at 150 lines, app.py is protected, and nothing needs JS, a dependency or a schema change. Assumptions (the conservative reading): (1) this completes behaviour G2's goal text already requires, so it counts as allowed idle work ('accessibility and small refactors strictly within G1–G5') and is nothing new; (2) the link goes to the home route, which already persists the choice in the cookie, rather than to the current path, so no route code changes; (3) the parked live-recording chain is not retried, because repeating a probe known to be blocked would only burn attempts; (4) synthetic fixtures never count toward G1. No milestone is added, since M2 covers this. The planner made no live calls.

## Consequences
Once T-0045 is done, every page offers a one-tap switch between German and English that persists through the cookie. Still open, and each needs a human: (1) network access for live HAFAS recording, to unpark T-0020, then T-0016/T-0021/T-0022/T-0017 and T-0018, and meet G1's definition of done, the top-priority goal; (2) confirmation that deploy/verify.sh passes in CI, since the sandbox cannot run Docker; (3) real Impressum and Datenschutz details in place of the placeholders. Until (1) is resolved, only further allowed idle work remains.
