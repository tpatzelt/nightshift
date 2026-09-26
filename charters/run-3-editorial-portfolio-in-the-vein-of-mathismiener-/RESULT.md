# Run 3 — Editorial portfolio, in the vein of mathismiener.com

Armed 2026-09-25T10:39:37+0200, finished 2026-09-25T22:47:48+0200 (charter complete: 3 planner runs added nothing).
Charter: [CHARTER.md](CHARTER.md) · roadmap: [ROADMAP.md](ROADMAP.md) · planner reasoning: [decisions/](decisions/) · digests: [digests/](digests/) · cost ledger: [usage.jsonl](usage.jsonl).

## Outcome

Goals: G1, G2, G3.

- merged: **9** (G1 4, G2 3, G3 2)
- parked: 3
- backlog left: 0
- agent runs: 56
- estimated spend: **$12.94**

## Where the work is

Each project's `agent/integration` is tagged `nightshift/run-3` in its bare repo:

```bash
git -C ~/coding/tpatzelt.github.io fetch ~/nightshift/data/repos/tpatzelt.github.io.git nightshift/run-3:tp/nightshift-run3   # b49ae0f
```

## Merged and deployed

`tp/nightshift-run3` (`b49ae0f`) is on `master` as merge `c88fd50` and live at
<https://tpatzelt.github.io/> — Pages build `36220510613`, 2026-09-26 05:20 UTC,
success in 44s.

The run branched from run 2's tip `e2fcbc0` and never saw the five commits `master`
gained while it was in flight, so four files needed a decision at the merge rather
than a fast-forward. `style.css` kept our side: run 3 re-added the
`# machine_learning_engineer` kicker that `0b81dd2` had deliberately removed.
`_layouts/default.html` took run 3's, which carries no script tags, because both JS
files are gone. `main.js` accepted run 3's deletion. `scripts/check-site.sh` took run
3's 15 checks over our 4 — checks 9 and 10 pin the canvas background and the cat
cursor as removed, so `0b81dd2`'s intent is now enforced rather than merely done. The
one thing run 3's script lost against ours is the CSS brace-balance check.

This is the third run in a row to hit the same hazard: **the bare repo's ref topology
is not the topology the work lands in.** Run 1 hit it, run 2 got a disjoint diff and
called it luck, and run 3 needed four hand-resolved conflicts and came within one
file of silently reverting a deliberate removal. It is still unguarded.

Verified before pushing: `check-site.sh` passes all 15 checks and jekyll 4.4.1 builds
the merged tree clean. Verified after: `/` returns 200 in production.

## What to fix next

_Written by hand after reviewing the branch._

1. **The live site is serving placeholder copy.** This is the one item that needs
   Tim, not the loop. <https://tpatzelt.github.io/> currently renders
   "[Placeholder — about statement to be written by Tim: focus areas, current role,
   what he builds.]", "[Placeholder project 1]" and "[Placeholder project 2]". The
   charter was explicit that inventing biography was a non-goal and the run obeyed it
   exactly — nothing about Tim is fabricated, and every gap is bracketed — but
   "correctly marked as missing" and "fit to be the public site" are different bars,
   and the merge cleared the first one onto production. Either supply the About
   statement and real project entries in `_data/projects.yml`, or **make a bracketed
   placeholder a deploy-blocking check**: `check-site.sh` already has 15 checks and
   grepping `_site/` for `[Placeholder` is a sixteenth.
2. ~~**Gate 6 could not see this repo's test suite.**~~ **Fixed in `2921bd2`.** The
   site has no `tests/` directory — its whole suite is `scripts/check-site.sh`, which
   `TEST_PATH_RE` matched none of, so `test_files_touched` came back empty however
   well a task was done. T-0010 and T-0019 each burned both attempts on
   "new_tests_required is set but no test file was added or changed" while their
   diffs *did* add a check. Three parks in a row tripped `max_consecutive_failures`
   and **paused the run for 9.8 hours** — the ledger goes quiet after the T-0020
   worker at 11:28 and resumes with a planner at 21:15. The planner diagnosed this
   correctly and worked around it (ADR 20260925-110727 re-issued T-0010 as T-0018
   with `new_tests_required: false` and negative acceptance commands proving the check
   works), then talked itself back into the wrong assumption in ADR 20260925-112507
   and had to un-assume it in ADR 20260925-211503. Three ADRs and a 9.8-hour stall
   for one regex.
