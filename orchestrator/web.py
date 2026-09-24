#!/usr/bin/env python3
"""The dashboard: a read-mostly HTTP view of the run, and the way charters arrive.

Runs as a second container off the same image as the orchestrator, with the same
/data bind mount and none of the privileges: no docker socket, no OAuth token, no
certificates. It reads the run's files and writes exactly two things — a queue
entry, and a command file the loop drains. state.json keeps its single writer.

Standard library only, in the spirit of the rest of the stack: the process that
faces the network is not the place to take a dependency.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import socket
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

import plan
import runs

APP = Path(__file__).resolve().parent
STATIC = APP / "static"
DATA = runs.DATA
LOGS = DATA / "logs"
STATE_FILE = DATA / "state" / "state.json"
HEARTBEAT = DATA / "state" / "heartbeat"
ORCH_LOG = LOGS / "orchestrator.log"
STOP_FILE = DATA / "STOP"

TASK_ID_RE = re.compile(r"^T-\d{4,}$")
RUN_NAME_RE = re.compile(r"^run-\d+[A-Za-z0-9._-]*$")
MAX_BODY = 1024 * 1024


def config() -> dict:
    try:
        with (APP / "config.yaml").open(encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except OSError:
        return {}


def web_cfg() -> dict:
    return config().get("web", {}) or {}


def read_state() -> dict:
    return runs.read_json(STATE_FILE, {})


def ts() -> str:
    return runs.ts()


# ------------------------------------------------------------------- readers
def charter_goal_texts() -> list[dict]:
    """The charter's goals as the dashboard shows them: id, text, merges so far."""
    if not plan.CHARTER.exists():
        return []
    text = plan.charter_text()
    goals: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        match = re.match(r"^\s*[-*]\s*(G\d+)\s*:\s*(.*)$", line)
        if match:
            # First mention wins: a charter states each goal under "## Goals" and
            # then cites it again under "## Definition of done per goal", and the
            # goal is what belongs on the dashboard.
            current = match.group(1) if match.group(1) not in goals else None
            if current:
                goals[current] = [match.group(2).strip()]
            continue
        if current and line.startswith(("  ", "\t")) and line.strip():
            goals[current].append(line.strip())
        elif not line.strip():
            current = None
    merges = runs.run_stats()["merges_by_goal"]
    return [{"id": gid, "text": " ".join(parts), "merges": merges.get(gid, 0)}
            for gid, parts in goals.items()]


def task_summaries(folder: Path, limit: int = 400) -> list[dict]:
    """Tasks as rows, tolerating files the strict loader would refuse."""
    out = []
    if not folder.exists():
        return out
    for path in sorted(folder.glob("*.yaml"))[:limit]:
        try:
            task = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        out.append({
            "id": task.get("id", path.stem),
            "title": task.get("title", ""),
            "goal": task.get("charter_goal", ""),
            "milestone": task.get("roadmap_ref", ""),
            "status": task.get("status", folder.name),
            "attempts": task.get("attempts", 0),
            "project": task.get("project", ""),
            "created": task.get("created", ""),
            "merged_sha": task.get("merged_sha", ""),
            "merged_at": task.get("merged_at", ""),
            "park_reason": task.get("park_reason", ""),
        })
    return out


def find_task(task_id: str) -> dict | None:
    for folder in (plan.BACKLOG, plan.DONE, plan.PARKED):
        path = folder / f"{task_id}.yaml"
        if path.exists():
            try:
                task = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError):
                return None
            task["_folder"] = folder.name
            return task
    return None


def tail(path: Path, lines: int) -> list[str]:
    """Last `lines` lines without reading a 200 MB transcript into memory."""
    if not path.exists():
        return []
    chunk, data, size = 64 * 1024, b"", path.stat().st_size
    try:
        with path.open("rb") as fh:
            while size > 0 and data.count(b"\n") <= lines:
                step = min(chunk, size)
                size -= step
                fh.seek(size)
                data = fh.read(step) + data
    except OSError:
        return []
    return data.decode("utf-8", "replace").splitlines()[-lines:]


