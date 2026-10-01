# Idle-phase G2 accessibility: error messages use role="alert" and the footer nav gets a label (T-0049)

_Recorded 20260930-063208 by the NIGHTSHIFT planner._

## Context
The backlog is empty and there are no worker followups. G1's definition of done is still blocked because live HAFAS recording does not work in this sandbox. The recording chain T-0016/T-0017/T-0018/T-0020-T-0022 stays parked until a human decides on network access. G2-G5 already have their definition-of-done tests. Reading /repo/mein-pendel showed four error paragraphs (stops.html, commute_new.html, and two in notifications.html) without role="alert", so screen readers do not announce them after a failed submit. It also showed that the footer <nav> in base.html has no accessible name, and that the .error class has no style in style.css.

## Decision
Add T-0049 (G2/M2), limited to four templates, i18n.py, style.css and a new tests/test_web_a11y.py, with a 200-line cap. app.py and all backend modules are protected. Assumptions (the conservative reading): (1) accessibility within G2 is named explicitly in the charter's allowed idle work, so this adds nothing new; (2) the new footer_nav_label key is added in both DE and EN to keep the UI bilingual; (3) the CSS change is one colour rule with no fixed widths, so the 360px structure tests stay valid; (4) the parked live-recording chain is not retried, and synthetic fixtures never count toward G1. No milestone is added. The planner made no live calls. Gaps noted but not scheduled: /today shows raw stop IDs, and the footer language switch always goes to '/' instead of the current page.

## Consequences
Screen-reader users hear why a stop search, commute save or ntfy save failed, and the footer navigation has a name in both languages. A test keeps both in place. Still open, and each needs a human: (1) network access for live HAFAS recording, to unpark T-0020, then T-0016/T-0021/T-0022/T-0017 and T-0018, and meet G1's definition of done, the top-priority goal; (2) confirmation that deploy/verify.sh passes in CI, since the sandbox cannot run Docker; (3) real Impressum and Datenschutz details in place of the placeholders.
