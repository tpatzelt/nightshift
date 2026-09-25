# Run 2 — new website

Armed 2026-09-24T21:22:00+0200, finished 2026-09-25T00:58:36+0200 (charter complete: 3 planner runs added nothing).
Charter: [CHARTER.md](CHARTER.md) · roadmap: [ROADMAP.md](ROADMAP.md) · planner reasoning: [decisions/](decisions/) · digests: [digests/](digests/) · cost ledger: [usage.jsonl](usage.jsonl).

## Outcome

Goals: G1.

- merged: **8** (G1 8)
- parked: 0
- backlog left: 0
- agent runs: 38
- estimated spend: **$5.12**

## Where the work is

Each project's `agent/integration` is tagged `nightshift/run-2` in its bare repo:

```bash
git -C ~/coding/tpatzelt.github.io fetch ~/nightshift/data/repos/tpatzelt.github.io.git nightshift/run-2:tp/nightshift-run2   # e2fcbc0
```

## Merged and deployed

`tp/nightshift-run2` (`e2fcbc0`) is on `master` and live at
<https://tpatzelt.github.io/> — Pages build `91179ea`, 2026-09-25 05:03 UTC.

The run was armed on `11b6cdb`, but `origin/master` had moved to `d6be062`
("Update cv.") while the run was in flight, so `master` is the merge `91179ea`
rather than a fast-forward. The two sides were disjoint — run 2 touched
`_layouts/default.html`, `index.html`, `assets/css/style.css`,
`assets/js/{main,background}.js`; the CV commit touched only `assets/cv.pdf` — so
the merge was clean. That is luck, not a gate: it is the same "the bare repo's ref
topology is not the topology the work lands in" hazard run 1 hit, and it is still
unguarded.

Verified before pushing: `bundle exec jekyll build` succeeds on the merged tree, all
seven local asset references return 200, and no secret or personal-data string
appears in the diff. Verified after: `/`, both stylesheets, all three scripts, the
sprite and the new 106 KB CV all returned 200 in production.

One follow-up landed on review, `0b81dd2`: the cat cursor and the
`# machine_learning_engineer` kicker were both cut (-412 lines — `cat-cursor.js`,
`cat-cursor.css`, `walking_cat_sprite.png`, two layout tags, three dead
`window.catCursor` hooks in `main.js`, and the `.name::before` rule). Neither was
run 2's work — the cat predates it (`6b52553 add cats`) and the kicker came with
T-0004 — but both were decorative noise against the new design, and removing the cat
also settled findings 1 and 5 below. Dropping `cat-cursor.css` took `.cat-active`
with it, so the typing caret is visible and blinking again.

## What to fix next

1. ~~**`cat-cursor.js` is the one file with no reduced-motion guard.**~~ **Resolved
   by removal** in `0b81dd2`. T-0006 added `matchMedia('(prefers-reduced-motion:
   reduce)')` to `main.js` and `background.js`, and `style.css` carries seven
   reduced-motion blocks — but `cat-cursor.js` had zero, so its flying rAF loop and
   inline rotate transform kept running for visitors who asked for stillness.
   (`cat-cursor.css` did have a reduced-motion block parking the cat, but it covered
   `left`/`top` only, so the `!important` never reached the spin.) The planner
   recorded the gap in ADR 20260925-005807 and left it unscheduled pending
   acceptance — the right call: on review the whole cat went, so the guard was never
   needed. **The planner was correct to wait.**
2. **Nothing in the run ever built the site.** The charter's `test_cmd` is `""` and
   its constraint reads "`` must stay green" — an empty backtick — so the one
   constraint the charter carried was vacuous and eight merges landed with no
   automated check at all. For a Jekyll site the obvious gate is
   `bundle exec jekyll build` plus a link check over `_site/`; it would have cost
   seconds per merge. **Never arm a charter with an empty `test_cmd`** — make the
   arming step refuse it, or substitute a default.
3. **The definition of done was not a test.** "claude orchestrator accepts it" put a
   human in the loop that the loop could not call, so M1 stayed `planned` and five of
   nine planner passes were no-ops recording "backlog stays empty" until
   `finish_after_idle_planner_runs` ended the run. That is the idle brake working, but
   it burned four planner passes to discover a question only a person could answer. A
   subjective goal needs an explicit "await review" state, not an empty backlog.
4. **Three background layers may be one too many.** Body radial gradients, blurred
   parallax blobs and the animated canvas all stack behind the content; the auditor
   called the clutter risk at drift 1. Still open — though `0b81dd2` removed the cat
   sprite orbiting on top of them, which was the loudest part of the clutter.
5. ~~**`.name::before` injects `# machine_learning_engineer` into the `<h1>`.**~~
   **Resolved by removal** in `0b81dd2`. Generated content counts toward a heading's
   accessible name, so the page's only `h1` announced as "# machine_learning_engineer
   Tim Patzelt". The kicker was cut rather than relocated.
6. **Six sandbox denials went unexplained.** The auditor flagged them and said the
   logs it was given do not say what was denied. Whatever the loop hands the auditor
   should include the denial records.

## What it cost

| Role | Runs | Cost |
|---|---|---|
| worker | 10 | $2.43 |
| planner | 9 | $1.48 |
| reviewer | 10 | $0.96 |
| auditor | 1 | $0.24 |
| merge | 8 | — |
| **total** | **38** | **$5.12** |

8 merges from 10 worker runs, nothing parked, no repeated failures — against run 1's
82 worker runs for 42 merges. The planner's idle floor also held: 9 planner runs with
zero rate-limiting, where run 1 logged 567.