def transcript_activity(task_id: str, limit: int = 40) -> list[dict]:
    """The newest agent transcript for a task, rendered as what it did.

    A stream-json transcript is one event per line; only a few of them say
    anything a human wants at a glance - what the agent said, which tool it
    reached for, and how the run ended.
    """
    folder = LOGS / task_id
    if not folder.exists():
        return []
    files = sorted(folder.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        return []
    newest = files[-1]
    out: list[dict] = []
    for line in tail(newest, 400):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "assistant":
            for block in (event.get("message", {}) or {}).get("content", []) or []:
                if block.get("type") == "text" and block.get("text", "").strip():
                    out.append({"kind": "say", "text": block["text"].strip()[:600]})
                elif block.get("type") == "tool_use":
                    target = block.get("input", {}) or {}
                    detail = (target.get("command") or target.get("file_path")
                              or target.get("pattern") or target.get("description") or "")
                    out.append({"kind": "tool", "text": f"{block.get('name', 'tool')}"
                                f"{(': ' + str(detail)[:180]) if detail else ''}"})
        elif kind == "result":
            out.append({"kind": "result",
                        "text": f"finished after {event.get('num_turns', '?')} turns, "
                                f"${float(event.get('total_cost_usd') or 0):.2f}"})
    return [{**item, "file": newest.name} for item in out[-limit:]]


def gate_runs(task_id: str) -> list[dict]:
    folder = LOGS / task_id
    if not folder.exists():
        return []
    out = []
    for path in sorted(folder.glob("gates-*.json")):
        entry = runs.read_json(path, None)
        if isinstance(entry, dict):
            out.append(entry)
    return out


def heartbeat_age_min() -> float | None:
    if not HEARTBEAT.exists():
        return None
    return (time.time() - HEARTBEAT.stat().st_mtime) / 60


def disk_free_gb() -> float:
    try:
        return shutil.disk_usage(DATA).free / 1024 ** 3
    except OSError:
        return -1.0


def deadline_info(state: dict, run: dict) -> dict:
    hours = run.get("run_until_hours")
    if hours is None:
        hours = (config().get("loop", {}) or {}).get("run_until_hours", 0)
    armed_at = state.get("armed_at")
    if not hours or not armed_at:
        return {"hours": hours or 0, "ends": None, "hours_left": None}
    try:
        ends = datetime.fromisoformat(armed_at).timestamp() + float(hours) * 3600
    except ValueError:
        return {"hours": hours, "ends": None, "hours_left": None}
    return {"hours": hours, "ends": datetime.fromtimestamp(ends).isoformat(timespec="minutes"),
            "hours_left": round((ends - time.time()) / 3600, 1)}


def latest_digest() -> dict | None:
    folder = DATA / "digests"
    if not folder.exists():
        return None
    files = sorted(folder.glob("*.json"))
    if not files:
        return None
    entry = runs.read_json(files[-1], None)
    if isinstance(entry, dict):
        entry["date"] = files[-1].stem
        return entry
    return None


def recent_merges(limit: int = 15) -> list[dict]:
    merges = [e for e in runs.read_usage() if e.get("role") == "merge"]
    return merges[-limit:][::-1]


def usage_series() -> dict:
    """Merges and spend per day, plus a cumulative cost line for the chart."""
    per_day: dict[str, dict] = {}
    for entry in runs.read_usage():
        day = str(entry.get("ts", ""))[:10]
        if not day:
            continue
        bucket = per_day.setdefault(day, {"day": day, "merges": 0, "cost_usd": 0.0,
                                          "runs": 0})
        bucket["runs"] += 1
        bucket["cost_usd"] += float(entry.get("cost_usd") or 0)
        if entry.get("role") == "merge":
            bucket["merges"] += 1
    days = [dict(v, cost_usd=round(v["cost_usd"], 2)) for _, v in sorted(per_day.items())]
    running = 0.0
    for day in days:
        running += day["cost_usd"]
        day["cumulative_usd"] = round(running, 2)
    return {"days": days}


def overview() -> dict:
    state = read_state()
    run = runs.active_run() or {}
    current_id = state.get("current_task")
    current = None
    if current_id:
        task = find_task(current_id)
        current = {"task": task, "activity": transcript_activity(current_id)}
    stale = heartbeat_age_min()
    return {
        "now": ts(),
        "read_only": bool(web_cfg().get("read_only")),
        "armed": bool(plan.CHARTER.exists() and state.get("charter_sha256")),
        "run": run,
        "deadline": deadline_info(state, run),
        "goals": charter_goal_texts(),
        "state": {k: state.get(k) for k in
                  ("paused", "pause_reason", "current_task", "consecutive_failures",
                   "merges_total", "merges_since_planner", "limit_until",
                   "idle_planner_streak", "finish_requested", "last_planner_run",
                   "last_auditor_run", "armed_at")},
        "stopped": STOP_FILE.exists(),
        "stats": runs.run_stats(),
        "queue": [{k: v for k, v in entry.items() if k not in ("charter_md", "_path")}
                  for entry in runs.queue_list()],
        "current": current,
        "digest": latest_digest(),
        "recent_merges": recent_merges(),
        "history": runs.archived_runs()[:10],
        "health": {"heartbeat_min": None if stale is None else round(stale, 1),
                   "disk_free_gb": round(disk_free_gb(), 1)},
    }


# -------------------------------------------------------------------- handler
class Handler(BaseHTTPRequestHandler):
    server_version = "nightshift-web"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003 - base class API
        if os.environ.get("NS_WEB_ACCESS_LOG"):
            print(f"{ts()} [web] {self.address_string()} {fmt % args}", flush=True)

    # -- plumbing
    def _send(self, code: int, body: bytes, content_type: str,
              extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def json(self, payload, code: int = 200) -> None:
        self._send(code, json.dumps(payload, default=str).encode("utf-8"),
                   "application/json; charset=utf-8")

    def fail(self, code: int, message: str) -> None:
        self.json({"error": message}, code)

    def body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY:
            raise ValueError(f"request body larger than {MAX_BODY // 1024} KB")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"body is not JSON: {exc}") from exc

    def guard_writable(self) -> bool:
        if web_cfg().get("read_only"):
            self.fail(403, "the dashboard is in read-only mode (web.read_only in "
                           "config.yaml)")
            return False
        return True

    # -- routing
    def do_GET(self) -> None:  # noqa: N802 - base class API
        url = urllib.parse.urlparse(self.path)
        path, query = url.path, urllib.parse.parse_qs(url.query)
        try:
            if path.startswith("/api/"):
                return self.api_get(path[5:], query)
            return self.static(path)
        except Exception as exc:  # noqa: BLE001 - one bad request must not end the server
            return self.fail(500, f"{type(exc).__name__}: {exc}")

    do_HEAD = do_GET

    def do_POST(self) -> None:  # noqa: N802 - base class API
        url = urllib.parse.urlparse(self.path)
        try:
            payload = self.body()
        except ValueError as exc:
            return self.fail(400, str(exc))
        try:
            return self.api_post(url.path[5:] if url.path.startswith("/api/") else "",
                                 payload)
        except runs.RunError as exc:
            return self.fail(400, str(exc))
        except Exception as exc:  # noqa: BLE001
            return self.fail(500, f"{type(exc).__name__}: {exc}")

    def do_DELETE(self) -> None:  # noqa: N802 - base class API
        url = urllib.parse.urlparse(self.path)
        parts = [p for p in url.path.split("/") if p]
        try:
            if parts[:2] == ["api", "queue"] and len(parts) == 3:
                if not self.guard_writable():
                    return None
                return self.json({"removed": runs.queue_remove(parts[2])})
        except Exception as exc:  # noqa: BLE001
            return self.fail(500, f"{type(exc).__name__}: {exc}")
        return self.fail(404, "no such endpoint")

    # -- GET endpoints
    def api_get(self, route: str, query: dict) -> None:
        parts = [p for p in route.split("/") if p]
        head = parts[0] if parts else ""

        if head == "overview":
            return self.json(overview())
        if head == "health":
            return self.json({"ok": True, "now": ts()})
        if head == "repos":
            return self.json({"repos": runs.available_repos()})
        if head == "queue":
            return self.json({"queue": runs.queue_list()})
        if head == "charter":
            return self.json({
                "charter": plan.charter_text() if plan.CHARTER.exists() else "",
                "roadmap": (plan.ROADMAP.read_text(encoding="utf-8")
                            if plan.ROADMAP.exists() else ""),
            })
        if head == "usage":
            return self.json(usage_series())
        if head == "tasks" and len(parts) == 1:
            return self.json({
                "backlog": task_summaries(plan.BACKLOG),
                "done": task_summaries(plan.DONE),
                "parked": task_summaries(plan.PARKED),
            })
        if head == "tasks" and len(parts) == 2:
            task_id = parts[1]
            if not TASK_ID_RE.match(task_id):
                return self.fail(400, "not a task id")
            task = find_task(task_id)
            if task is None:
                return self.fail(404, "no such task")
            return self.json({"task": task, "gates": gate_runs(task_id),
                              "activity": transcript_activity(task_id, limit=200)})
        if head == "logs":
            cap = int(web_cfg().get("log_tail_lines", 500))
            want = min(int((query.get("lines") or [200])[0] or 200), cap)
            return self.json({"lines": tail(ORCH_LOG, want)})
        if head == "decisions":
            folder = plan.DECISIONS
            files = sorted(folder.glob("*.md"), reverse=True) if folder.exists() else []
            if len(parts) == 2:
                match = next((f for f in files if f.name == parts[1]), None)
                if match is None:
                    return self.fail(404, "no such decision")
                return self.json({"name": match.name,
                                  "text": match.read_text(encoding="utf-8")})
            return self.json({"decisions": [{"name": f.name,
                                             "title": f.stem.split("-", 2)[-1].replace("-", " "),
                                             "ts": f.stem[:15]} for f in files[:80]]})
        if head == "digests":
            folder = DATA / "digests"
            files = sorted(folder.glob("*.json"), reverse=True) if folder.exists() else []
            return self.json({"digests": [dict(runs.read_json(f, {}), date=f.stem)
                                          for f in files[:30]]})
        if head == "runs" and len(parts) == 1:
            return self.json({"runs": runs.archived_runs()})
        if head == "runs" and len(parts) == 2:
            name = parts[1]
            if not RUN_NAME_RE.match(name):
                return self.fail(400, "not a run name")
            folder = runs.ARCHIVE / name
            if not folder.is_dir():
                return self.fail(404, "no such run")
            texts = {}
            for filename in ("RESULT.md", "CHARTER.md", "ROADMAP.md"):
                path = folder / filename
                if path.exists():
                    texts[filename] = path.read_text(encoding="utf-8")[:200_000]
            return self.json({"name": name, "files": texts})
        return self.fail(404, "no such endpoint")

    # -- POST endpoints
    def api_post(self, route: str, payload: dict) -> None:
        parts = [p for p in route.split("/") if p]
        head = parts[0] if parts else ""

        if head == "queue" and len(parts) == 1:
            if not self.guard_writable():
                return None
            entry = runs.queue_add(
                title=payload.get("title", ""),
                charter_md=payload.get("charter_md", ""),
                roadmap_md=payload.get("roadmap_md", "") or "",
                sources=payload.get("sources") or {},
                run_until_hours=payload.get("run_until_hours"))
            print(f"{ts()} [web] queued charter {entry['id']}: {entry['title']}",
                  flush=True)
            return self.json({"queued": {k: v for k, v in entry.items()
                                         if k != "charter_md"}}, 201)
        if head == "queue" and len(parts) == 3 and parts[2] == "move":
            if not self.guard_writable():
                return None
            delta = int(payload.get("delta", 0))
            return self.json({"moved": runs.queue_move(parts[1], delta)})
        if head == "validate":
            try:
                declared = runs.check_charter(payload.get("charter_md", ""))
            except runs.RunError as exc:
                return self.json({"ok": False, "error": str(exc)})
            return self.json({"ok": True, "goals": declared["goals"],
                              "projects": declared["projects"]})
        if head == "control":
            if not self.guard_writable():
                return None
            cmd = str(payload.get("cmd", ""))
            name = runs.control_push(cmd, by="web")
            print(f"{ts()} [web] control {cmd}", flush=True)
            return self.json({"queued": cmd, "file": name})
        return self.fail(404, "no such endpoint")

    # -- static files
    def static(self, path: str) -> None:
        name = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (STATIC / name).resolve()
        if STATIC.resolve() not in target.parents or not target.is_file():
            return self.fail(404, "not found")
        kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        return self._send(200, target.read_bytes(), kind)


def serve() -> int:
    port = int(os.environ.get("NS_WEB_PORT") or web_cfg().get("port", 8080))
    for folder in (runs.QUEUE, runs.CONTROL, plan.BACKLOG, plan.DONE, plan.PARKED,
                   plan.DECISIONS, LOGS):
        folder.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer.address_family = socket.AF_INET
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.daemon_threads = True
    print(f"{ts()} [web] listening on 0.0.0.0:{port} "
          f"(read_only={bool(web_cfg().get('read_only'))})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
