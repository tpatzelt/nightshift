#!/usr/bin/env python3
"""Charter queue and run lifecycle.

One run is one charter; that has not changed. What changes here is who does the
work of moving from one run to the next. It used to be Tim, over SSH: archive the
plan by hand, run `scripts/reset-run.sh`, seed a bare repo, write CHARTER.md, arm.
That is four manual steps between a finished charter and the next one, which is
why the loop spent most of 2026-09-23 planning against goals it had already met.

Now a charter is a queue entry. The orchestrator activates the next one when it
has nothing left to do, archives the finished run under `charters/` on its way
out, and keeps going. The web UI writes queue entries; nothing else does.

The module owns files, never docker and never the agent loop: everything here is
safe to import from the read-only web process.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import gates
import plan

DATA = Path(os.environ.get("NS_DATA_DIR", "/data"))
QUEUE = DATA / "queue"
FAILED = QUEUE / "failed"
CONTROL = DATA / "control"
STATE_DIR = DATA / "state"
ACTIVE_FILE = STATE_DIR / "active-run.json"
RUNS_FILE = STATE_DIR / "runs.json"
USAGE_LOG = STATE_DIR / "usage.jsonl"
REPOS = DATA / "repos"

# Where finished runs are kept. This is the git-tracked `charters/` directory of
# the nightshift repo, bind-mounted; it is the only writable path outside /data.
ARCHIVE = Path(os.environ.get("NS_ARCHIVE_DIR", "/charters"))
# Where a charter's projects may be cloned from. A queue entry names a repo under
# this root and nothing else: it arrives from a web form, so the path it carries
# is checked against this root before git ever sees it.
SOURCE_ROOT = Path(os.environ.get("NS_SOURCE_ROOT", "/coding"))

INTEGRATION = "agent/integration"
REPO_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
COMMANDS = {"pause", "resume", "stop", "status", "digest", "finish", "plan-now"}
MAX_CHARTER_BYTES = 256 * 1024


class RunError(RuntimeError):
    """Raised when a queue entry cannot be turned into a run."""


def _noop(*_args, **_kwargs) -> None:
    return None


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def ts() -> str:
    return now().strftime("%Y-%m-%dT%H:%M:%S%z")


def slugify(text: str, limit: int = 48) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:limit] or "charter"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


# ------------------------------------------------------------------- charters
def check_charter(text: str) -> dict:
    """Validate a charter the way `arm` will, and say what it declares.

    Everything this rejects would otherwise be rejected hours later by `arm`,
    with the charter already at the head of the queue and no one watching.
    """
    if not isinstance(text, str) or not text.strip():
        raise RunError("the charter is empty")
    if len(text.encode("utf-8")) > MAX_CHARTER_BYTES:
        raise RunError(f"the charter is larger than {MAX_CHARTER_BYTES // 1024} KB")
    goals = plan.goals_in(text)
    if not goals:
        raise RunError("no goals found: the charter needs lines like '- G1: ...'")
    expected = [f"G{i}" for i in range(1, len(goals) + 1)]
    if goals != expected:
        raise RunError(f"goals must be numbered G1..G{len(goals)} in order, found {goals}")
    projects = plan.projects_in(text)
    if not projects:
        raise RunError("no projects found: add a '## Projects' section with lines like "
                       '\'- repo: my-repo   goals: [G1]   test_cmd: "pytest -q"\'')
    for name, entry in projects.items():
        if not REPO_NAME_RE.match(name):
            raise RunError(f"'{name}' is not a usable repository name")
        if not entry.get("test_cmd"):
            raise RunError(f"project '{name}' declares no test_cmd")
        unknown = [g for g in entry.get("goals", []) if g not in goals]
        if unknown:
            raise RunError(f"project '{name}' cites goals {unknown} that the charter "
                           f"does not declare")
    return {"goals": goals, "projects": projects}


# ---------------------------------------------------------------------- queue
def queue_list() -> list[dict]:
    """Queued charters, in the order they will run."""
    entries = []
    for path in sorted(QUEUE.glob("*.json")):
        entry = read_json(path, None)
        if isinstance(entry, dict):
            entry["_path"] = str(path)
            entries.append(entry)
    entries.sort(key=lambda e: (e.get("position", 0), e.get("created", "")))
    return entries


def queue_get(qid: str) -> dict | None:
    for entry in queue_list():
        if entry.get("id") == qid:
            return entry
    return None


def queue_add(*, title: str, charter_md: str, roadmap_md: str = "",
              sources: dict | None = None, run_until_hours: int | None = None) -> dict:
    """Validate and enqueue a charter. Returns the stored entry."""
    declared = check_charter(charter_md)
    title = (title or "").strip() or f"Charter {now():%Y-%m-%d %H:%M}"
    if len(title) > 120:
        raise RunError("the title is longer than 120 characters")
    if run_until_hours is not None:
        try:
            run_until_hours = int(run_until_hours)
        except (TypeError, ValueError) as exc:
            raise RunError("run_until_hours must be a whole number of hours") from exc
        if not 0 <= run_until_hours <= 24 * 30:
            raise RunError("run_until_hours must be between 0 (no deadline) and 720")

    resolved: dict[str, dict] = {}
    for name in declared["projects"]:
        given = (sources or {}).get(name) or {}
        source = str(given.get("source") or (SOURCE_ROOT / name)).strip()
        ref = str(given.get("ref") or "HEAD").strip() or "HEAD"
        if not re.fullmatch(r"[A-Za-z0-9._/\-]{1,120}", ref):
            raise RunError(f"'{ref}' is not a usable git ref for project '{name}'")
        # Checked here and again at activation: the entry sits on disk in between.
        check_source(name, source, must_exist=not repo_bare(name).exists())
        resolved[name] = {"source": source, "ref": ref,
                          "fresh_clone": bool(given.get("fresh_clone"))}

    stamp = now().strftime("%Y%m%d-%H%M%S")
    entry = {
        "id": f"{stamp}-{slugify(title, 32)}",
        "title": title,
        "charter_md": charter_md,
        "roadmap_md": roadmap_md.strip() or default_roadmap(declared["goals"]),
        "projects": resolved,
        "goals": declared["goals"],
        "run_until_hours": run_until_hours,
        "created": ts(),
        "position": len(queue_list()) + 1,
        "status": "queued",
    }
    write_atomic(QUEUE / f"{entry['id']}.json", json.dumps(entry, indent=2) + "\n")
    return entry


def queue_remove(qid: str) -> bool:
    entry = queue_get(qid)
    if not entry:
        return False
    Path(entry["_path"]).unlink(missing_ok=True)
    return True


def queue_move(qid: str, delta: int) -> bool:
    """Move an entry up (-1) or down (+1) in the queue."""
    entries = queue_list()
    index = next((i for i, e in enumerate(entries) if e.get("id") == qid), None)
    if index is None:
        return False
    target = max(0, min(len(entries) - 1, index + delta))
    if target == index:
        return False
    entries.insert(target, entries.pop(index))
    for position, entry in enumerate(entries, start=1):
        path = Path(entry.pop("_path"))
        entry["position"] = position
        write_atomic(path, json.dumps(entry, indent=2) + "\n")
    return True


def default_roadmap(goals: list[str]) -> str:
    """A roadmap the planner can extend. It refuses to run without one."""
    lines = ["# Roadmap", "",
             "One milestone per goal to start with; the planner adds more as it learns "
             "what the code actually needs.", ""]
    lines += [f"M{i} [{goal}] First milestone for {goal} — planned — "
              f"the charter's definition of done for {goal} is met"
              for i, goal in enumerate(goals, start=1)]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------- repos
def repo_bare(name: str) -> Path:
    return REPOS / f"{name}.git"


def check_source(name: str, source: str, *, must_exist: bool = True) -> Path:
    """Resolve a clone source and refuse anything outside SOURCE_ROOT.

    The source arrives from a web form. Everything that follows hands it to git,
    so this is the boundary: a path that does not resolve inside the read-only
    coding mount is not a mistake to report later, it is a refusal now.
    """
    if not REPO_NAME_RE.match(name):
        raise RunError(f"'{name}' is not a usable repository name")
    path = Path(source)
    if not path.is_absolute():
        path = SOURCE_ROOT / path
    resolved = path.resolve()
    root = SOURCE_ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise RunError(f"clone source for '{name}' must live under {SOURCE_ROOT}")
    if must_exist and not (resolved / ".git").exists() and not (resolved / "HEAD").exists():
        raise RunError(f"no git repository at {resolved}")
    return resolved


def available_repos() -> list[dict]:
    """Repositories the UI may offer as clone sources."""
    out = []
    if not SOURCE_ROOT.exists():
        return out
    for path in sorted(SOURCE_ROOT.iterdir()):
        if not path.is_dir() or not (path / ".git").exists():
            continue
        try:
            branches = gates.git(path, "for-each-ref", "--sort=-committerdate",
                                 "--format=%(refname:short)", "refs/heads",
                                 timeout=20).split()
            head = gates.git(path, "rev-parse", "--abbrev-ref", "HEAD", timeout=20).strip()
        except (RuntimeError, subprocess.SubprocessError, OSError):
            continue
        out.append({"name": path.name, "source": str(path), "head": head,
                    "branches": branches[:40], "seeded": repo_bare(path.name).exists()})
    return out


def seed_repo(name: str, source: str, ref: str = "HEAD", *,
              fresh_clone: bool = False, log=_noop) -> str:
    """Make sure /data/repos/<name>.git exists and carries agent/integration.

    Returns a one-line description of what was done. An existing bare repo is
    kept unless `fresh_clone` is set, and even then it is renamed rather than
    deleted: it holds every branch a finished run produced.
    """
    bare = repo_bare(name)
    if bare.exists() and fresh_clone:
        stamp = now().strftime("%Y%m%d-%H%M%S")
        retired = REPOS / f"{name}.git.retired-{stamp}"
        bare.rename(retired)
        log(f"kept the previous {name} repo as {retired.name}")
    if bare.exists():
        _ensure_integration(bare, ref if ref != "HEAD" else "", log=log)
        return f"{name}: reused the existing bare repo"

    resolved = check_source(name, source)
    REPOS.mkdir(parents=True, exist_ok=True)
    log(f"cloning {resolved} -> {bare}")
    try:
        gates.git(REPOS, "clone", "--bare", str(resolved), str(bare), timeout=1800)
    except (RuntimeError, subprocess.SubprocessError, OSError) as exc:
        shutil.rmtree(bare, ignore_errors=True)
        raise RunError(f"could not clone {resolved}: {exc}") from exc
    base = _ensure_integration(bare, "" if ref == "HEAD" else ref, log=log)
    return f"{name}: cloned from {resolved} at {base}"


def _ensure_integration(bare: Path, ref: str, *, log=_noop) -> str:
    """Point HEAD at the base ref and branch agent/integration off it."""
    base = ref or gates.git(bare, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if base in ("HEAD", ""):
        base = "main"
    if gates.git(bare, "rev-parse", "--verify", "--quiet", base,
                 check=False).strip() == "":
        raise RunError(f"{bare.name} has no ref '{base}'")
    if gates.git(bare, "rev-parse", "--verify", "--quiet", INTEGRATION,
                 check=False).strip() == "":
        gates.git(bare, "branch", INTEGRATION, base)
        log(f"{bare.name}: branched {INTEGRATION} off {base}")
    gates.git(bare, "symbolic-ref", "HEAD", f"refs/heads/{base}", check=False)
    return base


# ----------------------------------------------------------------- run ledger
def runs_load() -> dict:
    ledger = read_json(RUNS_FILE, {"history": []})
    ledger.setdefault("history", [])
    return ledger


def runs_save(ledger: dict) -> None:
    write_atomic(RUNS_FILE, json.dumps(ledger, indent=2) + "\n")


def active_run() -> dict | None:
    run = read_json(ACTIVE_FILE, None)
    return run if isinstance(run, dict) else None


def next_run_no() -> int:
    highest = 0
    for entry in runs_load()["history"]:
        highest = max(highest, int(entry.get("run_no", 0)))
    run = active_run()
    if run:
        highest = max(highest, int(run.get("run_no", 0)))
    if ARCHIVE.exists():
        for path in ARCHIVE.glob("run-*"):
            match = re.match(r"run-(\d+)", path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def read_usage(limit: int = 20000) -> list[dict]:
    if not USAGE_LOG.exists():
        return []
    out = []
    for line in USAGE_LOG.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def run_stats() -> dict:
    """What the current run has produced so far. Read-only, cheap enough to poll."""
    usage = read_usage()
    merges = [e for e in usage if e.get("role") == "merge"]
    by_goal: dict[str, int] = {}
    for entry in merges:
        goal = entry.get("charter_goal") or "?"
        by_goal[goal] = by_goal.get(goal, 0) + 1
    counts = {}
    for name, folder in (("backlog", plan.BACKLOG), ("done", plan.DONE),
                         ("parked", plan.PARKED)):
        counts[name] = len(list(folder.glob("*.yaml"))) if folder.exists() else 0
    return {
        "merges": len(merges),
        "merges_by_goal": by_goal,
        "cost_usd": round(sum(e.get("cost_usd", 0) or 0 for e in usage), 2),
        "agent_runs": len(usage),
        "tasks": counts,
        "decisions": len(list(plan.DECISIONS.glob("*.md"))) if plan.DECISIONS.exists() else 0,
    }


# ------------------------------------------------------------------ activation
def activate_next(state: dict, *, log=_noop, notify=_noop) -> dict | None:
    """Turn the head of the queue into the active run. Returns it, or None.

    Mutates `state` the way `arm` does and leaves saving it to the caller, which
    owns state.json.
    """
    if plan.CHARTER.exists() or state.get("charter_sha256"):
        return None
    entries = queue_list()
    if not entries:
        return None
    entry = entries[0]
    path = Path(entry.pop("_path"))
    log(f"activating queued charter {entry['id']}: {entry['title']}")

    try:
        declared = check_charter(entry["charter_md"])
        seeded = [seed_repo(name, src.get("source", ""), src.get("ref", "HEAD"),
                            fresh_clone=src.get("fresh_clone", False), log=log)
                  for name, src in entry.get("projects", {}).items()]
    except (RunError, RuntimeError, subprocess.SubprocessError, OSError) as exc:
        FAILED.mkdir(parents=True, exist_ok=True)
        entry.update(status="failed", error=str(exc), failed_at=ts())
        write_atomic(FAILED / path.name, json.dumps(entry, indent=2) + "\n")
        path.unlink(missing_ok=True)
        log(f"could not activate {entry['id']}: {exc}", level="ERROR")
        notify(f"{entry['title']}\n\n{exc}\n\nThe entry is in data/queue/failed/; "
               f"fix it and queue it again.",
               title="NIGHTSHIFT: charter rejected", priority="high", tags="warning")
        return None

    plan.PLAN.mkdir(parents=True, exist_ok=True)
    for folder in (plan.BACKLOG, plan.PARKED, plan.DONE, plan.DECISIONS):
        folder.mkdir(parents=True, exist_ok=True)
    write_atomic(plan.CHARTER, entry["charter_md"].rstrip() + "\n")
    write_atomic(plan.ROADMAP, entry["roadmap_md"].rstrip() + "\n")

    run = {
        "run_no": next_run_no(),
        "id": entry["id"],
        "title": entry["title"],
        "slug": slugify(entry["title"]),
        "goals": declared["goals"],
        "projects": entry.get("projects", {}),
        "test_cmds": {n: p.get("test_cmd", "") for n, p in declared["projects"].items()},
        "run_until_hours": entry.get("run_until_hours"),
        "armed_at": ts(),
        "charter_sha256": plan.charter_hash(),
    }
    write_atomic(ACTIVE_FILE, json.dumps(run, indent=2) + "\n")
    path.unlink(missing_ok=True)

    state.update(charter_sha256=run["charter_sha256"], armed_at=run["armed_at"],
                 paused=False, pause_reason="", consecutive_failures=0,
                 merges_total=0, merges_since_planner=0, idle_planner_streak=0,
                 finish_requested=False, last_planner_run=None, planner_due=True,
                 current_task=None,
                 # Not None: a fresh run has nothing to audit, and an unset clock
                 # makes the daily digest fire the minute the charter arms.
                 last_auditor_run=ts())
    log(f"run {run['run_no']} armed: goals={run['goals']} "
        f"projects={list(run['projects'])}")
    notify(f"Run {run['run_no']}: {run['title']}\n\n"
           + "\n".join(seeded)
           + f"\n\nGoals: {', '.join(run['goals'])}",
           title="NIGHTSHIFT: charter armed", tags="rocket")
    return run


# ------------------------------------------------------------------- archival
def finish_active(state: dict, *, reason: str, log=_noop, notify=_noop) -> Path | None:
    """Archive the active run under charters/ and clear the runtime for the next.

    Nothing is deleted before the copy is on disk and verified, and the bare
    repos are never touched: they hold the branches the run produced.
    """
    run = active_run() or {}
    run_no = run.get("run_no") or next_run_no()
    slug = run.get("slug") or "charter"
    target = ARCHIVE / f"run-{run_no}-{slug}"
    if not plan.CHARTER.exists():
        log("nothing to archive: no charter in flight", level="WARN")
        return None

    stats = run_stats()
    tips = _tag_run(run_no, run.get("projects", {}), log=log)
    try:
        suffix = 2
        while target.exists():
            target = ARCHIVE / f"run-{run_no}-{slug}-{suffix}"
            suffix += 1
        target.mkdir(parents=True)
        shutil.copy2(plan.CHARTER, target / "CHARTER.md")
        if plan.ROADMAP.exists():
            shutil.copy2(plan.ROADMAP, target / "ROADMAP.md")
        for name, folder in (("done", plan.DONE), ("parked", plan.PARKED),
                             ("backlog", plan.BACKLOG)):
            if folder.exists() and any(folder.iterdir()):
                shutil.copytree(folder, target / "tasks" / name)
        for name, folder in (("decisions", plan.DECISIONS), ("digests", DATA / "digests")):
            if folder.exists() and any(folder.iterdir()):
                shutil.copytree(folder, target / name)
        if USAGE_LOG.exists():
            shutil.copy2(USAGE_LOG, target / "usage.jsonl")
        (target / "RESULT.md").write_text(
            result_markdown(run, stats, tips, reason), encoding="utf-8")
    except OSError as exc:
        log(f"archiving run {run_no} failed: {exc}", level="ERROR")
        notify(f"Could not archive run {run_no}: {exc}\nThe run is left in place.",
               title="NIGHTSHIFT: archive failed", priority="urgent", tags="warning")
        return None

    if not (target / "CHARTER.md").exists():
        log("archive verification failed; keeping the runtime", level="ERROR")
        return None

    ledger = runs_load()
    ledger["history"].append({
        "run_no": run_no, "title": run.get("title", ""), "slug": slug,
        "armed_at": run.get("armed_at"), "finished_at": ts(), "reason": reason,
        "path": str(target), "goals": run.get("goals", []),
        "merges": stats["merges"], "parked": stats["tasks"]["parked"],
        "cost_usd": stats["cost_usd"], "tips": tips,
    })
    runs_save(ledger)

    _clear_runtime(log=log)
    state.update(charter_sha256=None, armed_at=None, current_task=None,
                 merges_total=0, merges_since_planner=0, consecutive_failures=0,
                 idle_planner_streak=0, finish_requested=False,
                 last_planner_run=None, last_auditor_run=None, paused=False,
                 pause_reason="")
    ACTIVE_FILE.unlink(missing_ok=True)
    log(f"run {run_no} archived to {target} ({reason})")
    notify(f"{run.get('title', 'Run')} is finished ({reason}).\n\n"
           f"{stats['merges']} merged, {stats['tasks']['parked']} parked, "
           f"${stats['cost_usd']:.2f}.\nArchived as {target.name}.",
           title=f"NIGHTSHIFT: run {run_no} finished", priority="high",
           tags="checkered_flag")
    return target


def _tag_run(run_no: int, projects: dict, *, log=_noop) -> dict[str, str]:
    """Tag each project's integration branch so the run's work stays findable."""
    tips: dict[str, str] = {}
    for name in projects:
        bare = repo_bare(name)
        if not bare.exists():
            continue
        try:
            sha = gates.git(bare, "rev-parse", "--short", INTEGRATION,
                            check=False).strip()
            if not sha:
                continue
            gates.git(bare, "tag", "-f", f"nightshift/run-{run_no}", INTEGRATION,
                      check=False)
            tips[name] = sha
        except (RuntimeError, subprocess.SubprocessError, OSError) as exc:
            log(f"could not tag {name}: {exc}", level="WARN")
    return tips


def _clear_runtime(*, log=_noop) -> None:
    """Everything reset-run.sh clears, minus the bare repos."""
    for folder in (plan.BACKLOG, plan.DONE, plan.PARKED, plan.DECISIONS,
                   DATA / "digests", DATA / "work"):
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True, exist_ok=True)
    # Deliberately not DATA/"STOP": the kill switch is Tim's, and a run that ends
    # while it is set must not quietly rearm the stack by clearing it.
    for path in (plan.CHARTER, plan.ROADMAP, USAGE_LOG):
        Path(path).unlink(missing_ok=True)
    logs = DATA / "logs"
    if logs.exists():
        for child in logs.iterdir():
            # Per-task transcripts only. logs/proxy is squid's bind mount, and a
            # squid whose log directory vanishes under it never starts again.
            if child.is_dir() and re.match(r"^(T-\d+|planner|auditor)$", child.name):
                shutil.rmtree(child, ignore_errors=True)
    log("runtime cleared for the next charter")


def result_markdown(run: dict, stats: dict, tips: dict, reason: str) -> str:
    """The generated half of a RESULT.md: what happened, in numbers.

    Run 1's RESULT.md was written by hand and says what the numbers meant. This
    is deliberately only the record — armed and finished, what merged, what it
    cost, and where the code is — so that a run archived while nobody is watching
    still leaves something exact behind to write the rest against.
    """
    run_no = run.get("run_no", "?")
    goals = ", ".join(run.get("goals", [])) or "—"
    by_goal = stats["merges_by_goal"]
    lines = [
        f"# Run {run_no} — {run.get('title', 'charter')}",
        "",
        f"Armed {run.get('armed_at', '?')}, finished {ts()} ({reason}).",
        f"Charter: [CHARTER.md](CHARTER.md) · roadmap: [ROADMAP.md](ROADMAP.md) · "
        f"planner reasoning: [decisions/](decisions/) · digests: [digests/](digests/) · "
        f"cost ledger: [usage.jsonl](usage.jsonl).",
        "",
        "## Outcome",
        "",
        f"Goals: {goals}.",
        "",
        f"- merged: **{stats['merges']}**"
        + (f" ({', '.join(f'{g} {n}' for g, n in sorted(by_goal.items()))})" if by_goal else ""),
        f"- parked: {stats['tasks']['parked']}",
        f"- backlog left: {stats['tasks']['backlog']}",
        f"- agent runs: {stats['agent_runs']}",
        f"- estimated spend: **${stats['cost_usd']:.2f}**",
        "",
    ]
    if tips:
        lines += ["## Where the work is", "",
                  "Each project's `agent/integration` is tagged `nightshift/run-"
                  f"{run_no}` in its bare repo:", "", "```bash"]
        for name, sha in tips.items():
            lines.append(f"git -C ~/coding/{name} fetch ~/nightshift/data/repos/{name}.git "
                         f"nightshift/run-{run_no}:tp/nightshift-run{run_no}   # {sha}")
        lines += ["```", ""]
    lines += ["## What to fix next", "",
              "_Written by hand after reviewing the branch._", ""]
    return "\n".join(lines)


def archived_runs() -> list[dict]:
    """Finished runs, newest first, read from the ledger and from charters/."""
    seen: dict[str, dict] = {}
    for entry in runs_load()["history"]:
        seen[Path(entry.get("path", "")).name] = {**entry, "source": "ledger"}
    if ARCHIVE.exists():
        for path in sorted(ARCHIVE.glob("run-*")):
            if not path.is_dir():
                continue
            match = re.match(r"run-(\d+)-(.*)", path.name)
            entry = seen.setdefault(path.name, {
                "run_no": int(match.group(1)) if match else 0,
                "title": (match.group(2).replace("-", " ") if match else path.name),
                "path": str(path), "source": "disk",
            })
            entry["has_result"] = (path / "RESULT.md").exists()
            entry["name"] = path.name
    out = list(seen.values())
    for entry in out:
        entry.setdefault("name", Path(entry.get("path", "")).name)
    out.sort(key=lambda e: int(e.get("run_no", 0)), reverse=True)
    return out


# -------------------------------------------------------------------- control
def control_push(cmd: str, by: str = "web") -> str:
    """Queue a command for the loop. The web process never touches state.json."""
    if cmd not in COMMANDS:
        raise RunError(f"unknown command '{cmd}'")
    CONTROL.mkdir(parents=True, exist_ok=True)
    name = f"{now().strftime('%Y%m%d-%H%M%S-%f')}-{cmd}.json"
    write_atomic(CONTROL / name, json.dumps({"cmd": cmd, "by": by, "at": ts()}) + "\n")
    return name


def control_pop() -> list[dict]:
    """Drain the control directory, oldest first. Each command is read once."""
    if not CONTROL.exists():
        return []
    out = []
    for path in sorted(CONTROL.glob("*.json")):
        entry = read_json(path, None)
        path.unlink(missing_ok=True)
        if isinstance(entry, dict) and entry.get("cmd") in COMMANDS:
            out.append(entry)
    return out
