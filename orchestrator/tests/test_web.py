"""The dashboard API, driven over real HTTP against a temporary /data.

Run: python3 tests/test_web.py
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(tempfile.mkdtemp(prefix="ns-web-"))
os.environ["NS_DATA_DIR"] = str(ROOT / "data")
os.environ["NS_ARCHIVE_DIR"] = str(ROOT / "charters")
os.environ["NS_SOURCE_ROOT"] = str(ROOT / "coding")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plan  # noqa: E402
import runs  # noqa: E402
import web  # noqa: E402

from http.server import ThreadingHTTPServer  # noqa: E402

failures = []

CHARTER = """# Toy charter

## Goals
- G1: The toy module explains itself.

## Non-goals
- No new dependencies.

## Constraints
- `pytest -q` must stay green.

## Definition of done per goal
- G1: every return value carries a reason.

## Priority order
G1

## Projects
- repo: toy   goals: [G1]   test_cmd: "pytest -q"
"""


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else f'  -> {detail}'}")
    if not ok:
        failures.append(name)


def make_source_repo():
    path = Path(os.environ["NS_SOURCE_ROOT"]) / "toy"
    path.mkdir(parents=True)
    def sh(*args):
        subprocess.run(args, cwd=path, check=True, capture_output=True)
    sh("git", "init", "-q", "-b", "main")
    (path / "toy.py").write_text("x = 1\n")
    sh("git", "add", "-A")
    sh("git", "-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "init")
    return path


def request(method, path, payload=None):
    url = f"http://127.0.0.1:{PORT}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            return resp.status, (json.loads(body) if body.startswith(("{", "[")) else body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body


for folder in (runs.QUEUE, runs.CONTROL, plan.BACKLOG, plan.DONE, plan.PARKED,
               plan.DECISIONS, web.LOGS):
    folder.mkdir(parents=True, exist_ok=True)
source = make_source_repo()

server = ThreadingHTTPServer(("127.0.0.1", 0), web.Handler)
server.daemon_threads = True
PORT = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

# ------------------------------------------------------------------- serving
status, body = request("GET", "/")
check("the page is served", status == 200 and "NIGHTSHIFT" in body, status)
status, _ = request("GET", "/app.js")
check("the script is served", status == 200, status)
status, _ = request("GET", "/../config.yaml")
check("static traversal is refused", status == 404, status)
status, body = request("GET", "/api/health")
check("health answers", status == 200 and body["ok"], body)
status, body = request("GET", "/api/nope")
check("an unknown endpoint 404s", status == 404, status)

# ------------------------------------------------------------------ overview
status, body = request("GET", "/api/overview")
check("overview answers with nothing armed",
      status == 200 and body["armed"] is False and body["queue"] == [], body)
check("overview reports health", "disk_free_gb" in body["health"], body.get("health"))

# --------------------------------------------------------------------- queue
status, body = request("POST", "/api/validate", {"charter_md": CHARTER})
check("a good charter validates", status == 200 and body["ok"] and body["goals"] == ["G1"], body)
status, body = request("POST", "/api/validate", {"charter_md": "# nothing"})
check("a bad charter reports why", status == 200 and not body["ok"] and "no goals" in body["error"],
      body)

status, body = request("POST", "/api/queue", {
    "title": "Toy: explain itself", "charter_md": CHARTER,
    "sources": {"toy": {"source": str(source), "ref": "main"}},
    "run_until_hours": 8})
check("a charter can be queued", status == 201 and body["queued"]["position"] == 1, body)
qid = body["queued"]["id"]
check("the queued entry does not echo its charter back", "charter_md" not in body["queued"])

status, body = request("POST", "/api/queue", {"title": "Bad", "charter_md": "# nope"})
check("an invalid charter is refused with a reason",
      status == 400 and "no goals" in body["error"], body)

status, body = request("POST", "/api/queue", {
    "title": "Escape", "charter_md": CHARTER,
    "sources": {"toy": {"source": "/etc", "ref": "main"}}})
check("a source outside the coding root is refused",
      status == 400 and "must live under" in body["error"], body)

status, body = request("GET", "/api/queue")
check("the queue lists the entry", status == 200 and len(body["queue"]) == 1, body)
status, body = request("GET", "/api/overview")
check("the overview shows the queue", body["queue"][0]["title"] == "Toy: explain itself",
      body["queue"])

status, body = request("DELETE", f"/api/queue/{qid}")
check("a queue entry can be removed", status == 200 and body["removed"], body)
check("the queue is empty again", request("GET", "/api/queue")[1]["queue"] == [])

# ------------------------------------------------------------------- control
status, body = request("POST", "/api/control", {"cmd": "pause"})
check("a control command is queued", status == 200 and body["queued"] == "pause", body)
check("the command reaches the loop's directory", [c["cmd"] for c in runs.control_pop()] == ["pause"])
status, body = request("POST", "/api/control", {"cmd": "sudo reboot"})
check("an unknown command is refused", status == 400 and "unknown command" in body["error"], body)

# --------------------------------------------------------------------- reads
status, body = request("GET", "/api/tasks")
check("tasks answer even with no plan",
      status == 200 and body["backlog"] == [] and body["done"] == [], body)
status, body = request("GET", "/api/tasks/T-9999")
check("an unknown task 404s", status == 404, status)
status, body = request("GET", "/api/tasks/not-a-task")
check("a malformed task id is refused", status == 400, status)
status, body = request("GET", "/api/runs/..%2F..%2Fetc")
check("a run-name traversal is refused", status in (400, 404), status)
status, body = request("GET", "/api/logs?lines=5")
check("logs answer", status == 200 and isinstance(body["lines"], list), body)
status, body = request("GET", "/api/usage")
check("usage answers", status == 200 and body["days"] == [], body)
status, body = request("GET", "/api/repos")
check("repos are offered as clone sources",
      status == 200 and [r["name"] for r in body["repos"]] == ["toy"], body)

# ----------------------------------------------------------------- read-only
web.web_cfg = lambda: {"read_only": True, "port": PORT, "log_tail_lines": 50}
status, body = request("POST", "/api/queue", {"title": "x", "charter_md": CHARTER})
check("read-only mode refuses a queue write", status == 403, (status, body))
status, body = request("POST", "/api/control", {"cmd": "stop"})
check("read-only mode refuses a control command", status == 403, (status, body))
status, body = request("GET", "/api/overview")
check("read-only mode still reads", status == 200 and body["read_only"] is True, status)

server.shutdown()
print(f"\n{'ALL WEB TESTS PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
