"""Plan hierarchy: charter → roadmap → backlog, and the schemas around them.

The rule that makes the system safe to leave alone is that agents never write
state. The planner and reviewer return JSON; everything in this module exists to
validate that JSON and decide what the orchestrator is willing to apply.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path

import yaml

# /data everywhere in production; overridable so the tests can run a whole plan
# directory out of a temporary folder without a container.
PLAN = Path(os.environ.get("NS_DATA_DIR", "/data")) / "plan"
CHARTER = PLAN / "CHARTER.md"
ROADMAP = PLAN / "ROADMAP.md"
BACKLOG = PLAN / "backlog"
PARKED = PLAN / "parked"
DONE = PLAN / "done"
DECISIONS = PLAN / "decisions"

STATUSES = {"ready", "in_progress", "parked", "done"}
RISKS = {"low", "medium", "high"}
VERDICTS = {"approve", "revise", "reject"}

# Ceilings the planner may not raise, whatever it argues.
MAX_DIFF_LINES_CEILING = 800
MAX_NEW_TASKS_PER_RUN = 10

TASK_REQUIRED = {
    "id": str, "project": str, "roadmap_ref": str, "charter_goal": str,
    "title": str, "why": str, "acceptance": list, "allowed_paths": list,
    "protected_paths": list, "max_diff_lines": int, "timeout_min": int,
    "max_turns": int, "status": str,
}
TASK_DEFAULTS = {
    "depends_on": [], "new_tests_required": True, "attempts": 0,
    "notes": [], "created": "", "max_diff_lines": 400, "timeout_min": 45,
    "max_turns": 60, "status": "ready",
}

TASK_ID_RE = re.compile(r"^T-\d{4,}$")
# A capitalised English word followed by four or more further words. Acceptance
# lines are handed to bash verbatim, and a planner that writes one as a sentence
# ("Each of the five tests asserts the reply with ==") costs two worker attempts
# and a park before anything notices. Two words are left alone so a real command
# whose name happens to be capitalised - Rscript, Xvfb - still validates.
PROSE_RE = re.compile(r"^[A-Z][a-z]+(?:\s+\S+){4,}$")
GOAL_RE = re.compile(r"^G\d+$")
MILESTONE_RE = re.compile(r"^M\d+$")


class PlanError(ValueError):
    """Raised when agent-supplied plan data fails validation."""


def check_shell_command(command: str) -> None:
    """Reject an acceptance line that bash could never run as written.

    `bash -n` catches the malformed ones outright; PROSE_RE catches the sentences
    that happen to parse. Neither can catch a sentence that opens with a real
    command name, so this narrows the failure mode rather than closing it.
    """
    if not isinstance(command, str) or not command.strip():
        raise PlanError("acceptance entries must be non-empty strings")
    text = command.strip()
    try:
        proc = subprocess.run(["bash", "-n"], input=text, text=True,
                              capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return                      # no bash here: fall through to the prose check
    if proc.returncode != 0:
        raise PlanError(f"acceptance line is not valid shell: {text[:90]}")
    if PROSE_RE.match(text):
        raise PlanError(f"acceptance line reads as prose, not a command: {text[:90]}")


# ------------------------------------------------------------------- charter
def charter_text() -> str:
    return CHARTER.read_text(encoding="utf-8")


def charter_hash() -> str:
    return hashlib.sha256(CHARTER.read_bytes()).hexdigest()


def goals_in(text: str) -> list[str]:
    """Goal ids declared in a charter, e.g. ['G1', 'G2']."""
    goals = []
    for line in text.splitlines():
        for match in re.finditer(r"\b(G\d+)\b\s*:", line):
            if match.group(1) not in goals:
                goals.append(match.group(1))
    return goals


def charter_goals() -> list[str]:
    return goals_in(charter_text())


def projects_in(text: str) -> dict[str, dict]:
    """Parse the '- repo: x  goals: [...]  test_cmd: "..."' lines."""
    projects: dict[str, dict] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- repo:"):
            continue
        entry: dict[str, str] = {}
        for key in ("repo", "test_cmd", "lint_cmd"):
            m = re.search(rf'{key}:\s*"([^"]+)"|{key}:\s*(\S+)', line)
            if m:
                entry[key] = (m.group(1) or m.group(2)).strip()
        goals = re.search(r"goals:\s*\[([^\]]*)\]", line)
        entry["goals"] = [g.strip() for g in goals.group(1).split(",") if g.strip()] if goals else []
        if entry.get("repo"):
            projects[entry["repo"]] = entry
    return projects


def charter_projects() -> dict[str, dict]:
    return projects_in(charter_text())


# ---------------------------------------------------------------------- tasks
def validate_task(task: dict, *, goals: list[str] | None = None,
                  acceptance_must_run: bool = False) -> dict:
    """Return a normalised task or raise PlanError. Used for both disk and agent input.

    `acceptance_must_run` is a gate on new planner output only. Tasks already on
    disk keep whatever they were written with: parked and done files are history,
    they are never executed again, and a loader that refused to read them would
    take the planner, the auditor and the status command down with it.
    """
    if not isinstance(task, dict):
        raise PlanError("task must be a mapping")
    out = {**TASK_DEFAULTS, **task}

    # Agent-supplied data is normalised here, at the boundary, rather than being
    # trusted at each use site: a planner that writes notes as a prose string
    # instead of a list must not be able to crash the loop that appends to it.
    for field in ("notes", "depends_on", "acceptance", "allowed_paths",
                  "protected_paths"):
        value = out.get(field)
        if value is None:
            out[field] = []
        elif isinstance(value, str):
            out[field] = [value]
        elif isinstance(value, (tuple, set)):
            out[field] = list(value)
    out["notes"] = [str(n) for n in out["notes"]]

    for field, kind in TASK_REQUIRED.items():
        if field not in out or out[field] in (None, ""):
            raise PlanError(f"task is missing required field '{field}'")
        if not isinstance(out[field], kind):
            raise PlanError(f"task field '{field}' must be {kind.__name__}")

    if not TASK_ID_RE.match(out["id"]):
        raise PlanError(f"task id '{out['id']}' must look like T-0001")
    if not GOAL_RE.match(out["charter_goal"]):
        raise PlanError(f"charter_goal '{out['charter_goal']}' must look like G1")
    if goals is not None and out["charter_goal"] not in goals:
        raise PlanError(f"charter_goal '{out['charter_goal']}' is not in the charter {goals}")
    if out["status"] not in STATUSES:
        raise PlanError(f"status '{out['status']}' is not one of {sorted(STATUSES)}")
    if not out["acceptance"]:
        raise PlanError("a task needs at least one acceptance command")
    if acceptance_must_run:
        for command in out["acceptance"]:
            check_shell_command(command)
    if not out["allowed_paths"]:
        raise PlanError("a task needs allowed_paths")
    if any(p.strip() in ("**", "*", "/", "**/*") for p in out["allowed_paths"]):
        raise PlanError("allowed_paths may not be a catch-all")
    if out["max_diff_lines"] > MAX_DIFF_LINES_CEILING:
        raise PlanError(f"max_diff_lines {out['max_diff_lines']} exceeds the "
                        f"ceiling of {MAX_DIFF_LINES_CEILING}")
    if out["max_diff_lines"] < 1 or out["timeout_min"] < 1 or out["max_turns"] < 1:
        raise PlanError("max_diff_lines, timeout_min and max_turns must be positive")
    return out


def task_path(task_id: str, status: str = "ready") -> Path:
    folder = {"parked": PARKED, "done": DONE}.get(status, BACKLOG)
    return folder / f"{task_id}.yaml"


def load_tasks(folder: Path = BACKLOG) -> list[dict]:
    tasks = []
    for path in sorted(folder.glob("*.yaml")):
        try:
            tasks.append(validate_task(yaml.safe_load(path.read_text(encoding="utf-8"))))
        except (PlanError, yaml.YAMLError) as exc:
            raise PlanError(f"{path.name}: {exc}") from exc
    return tasks


def save_task(task: dict, status: str | None = None) -> Path:
    task = dict(task)
    if status:
        task["status"] = status
    task = validate_task(task)
    path = task_path(task["id"], task["status"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(task, sort_keys=False, allow_unicode=True),
                   encoding="utf-8")
    tmp.replace(path)
    # A task lives in exactly one folder.
    for other in (BACKLOG, PARKED, DONE):
        stale = other / f"{task['id']}.yaml"
        if stale != path and stale.exists():
            stale.unlink()
    return path


# -------------------------------------------------------------- planner output
def validate_planner_output(payload: dict, *, goals: list[str],
                            existing: dict[str, dict]) -> list[dict]:
    """Reject anything the planner is not allowed to do; return accepted ops.

    Rejections are per-op and never fatal: a planner that proposes nine sane ops
    and one forbidden one still moves the project forward.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("ops"), list):
        raise PlanError("planner output must be an object with an 'ops' list")

    accepted: list[dict] = []
    rejected: list[str] = []
    added = 0
    # Tasks created earlier in this same batch are legitimate targets for a later
    # reorder or update; validating only against what was already on disk made a
    # planner's own new ordering unappliable.
    known = dict(existing)

    for op in payload["ops"]:
        if not isinstance(op, dict) or "op" not in op:
            rejected.append("op is not an object with an 'op' field")
            continue
        kind = op["op"]
        try:
            if kind == "add_task":
                added += 1
                if added > MAX_NEW_TASKS_PER_RUN:
                    raise PlanError(f"more than {MAX_NEW_TASKS_PER_RUN} new tasks in one run")
                task = validate_task(op.get("task") or {}, goals=goals,
                                     acceptance_must_run=True)
                if task["id"] in existing:
                    raise PlanError(f"task {task['id']} already exists")
                known[task["id"]] = task
                op = {"op": kind, "task": task}

            elif kind == "update_task":
                tid, fields = op.get("id"), op.get("fields")
                if tid not in known:
                    raise PlanError(f"unknown task {tid}")
                if not isinstance(fields, dict) or not fields:
                    raise PlanError("update_task needs a non-empty 'fields' object")
                current = known[tid]
                merged = validate_task({**current, **fields}, goals=goals,
                                       acceptance_must_run="acceptance" in fields)
                # protected_paths may be extended, never weakened.
                if not set(current["protected_paths"]).issubset(set(merged["protected_paths"])):
                    raise PlanError("update_task may not shrink protected_paths")
                if "attempts" in fields and fields["attempts"] < current.get("attempts", 0):
                    raise PlanError("update_task may not reset the attempt counter")
                op = {"op": kind, "id": tid, "fields": fields}

            elif kind == "park_task":
                if op.get("id") not in known:
                    raise PlanError(f"unknown task {op.get('id')}")
                if not op.get("reason"):
                    raise PlanError("park_task needs a reason")

            elif kind == "add_milestone":
                if not MILESTONE_RE.match(str(op.get("id", ""))):
                    raise PlanError(f"milestone id '{op.get('id')}' must look like M4")
                if op.get("charter_goal") not in goals:
                    raise PlanError(f"milestone cites unknown goal '{op.get('charter_goal')}'")
                if not op.get("title") or not op.get("exit_criteria"):
                    raise PlanError("milestone needs a title and exit_criteria")

            elif kind == "reorder":
                ids = op.get("ids")
                if not isinstance(ids, list) or not ids:
                    raise PlanError("reorder needs a non-empty id list")
                unknown = [i for i in ids if i not in known]
                if unknown:
                    raise PlanError(f"reorder references unknown tasks {unknown}")

            else:
                raise PlanError(f"unsupported op '{kind}'")

            accepted.append(op)
        except PlanError as exc:
            rejected.append(f"{kind}: {exc}")

    payload["_rejected"] = rejected
    return accepted


