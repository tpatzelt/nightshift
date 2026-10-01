# Human: G1 done — real recorded fixtures landed; the parked recording chain is closed

_Recorded 20260930-073500 by Tim (via Claude Code), not the planner._

## Context
The recording chain was parked as a sandbox network block. It was not one: egress to v6.bvg.transport.rest works. On 2026-09-29 the public instance itself was down (Redis MISCONF, then 503), and T-0020's single request used a stop id that does not exist (900000100001). Real stop ids are 9 digits: Alexanderplatz 900100003, Friedrichstr. 900100001, Hauptbahnhof 900003201, Ostkreuz 900120003, Westkreuz 900024102, Zoo 900023201.

## Decision
Committed directly on agent/integration (7fece10, ff851eb): six real recorded departures fixtures under tests/fixtures/hafas/recorded/ (undisturbed, cancellation, delay, replacement_service, construction, warning) with a provenance README, scripts/record_fixtures.py, and tests/test_engine_recorded.py (table-driven, two false-positive cases). Real data exposed three engine bugs that are now fixed and tested: child stop ids were dropped by an exact stop.id match, English remarks ("Replacement service") were not classified, and HTML entities leaked into reasons. Deploy docs now use container_name pendel-web and the homelab's Caddy/cloudflared shapes.

T-0002, T-0015, T-0016, T-0017, T-0018, T-0020, T-0021 and T-0022 are superseded and must not be revived. G1's definition of done is met. deploy/verify.sh was run on the host and passes.

## Consequences
Every goal's definition of done is met. Do not add more idle polish; let the run finish.
