# NIGHTSHIFT

An autonomous Claude Code runner that sticks to a plan. Everything lives in this
directory plus one Compose project called `nightshift`; nothing on the host OS was
changed (no sudo, no apt, no systemd units, no host iptables).

## Operate

```bash
cd ~/nightshift
docker compose ps                  # stack status
docker compose logs -f orchestrator
docker compose exec orchestrator python3 /app/nightshift.py selftest
ls data/logs/T-0007                # agent transcripts + gates-*.json per attempt
touch data/STOP                    # kill switch (removes itself from nothing; delete to resume)
docker compose stop                # full stop; fires the healthchecks.io alert
```

From the phone, on the ntfy `-cmd` topic, every message prefixed with `CMD_SECRET`:
`pause`, `resume`, `stop`, `status`, `digest`.

## Layout

| Path | What |
|---|---|
| `compose.yaml` | dind (inner daemon) + orchestrator |
| `.env` | topic, command secret, ping URL, pinned versions (chmod 600) |
| `secrets/oauth_token` | Claude OAuth token, mounted into the orchestrator only |
| `orchestrator/` | the Python loop, config, prompts, tests |
| `sandbox/` | agent image, managed settings, guard hook |
| `proxy/` | squid egress allowlist |
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
and what to fix next.

| Run | Charter | Result |
|---|---|---|
| 1 | job-application-agent: offline result-quality harness, better triage, output that explains itself | [RESULT.md](charters/run-1-job-application-agent/RESULT.md) — 42 merged, $138.96 |

Between runs:

```bash
touch data/STOP                              # let the task in flight finish
cp -r data/plan/... charters/<run>/          # archive (see run 1 for the layout)
scripts/reset-run.sh --dry-run               # then without the flag
```

`reset-run.sh` refuses to clear a charter that is not archived, or a loop that is still
mid-task, and keeps the bare repos unless given `--repos`. It prints the arming steps
when it is done.

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
