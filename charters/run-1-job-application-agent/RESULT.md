# Run 1 — job-application-agent

Armed 2026-09-22 16:59 +0200, frozen 2026-09-24 14:20 +0200 (~45 h wall, 10.7 h of
agent wall time). Charter: [CHARTER.md](CHARTER.md) · roadmap: [ROADMAP.md](ROADMAP.md)
· planner reasoning: [decisions/](decisions/) · daily digests: [digests/](digests/) · per-run token and cost ledger: [usage.jsonl](usage.jsonl).

## Outcome

42 tasks merged into `agent/integration`, 19 parked, backlog empty at freeze.
The work left the sandbox as two branches in `~/coding/job-application-agent`:

| Branch | Base | Contents |
|---|---|---|
| `tp/nightshift-base` | `origin/main` | `b6da8dd`, the hand-written wip snapshot the run was armed on |
| `tp/nightshift-run1` | `tp/nightshift-base` | the 42 merged tasks — 38 files, +4146/-81, 112 commits |

Merges by goal: G1 9, G2 9, G3 24 (four of the G3 tasks are README-only).

Verified from a clean clone of `tp/nightshift-run1`:

- `uv run pytest -q` → 388 passed, 1 skipped (182/1 at arming)
- `uv run python run_mock_test.py` → passes
- `uv run python -m evals.offline_eval` → every metric 1.000

Offline harness, 58-record corpus: posting-shape 0.815 → 1.000, aggregator-drop
0.765 → 1.000, location 1.000 → 1.000, staleness 0.429 → 1.000, dedup 0.571 → 1.000.
The auditor's drift score stayed at 2, and no diff touched `Dockerfile`,
`docker-compose.yml`, `.github/**`, `pyproject.toml` or `uv.lock`.

## What it cost

| Role | Runs | Cost |
|---|---|---|
| worker | 82 | $66.50 |
| planner | 848 | $50.87 |
| reviewer | 55 | $19.88 |
| auditor | 59 | $1.70 |
| merge / probe | 43 | — |
| **total** | **1087** | **$138.96** |

627 of those 1087 runs came back rate-limited, 567 of them planner runs.

## What to fix before arming run 2

1. **The planner's idle floor is not applied to a failed run.** `run_planner` writes
   `state["last_planner_run"]` only on the success path (`nightshift.py:1107`), so a
   rate-limited or unusable planner response leaves the timestamp untouched and
   `planner_idle_ok` (`nightshift.py:1055`) permits another attempt on the very next
   iteration — one per `idle_sleep_sec` for the length of the window. That is where
   567 rate-limited planner runs came from. Stamp the attempt, not the success.
   `idle_retry_min` was added mid-run (2026-09-24 ~07:27) and fixes only the
   *successful*-but-empty case; $49 of clean planner spend predates it.
2. **`update_task` changes to `depends_on` never reached the tree.** The auditor traced
   most of the 19 parked tasks to this and to "planned task never reached the backlog"
   — a task is re-issued under a new id rather than unblocked, which is why 42 merges
   needed 82 worker runs. Check `apply_planner_ops`.
3. **The harness is saturated.** All five metrics read 1.000 on a corpus the agents
   both labelled (T-0027) and re-scoped (T-0026). A run-2 charter aimed at G2 would
   have no headroom to show a gain: it needs a corpus grown from postings the current
   code gets wrong, labelled outside the loop.
4. **Thin work at the tail.** Once the backlog ran dry the planner produced
   exact-text assertion tasks and README edits. A charter needs either more scope or a
   deliberate stop, not idle work.

## Parked tasks

19, listed in [tasks/parked/](tasks/parked/). Most were superseded by a re-issued task
(the `supersedes parked T-xxxx` notes in the merged titles map them). The only one that
left work behind was T-0038, whose two-file landing-page diff was superseded by the
merged T-0039 and T-0042; nothing else in `data/work/` held uncommitted changes.
