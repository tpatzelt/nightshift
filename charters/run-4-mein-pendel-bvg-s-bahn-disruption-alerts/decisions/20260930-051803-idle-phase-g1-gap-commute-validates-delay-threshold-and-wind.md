# Idle-phase G1 gap: Commute validates delay threshold and window order (T-0046)

_Recorded 20260930-051803 by the NIGHTSHIFT planner._

## Context
The backlog is empty and there are no worker followups. G1's definition of done is still blocked: live HAFAS recording has been blocked in this sandbox (T-0002, T-0015 and T-0020 were each blocked twice), and the recording chain T-0016/T-0017/T-0018/T-0020-T-0022 stays parked until a human decides on network access. G2-G5 have their definition-of-done tests in place. Reading /repo/mein-pendel showed that Commute.__post_init__ validates only lines and weekdays. POST /commutes therefore saves a negative delay_threshold_min, which makes evaluate() flag every on-time departure (a false positive for G1). It also saves a window_end earlier than window_start, which gives an empty window, so the commute is never affected and never gets an alert.

## Decision
Add T-0046 (G1/M1), limited to commute.py and two existing test files with a 150-line cap: reject delay_threshold_min < 0 and window_end < window_start with ValueError. app.py already maps that error to a 400 form response and stays protected. Assumptions (the conservative reading): (1) this is a small refactor and tests strictly within G1, so it counts as allowed idle work and is nothing new; (2) windows that cross midnight are not supported by window_bounds today, so rejecting them adds no feature and removes nothing that works; (3) no deployment exists yet, so no stored rows can hold the now-invalid values, and the scheduler's per-commute error isolation from T-0027 would contain any that did; (4) the parked live-recording chain is not retried, and synthetic fixtures never count toward G1. No milestone is added. The planner made no live calls.

## Consequences
Invalid commutes are refused at save time instead of causing constant false alerts or never alerting at all. Still open, and each needs a human: (1) network access for live HAFAS recording, to unpark T-0020, then T-0016/T-0021/T-0022/T-0017 and T-0018, and meet G1's definition of done, the top-priority goal; (2) confirmation that deploy/verify.sh passes in CI, since the sandbox cannot run Docker; (3) real Impressum and Datenschutz details in place of the placeholders.
