# Run 4 — Mein Pendel: BVG/S-Bahn disruption alerts

Armed 2026-09-29T08:05:06+0200, finished 2026-09-30T08:36:14+0200 (charter complete: 3 planner runs added nothing).
Charter: [CHARTER.md](CHARTER.md) · roadmap: [ROADMAP.md](ROADMAP.md) · planner reasoning: [decisions/](decisions/) · digests: [digests/](digests/) · cost ledger: [usage.jsonl](usage.jsonl).

## Outcome

Goals: G1, G2, G3, G4, G5.

- merged: **32** (G1 6, G2 10, G3 10, G4 4, G5 2)
- parked: 18
- backlog left: 0
- agent runs: 203
- estimated spend: **$68.44**

## Where the work is

Each project's `agent/integration` is tagged `nightshift/run-4` in its bare repo:

```bash
git -C ~/coding/mein-pendel fetch ~/nightshift/data/repos/mein-pendel.git nightshift/run-4:tp/nightshift-run4   # ff851eb
```

## Merged and deployed

`nightshift/run-4` (`ff851eb`) is `main` by fast-forward and was the first version of
Mein Pendel to go public: CI run `36684814794` (2026-09-30 07:37 UTC, green in 1m31s)
published `ghcr.io/tpatzelt/mein-pendel:latest`, and homelab `3bc818b` added the
`compose/pendel` stack (web, scheduler, telegram) behind Caddy and the tunnel at
`pendel.<domain>`.

The tag's last two commits are not the loop's. The run's own last merge is `5082a32`
(T-0050). On top of it sit two commits by hand, made on the integration branch while
the run was still idling out:

- `7fece10` recorded the six real HAFAS fixtures that the run could not record itself
  (item 2), and **fixed three engine bugs that the real data exposed at once**. The
  engine had passed every table-driven test over synthetic fixtures.
- `ff851eb` brought DEPLOY.md's Caddy and cloudflared snippets in line with how the
  homelab actually does it.

A third fix, `2f43bbf` (match commute lines ignoring case and spaces), was pushed to
`main` at 09:59 UTC the same morning and went green in CI, but the host was never
re-pulled. It stayed undeployed for 20 hours, until run 5's deploy picked it up.

## What to fix next

_Written by hand after reviewing the branch._

1. **The public site serves placeholder legal pages.** This needs Tim, not the loop.
   `/impressum` renders `[NAME]`, `[ADRESSE]` and `[E-MAIL]`, and `/about` renders
   `[PLACEHOLDER]` for the Ko-fi link. That is exactly what G5 asked for ("placeholders
   for Tim's details"), and it has been public since this run's deploy. A German site
   reachable from a Reddit post needs a real Impressum under § 5 DDG before that post
   goes up. This is run 3's item 1 again: "correctly marked as missing" made it to
   production because nothing blocks a bracketed placeholder. Fill
   `src/pendel/templates/impressum.html` from an env var or by hand, and add a test
   that `/impressum` and `/about` render no `[UPPERCASE]` token.
2. **The charter promised network access that the sandbox took away.** The charter says
   "the sandbox can reach v6.bvg.transport.rest. Use it to record fixtures", and egress
   *was* open. But the guard denies curl and wget, and the agents read that as "no
   network". A planner check was stopped with "network tools are not available in
   the sandbox". The live-recording chain therefore parked **8 of the run's 18 tasks**:
   T-0002, T-0015 and T-0020 were each blocked twice, and T-0016, T-0017, T-0018, T-0021
   and T-0022 were parked upstream without ever running. G1's definition of done (five
   real disruption kinds) was only met by `7fece10` by hand. That commit also added
   `scripts/record_fixtures.py`, a Python recorder that does not go through the guard.
   In run 5, T-0056 used it to record a real platform-change fixture on its own, so
   the path now exists. What is still missing is a way for a charter to say which
   network path agents are meant to use.
3. **The run's first parks were orchestrator bugs, fixed mid-run in `6e0f6b0`.** The
   guard blocked `Read` of `.nightshift/TASK.md`, the file the worker prompt says to read
   first. Retry notes were cut to 600 characters while reviewer verdicts run 2–3k
   (T-0001's reviewer: "the note is cut off at the source too"). This is most of
   the run's **126 permission denials**. Run 5, with both fixes in place, logged 21.
4. **Gate 2's `|| true` check cannot tell code from a test about code.** T-0040 parked
   on "diff appends '|| true' to a command". The line it matched was
   `assert "|| true" not in VERIFY_SH`, a test proving that verify.sh does *not*
   swallow failures. `orchestrator/gates.py:27` matches any added line containing
   `|| true`, string literals included. It cost a re-issue (T-0041). Still open.
5. **A line-matching bug escaped every gate and was found in production.** The first
   commute saved on the deployed app was "s5". HAFAS calls the line "S5", and the
   engine's exact set lookup meant that commute could never alert. `2f43bbf` compares
   without case or spaces, as `alternatives.py` already did. Every test spelled the
   line the way HAFAS does, because the tests and the fixtures were written by the same
   author. Item 2 has the same cause.
6. **Eight tasks were parked on a reviewer `revise` after both attempts.** T-0001,
   T-0007, T-0009, T-0013, T-0029, T-0032, T-0034 and T-0039 each needed a re-issue.
   The reviewers were right each time: a security fix, an empty
   `PENDEL_CHECK_LEAD_MIN` crashing the scheduler, an IP sentence in the
   Datenschutzerklärung the code did not back. Only T-0001 predates item 3's fix to the
   notes. The other seven had the whole verdict and still did not clear every point in
   two attempts.

## What it cost

| Role | Runs | Cost |
|---|---|---|
| worker | 78 | $47.33 |
| planner | 29 | $9.09 |
| reviewer | 62 | $11.36 |
| auditor | 2 | $0.66 |
| merge | 32 | — |
| **total** | **203** | **$68.44** |

32 merges from 78 worker runs. The 18 parks account for the gap: 8 for the
live-recording chain (item 2), 8 for reviewer revises (item 6), one superseded
duplicate (T-0011) and one gate false positive (item 4). Four runs were rate-limited
(three workers and a planner); none timed out.
