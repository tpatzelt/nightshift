# Idle-phase G2 gap: the footer language switch keeps the visitor on the current page (T-0050)

_Recorded 20260930-070327 by the NIGHTSHIFT planner._

## Context
The backlog is empty and there are no worker followups. G1's definition of done is still blocked because live HAFAS recording does not work in this sandbox. The recording chain T-0016/T-0017/T-0018/T-0020-T-0022 stays parked until a human decides on network access. G2-G5 already have their definition-of-done tests. Reading /repo/mein-pendel showed that base.html's footer language switch always links to '/?lang=..', even though every GET page route in app.py already handles ?lang= and sets the cookie. The T-0049 ADR recorded this as a known gap.

## Decision
Add T-0050 (G2/M2), limited to src/pendel/templates/base.html and tests/test_web_language.py, with a 150-line cap. app.py, i18n.py and all backend modules are protected. Assumptions (the conservative reading): (1) keeping the visitor on the same page when switching between the two UI languages completes G2's bilingual requirement, so it is allowed idle work (accessibility and small refactors within G2) and adds nothing new; (2) the link uses only the request path, only for GET requests, and never a path starting with '//', so no open protocol-relative link can appear; POST re-renders fall back to '/'; (3) other query parameters are dropped rather than adding app.py code; (4) the parked live-recording chain is not retried, and synthetic fixtures never count toward G1. No milestone is added. The planner made no live calls. Gap noted but not scheduled: /today shows raw stop IDs, because fixing it needs a schema or lookup change that is larger than idle work justifies.

## Consequences
A visitor who switches language on any GET page stays on that page, and tests keep that behaviour in place, including the POST fallback. Still open, and each needs a human: (1) network access for live HAFAS recording, to unpark T-0020, then T-0016/T-0021/T-0022/T-0017 and T-0018, and meet G1's definition of done, the top-priority goal; (2) confirmation that deploy/verify.sh passes in CI, since the sandbox cannot run Docker; (3) real Impressum and Datenschutz details in place of the placeholders.
