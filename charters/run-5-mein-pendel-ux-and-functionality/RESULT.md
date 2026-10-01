# Run 5 — Mein Pendel: UX and functionality

Armed 2026-09-30T13:09:47+0200, finished 2026-10-01T08:05:38+0200 (charter complete: 3 planner runs added nothing).
Charter: [CHARTER.md](CHARTER.md) · roadmap: [ROADMAP.md](ROADMAP.md) · planner reasoning: [decisions/](decisions/) · digests: [digests/](digests/) · cost ledger: [usage.jsonl](usage.jsonl).

## Outcome

Goals: G1, G2, G3, G4, G5.

- merged: **37** (G1 7, G2 9, G3 9, G4 6, G5 6)
- parked: 5
- backlog left: 0
- agent runs: 169
- estimated spend: **$66.51**

## Where the work is

Each project's `agent/integration` is tagged `nightshift/run-5` in its bare repo:

```bash
git -C ~/coding/mein-pendel fetch ~/nightshift/data/repos/mein-pendel.git nightshift/run-5:tp/nightshift-run5   # c453b55
```

## Merged and deployed

`nightshift/run-5` (`c453b55`) branched from `main`'s tip `2f43bbf`, so for the first
time a run's work landed by **fast-forward with no decision at the merge**. Runs 1–3
each had to resolve something by hand. Before merging, `uv run pytest -q` passed 490
tests on the tag. Nothing under `deploy/`, the Dockerfile, CI or `pyproject.toml`
changed, so the homelab stack needed no edit.

CI run `36823419649` (2026-10-01 06:10 UTC, green in 1m) published the image. The
three containers in `homelab/compose/pendel` were pulled and recreated at 06:12 UTC.
This was the first deploy to run migrations against live data:
`0002_commute_stop_names` and `0003_commute_paused` both add columns with defaults and
applied on start, and the one saved commute survived. The database was snapshotted
first to `/opt/dockerdata/pendel/pre-run5-backup-20261001.db`. Verified after:
`pendel-web` healthy, `/`, `/healthz` and `/static/manifest.json` return 200 from inside
the container, the public `/healthz` returns 200, and the scheduler is fetching real
departures.

The deploy also shipped `2f43bbf` (run 4's line-matching fix), which had been on `main`
but not on the host for 20 hours. Deploying is a manual `docker compose pull`, and
nothing notices when it is skipped.

## What to fix next

_Written by hand after reviewing the branch._

1. **Run 4's item 1 still stands: the Impressum is a placeholder on a public site.**
   This run did not touch it, and was not asked to.
2. **Notification links are relative.** G5 asked that a notification "links to the
   today page". `tracker.py` ends every message with the bare path `/today`, and the
   comment above `_TODAY_PATH` admits that there is no public base URL to prefix it
   with. In Telegram or ntfy that is not a link. ADR 20260930-171420 assumed a
   `PENDEL_PUBLIC_URL` and noted "a human must add PENDEL_PUBLIC_URL to the deploy
   env after the run". No such variable exists in the code, so there is nothing to
   set. The worker left the variable as a follow-up. This is a small code change (read
   `PENDEL_PUBLIC_URL`, document it in `.pendel.env.example`) plus one line in the
   homelab env.
3. **The weekly backup killed a worker and the loop charged it as an attempt.** The
   autorestic `docker-data` hook stops every container at Thursday 03:00 UTC (05:00
   Berlin). At 05:00:07 it SIGTERM'd T-0039's second attempt 13 seconds in (exit 143,
   0 turns), and the loop parked T-0039 on "worker reported status=None". Two planner
   calls in the same second failed the same way, and the orchestrator came back at
   05:00:51. The planner re-issued the work as T-0053 and it merged, so the cost here
   was one re-issue. But a kill in the middle of a merge could cost more, and it will
   happen every Thursday a run is in flight. The backup system is frozen, so fix it on
   this side: treat exit 143 with 0 turns as "interrupted, not attempted", or have the
   loop pause itself from 02:55 to 03:30 UTC on Thursdays.
4. **Running out of turns is reported as "status=None".** Four worker runs ended by
   hitting `max_turns`: T-0015 twice (41 of 40), T-0033 once (61 of 60) and T-0048
   once (51 of 50). Together they cost $5.86. Their gate message reads
   `worker reported status=None, not 'done'`, the same message the backup kill in
   item 3 produced. The planner has to guess which of the two happened. It re-issued all
   three and they merged, but the gate should say "turn limit reached" so that it
   does not have to guess.
5. **The planner gave a task allowed_paths that excluded the test it would break.**
   T-0016 (midnight-crossing windows) had to make 08:00–07:30 valid, which
   `test_web_commutes.py::test_post_with_window_end_before_window_start_returns_400...`
   asserts is invalid. That file was outside allowed_paths, so attempt 1 failed scope
   and attempt 2 reported blocked ($2.08). T-0031 re-issued it with the file included.
   When a task changes a rule, the planner should include the tests that pin the old
   rule.
6. **$4.42 of idle work after the charter was done.** ADR 20261001-053418 recorded
   all five goals at their definition of done at 05:34. The planner then queued three
   idle milestones (M7 README, M8 a11y labels, M9 a platform-change fixture) before the
   three idle passes closed the run at 08:05. All three are real improvements, and M9
   recorded live data on its own (see run 4's item 2), but none was in the charter.
   Decide whether "done" should end a run immediately.
7. **Superseded parks are counted as parks.** All five parked tasks (T-0015, T-0016,
   T-0033, T-0039, T-0048) were replaced by a re-issue that merged (T-0049, T-0031,
   T-0050, T-0053, T-0051/T-0052). The run lost no work, yet the outcome line above
   reports "parked: 5". RESULT.md should report parked work separately from parked
   attempts at work.

## What it cost

| Role | Runs | Cost |
|---|---|---|
| worker | 62 | $48.68 |
| planner | 17 | $8.41 |
| reviewer | 51 | $8.56 |
| auditor | 2 | $0.86 |
| merge | 37 | — |
| **total** | **169** | **$66.51** |

37 merges from 62 worker runs, against run 4's 32 from 78, at slightly lower cost.
Planner runs fell from 29 to 17 and permission denials from 126 to 21: both reflect
`6e0f6b0` being in place from the start. 11 runs errored: 4 rate-limited, 4 out of
turns (item 4), and the backup kill plus the two planner calls beside it (item 3).
None timed out.