3. **A truncated reviewer verdict cost two full tasks.** T-0014 passed every gate and
   was parked on a `revise` whose recorded reason stops mid-sentence at "...the mktemp
   gate shows it fails when `_data/projects.yml` is removed, " — one clause short of
   the defect. T-0019's own `why` says so outright: "parked on a reviewer 'revise'
   whose reason was cut off, so this re-issue repeats that work in full." The auditor
   independently flagged that "the review excerpt shown finds no defect". So the same
   Selected-work section was specified three times (T-0014, T-0019, T-0020) and the
   planner was guessing at the defect each time. `reason[:600]` kept the head of a
   verdict that opens with praise and names the defect last. **Fix is open in PR #2**
   (`c9bc1f5`): `clip()` keeps both ends with a marker between them.
4. **The planner cost three times what run 2's did, for one more merge.** 15 planner
   runs at $4.77 against run 2's 9 at $1.48 — planner is now 37% of the run's spend
   and the single most expensive role after worker. Five of the fifteen passes added
   nothing (the three closing idle passes plus the two that re-litigated the gate-6
   assumption). Some of that is items 2 and 3 charging their rework to the planner,
   but not all of it: the idle floor that held at 9 passes in run 2 did not hold here.
5. **The contact loop reuses the previous link's URL.** Still live on `master`.
   `index.html:48-59` assigns `href` inside a `{% case link.kind %}` with no
   `{% else %}` branch, and Liquid does not reset an assigned variable between loop
   passes — so a `_data/contact.yml` entry with an unrecognised `kind` renders with
   whatever URL the entry before it got. No such entry exists today, which is exactly
   why this will land as a surprise the first time someone adds one. The auditor
   called it at drift 1 and it was not scheduled.
6. **The 400px result is a grep, not a render.** G3's definition of done says "the
   page has no horizontal scrollbar at 400px". Check 15 greps `style.css` for `100vw`
   and wide fixed widths, which is a proxy — nothing in the run ever rendered the page
   at 400px. The auditor said so and labelled it an assumption. This is run 2's finding
   2 in a milder form: the gate tests the cause it thought of, not the property the
   charter asked for.
7. **The auditor reads the integration branch, not the tree that ships.** It filed
   "G1 leftovers: `cat-cursor.js`, `cat-cursor.css` and `walking_cat_sprite.png` are
   still in the repo" — true of `b49ae0f`, and already false of `master`, where
   `0b81dd2` had deleted all three. Meanwhile the genuine regression in that same diff
   — run 3 re-adding the kicker `0b81dd2` removed — was invisible to it and had to be
   caught by hand at the merge. The audit is pointed at the wrong tree in both
   directions, and this is item "merged and deployed" again from the reviewing end.
8. **Eleven permission denials went unexplained.** Spread across seven worker tasks
   (T-0014 alone hit 3, T-0013 and T-0016 2 each). Run 2 logged six and its RESULT
   said whatever the loop hands the auditor should include the denial records. It
   still doesn't, and the count nearly doubled.

## What it cost

| Role | Runs | Cost |
|---|---|---|
| worker | 19 | $6.27 |
| planner | 15 | $4.77 |
| reviewer | 12 | $1.56 |
| auditor | 1 | $0.34 |
| merge | 9 | — |
| **total** | **56** | **$12.94** |

9 merges from 19 worker runs against run 2's 8 from 10 — the extra nine worker runs
are almost entirely items 2 and 3: six of them are T-0010, T-0014 and T-0019 burning
both attempts each on the same two pieces of work, which then landed as T-0018 and
T-0020. No rate limiting, no timeouts, no errored runs.