def validate_adr(payload: dict) -> dict:
    adr = payload.get("adr")
    if not isinstance(adr, dict):
        raise PlanError("planner output must include an 'adr' object")
    missing = [k for k in ("title", "context", "decision", "consequences")
               if not adr.get(k)]
    if missing:
        raise PlanError(f"adr is missing {missing}")
    return adr


def write_adr(adr: dict, stamp: str) -> Path:
    DECISIONS.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", adr["title"].lower()).strip("-")[:60]
    path = DECISIONS / f"{stamp}-{slug or 'decision'}.md"
    path.write_text(
        f"# {adr['title']}\n\n_Recorded {stamp} by the NIGHTSHIFT planner._\n\n"
        f"## Context\n{adr['context']}\n\n"
        f"## Decision\n{adr['decision']}\n\n"
        f"## Consequences\n{adr['consequences']}\n", encoding="utf-8")
    return path


# ------------------------------------------------------------- reviewer output
def validate_reviewer_output(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise PlanError("reviewer output must be a JSON object")
    for field in ("aligned", "meets_acceptance_intent", "scope_ok", "tests_meaningful"):
        if not isinstance(payload.get(field), bool):
            raise PlanError(f"reviewer field '{field}' must be a boolean")
    if payload.get("risk") not in RISKS:
        raise PlanError(f"reviewer risk must be one of {sorted(RISKS)}")
    if payload.get("verdict") not in VERDICTS:
        raise PlanError(f"reviewer verdict must be one of {sorted(VERDICTS)}")
    if not str(payload.get("notes", "")).strip():
        raise PlanError("reviewer must give notes")
    return payload


def review_passes(review: dict) -> bool:
    """The merge condition, kept in one place."""
    return (review["verdict"] == "approve" and review["aligned"]
            and review["scope_ok"] and review["meets_acceptance_intent"]
            and review["tests_meaningful"] and review["risk"] != "high")
