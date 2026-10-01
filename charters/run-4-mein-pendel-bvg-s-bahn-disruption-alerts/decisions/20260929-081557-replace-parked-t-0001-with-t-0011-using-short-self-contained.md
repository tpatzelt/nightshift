# Replace parked T-0001 with T-0011 using short, self-contained notes

_Recorded 20260929-081557 by the NIGHTSHIFT planner._

## Context
T-0001 (HAFAS client) was parked after two 'revise' reviews. Each review note was cut off at about 600 characters, both in the backlog YAML and in the worker's TASK.md. The worker never saw issues (2)-(4) from attempt 1, and the attempt-2 reviewer could not recover them either. The one visible fragment of issue (A) says the cache only grows, and it mentions departures calls keyed by `when`. Nothing from T-0001 was merged: the repo has no src/pendel/hafas. T-0002 and T-0004 depend on T-0001, so the whole G1 chain was blocked.

## Decision
Leave T-0001 parked, since IDs are never reused, and add T-0011 with the same scope and paths. Its notes are short and each stays well under the cut-off length. They state the missing requirements outright: a bounded cache with TTL eviction, a max_entries cap tested with many distinct `when` values, an injected clock, Retry-After handling, a typed error, no retry on other errors, and a test for the socket guard. T-0002 and T-0004 now depend on T-0011. Assumption, taking the conservative reading: the lost issues (2)-(4) are not recoverable, so T-0011 covers them with explicit, testable requirements and does not guess at their exact wording. The G1 → G3 → G2 order is unchanged.

## Consequences
The G1 chain is unblocked and T-0011 is ranked first. If the review again finds problems that the notes do not cover, reviewers should write short, separate notes so they are not cut off. Truncated reviewer feedback is a pipeline problem outside the charter; it is recorded here but not worked around.
