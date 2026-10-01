# Retry parked T-0007 as T-0024 to unblock the G3 pipeline, and queue G2 save-commute and delete-my-data behind it

_Recorded 20260929-132152 by the NIGHTSHIFT planner._

## Context
The backlog had 3 ready tasks: T-0008, T-0009 and T-0014. All of them depend on T-0007, directly or through T-0008. T-0007 is parked after 2 attempts. Attempt 1 failed the gate on a credential-shaped test literal. Attempt 2 got 'revise' for two concrete problems: the Telegram bot token could leak through the httpx.HTTPStatusError URL, and the ntfy topic was not validated. src/pendel/notify/ does not exist in /repo/mein-pendel. So nothing in the backlog could run. G1's definition of done is still blocked on live recording, as the 20260929-125118 ADR records, and that needs a human decision. There were no worker followups.

## Decision
Add T-0024 (G3/M3). It re-scopes T-0007 unchanged and adds the reviewer's two fixes: a sanitized ChannelSendError raised with `from None` plus a token-not-in-error test, and topic validation. It also adds a note against token-shaped literals. T-0008 and T-0014 now depend on T-0024 instead of T-0007. T-0007 stays parked because IDs are never reused. Add T-0025 (save a commute with an opaque HttpOnly SameSite=Lax uid cookie, no password) and T-0026 (POST /me/delete). Both are G2/M2 and cover definition-of-done routes. The order is T-0024, T-0008, T-0014, T-0009, then T-0025, T-0026, following G1 > G3 > G2. Assumptions, taking the conservative reading: the reviewer's option to percent-encode the ntfy topic is resolved in favour of strict charset validation, because that is narrower. T-0026 serves G2's delete-my-data route and is cited as G2. G5's separate tested requirement is covered by the same test, but G5 is not marked done. The planner made no live calls.

## Consequences
The G3 chain can run again, ending in the simulated-morning definition-of-done test in T-0009. G2 now has save-commute and delete-my-data queued. 'Today on my route' is still unplanned and will follow once T-0025 fixes the storage API. G1's definition of done is still blocked on live HAFAS recording, which needs a human decision. G4 and G5 are still unplanned.
