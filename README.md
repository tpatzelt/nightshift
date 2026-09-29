# NIGHTSHIFT

An autonomous Claude Code runner that sticks to a plan. Everything lives in this
directory plus one Compose project called `nightshift`; nothing on the host OS was
changed (no sudo, no apt, no systemd units, no host iptables).

It runs as a service: charters are queued from a dashboard, the loop arms the next
one whenever it has nothing left to do, archives the finished run under `charters/`,
and carries on. Queue three charters on a Friday and the answer on Monday is three
archived runs.

## Dashboard

`https://nightshift.dev.<domain>` — LAN only, behind basic auth in Caddy (the
credential lives in the homelab repo's `secrets/.caddy.env` as `NIGHTSHIFT_AUTH_*`).
It shows the run in flight — goals, the task board, what the agent is doing right
now, merges and spend per day, the planner's decisions, the daily digest — and it is
where charters are written and queued. The buttons (pause, resume, stop, plan now,
finish run) write a command file that the loop drains within seconds.

The `web` container is the same image as the orchestrator with none of its
privileges: no docker socket, no OAuth token, no certificates. It writes exactly two
things — a queue entry and a command file — so `state.json` keeps a single writer.

## Runs and the queue

| Where | What |
|---|---|
| `data/queue/*.json` | charters waiting their turn, in order |
| `data/queue/failed/` | a charter that could not be armed, with the reason |
| `data/control/*.json` | commands from the dashboard, drained by the loop |
| `data/state/active-run.json` | the run in flight: number, title, goals, projects |
| `data/state/runs.json` | the ledger of finished runs |
| `charters/run-N-<slug>/` | a finished run: charter, roadmap, tasks, decisions, digests, `usage.jsonl`, generated `RESULT.md` |

A run ends when its deadline passes, when the planner has added nothing for three
runs in a row (`runs.finish_after_idle_planner_runs`), or when **Finish run** is
pressed. Ending a run archives it, tags each project's `agent/integration` as
`nightshift/run-N` in its bare repo, clears the runtime, and arms whatever is next
in the queue. The bare repos are never deleted: the tag is how a run's work is
fetched back out, and the generated `RESULT.md` prints the exact command.

Charters name their projects in a `## Projects` line, and the dashboard clones a
project from `~/coding` (mounted read-only at `/coding`) into a bare repo the first
time it is needed. Nothing is ever written back to the working copies.

## Operate

```bash
cd ~/nightshift
docker compose ps                  # stack status
docker compose logs -f orchestrator
docker compose logs -f web         # the dashboard's own log
docker compose exec orchestrator python3 /app/nightshift.py selftest
ls data/logs/T-0007                # agent transcripts + gates-*.json per attempt
touch data/STOP                    # kill switch (removes itself from nothing; delete to resume)
docker compose stop                # full stop; fires the healthchecks.io alert
```

From the phone, on the ntfy `-cmd` topic, every message prefixed with `CMD_SECRET`:
`pause`, `resume`, `stop`, `status`, `digest`.

## Egress

Agents sit on the `--internal` `nightshift-jail` network, and the squid proxy in
`proxy/` is their only way out. Since 2026-09-22 that way out is **open to any
public host on ports 80 and 443**. It was opened so run 1 could work against the
live Brave and OpenRouter APIs. `proxy/allowlist.txt` is still mounted into the
proxy but no longer consulted, so adding a domain to it changes nothing. What
still holds:

- squid denies every private, loopback, link-local and CGNAT destination
  (`private_dst` in `squid.conf`), even when a public name resolves into those ranges.
  That keeps agents off the LAN and the other containers.
- inside dind, `DOCKER-USER` drops all jail traffic except to the proxy port.
- `sandbox/` managed settings and the guard hook deny curl, wget, ssh and `git push`.

So a charter cannot rely on a service being unreachable. If agents must not
call something, the charter has to forbid it and the sandbox must not hold
that service's credential. To check egress, run a request from a container on
`nightshift-jail` (the agent image has Python but no curl). A request from the
dind container itself bypasses the proxy and tells you nothing.

## Layout

| Path | What |
|---|---|
| `compose.yaml` | dind (inner daemon) + orchestrator + web |
| `.env` | topic, command secret, ping URL, pinned versions (chmod 600) |
| `secrets/oauth_token` | Claude OAuth token, mounted into the orchestrator only |
| `orchestrator/` | the Python loop, the queue (`runs.py`), the dashboard (`web.py`, `static/`), config, prompts, tests |
| `sandbox/` | agent image, managed settings, guard hook |
| `proxy/` | squid egress proxy (`squid.conf`) and a domain list it no longer enforces — see [Egress](#egress) |
| `dind-init/` | iptables jail script, applied inside dind |
| `data/` | plan, bare repos, worktrees, state, logs, digests, backups — untracked |
| `charters/` | one directory per finished run: charter, tasks, decisions, result |
| `scripts/` | `reset-run.sh`, which clears `data/` between runs |

`data/` is bind-mounted at `/data` in **both** containers at the same path, because
`-v` paths in agent `docker run` calls are resolved by the dind daemon, not the host.

## Runs

One run is one charter. `data/` holds the run in flight and is not tracked; a finished
run is archived under `charters/<run>/` — charter, roadmap, every planned task, the
planner's decision records, the daily digests, and a `RESULT.md` saying what came out
and what to fix next. Archiving is automatic; the "what to fix next" half of
`RESULT.md` is still written by hand, against the numbers the run recorded.

| Run | Charter | Result |
|---|---|---|
| 1 | job-application-agent: offline result-quality harness, better triage, output that explains itself | [RESULT.md](charters/run-1-job-application-agent/RESULT.md) — 42 merged, $138.96 |
| 2 | tpatzelt.github.io: artsy landing page for a machine learning engineer | [RESULT.md](charters/run-2-new-website/RESULT.md) — 8 merged, $5.12, deployed |
| 3 | tpatzelt.github.io: editorial portfolio, in the vein of mathismiener.com | [RESULT.md](charters/run-3-editorial-portfolio-in-the-vein-of-mathismiener-/RESULT.md) — 9 merged, $12.94, deployed |

Between runs there is nothing to do: press **Finish run**, or let the deadline or an
idle planner end it, and the next queued charter is armed. `scripts/reset-run.sh` is
still there for the manual path — it refuses to clear a charter that is not archived,
or a loop that is still mid-task, and keeps the bare repos unless given `--repos`.

Arming a charter by hand still works too: write `data/plan/CHARTER.md` and
`data/plan/ROADMAP.md`, seed the bare repo, and run
`docker compose exec orchestrator python3 /app/nightshift.py arm`. The loop will not
activate a queued charter while one is on disk, and says so in its log.

## Remove completely

```bash
cd ~/nightshift && docker compose down -v && cd ~ && rm -rf ~/nightshift
```

## Deviations from the plan

- **Disk.** Everything lives under `~/nightshift` on `/`, which is shared with the rest
  of the homelab. The guard triggers on absolute free space (alert < 10 GB, pause < 5 GB)
  rather than the plan's "85% full": on a 197 GB volume a percentage says little about
  whether there is room to work.
- **Pins.** The plan suggested `docker:27-dind`; the host runs Docker 29.7.2, so dind is
  pinned to `docker:29.7.2-dind` (the same image `orca-dind` already uses) to keep the
  client and daemon versions matched.
- **dind hostname.** The dind TLS server certificate is issued for `docker`/`localhost`,
  so the service carries the network alias `docker` and `DOCKER_HOST=tcp://docker:2376`.
