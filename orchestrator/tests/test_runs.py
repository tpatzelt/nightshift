"""Charter queue, repo seeding, activation and archival — against real git repos.

Run: python3 tests/test_runs.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(tempfile.mkdtemp(prefix="ns-runs-"))
os.environ["NS_DATA_DIR"] = str(ROOT / "data")
os.environ["NS_ARCHIVE_DIR"] = str(ROOT / "charters")
os.environ["NS_SOURCE_ROOT"] = str(ROOT / "coding")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plan  # noqa: E402
import runs  # noqa: E402

failures = []

CHARTER = """# Make the toy repo explain itself

## Goals
- G1: The toy module states why it did what it did.
- G2: The output is covered by tests.

## Non-goals
- No new dependencies.

## Constraints
- `pytest -q` must stay green.

## Definition of done per goal
- G1: every return value carries a reason string.
- G2: pytest -q covers each branch.

## Priority order
G1 > G2

## Projects
- repo: toy   goals: [G1, G2]   test_cmd: "pytest -q"
"""


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else f'  -> {detail}'}")
    if not ok:
        failures.append(name)


def raises(name, fn, needle=""):
    try:
        fn()
    except runs.RunError as exc:
        check(name, needle in str(exc), f"wrong message: {exc}")
    except Exception as exc:  # noqa: BLE001
        check(name, False, f"{type(exc).__name__}: {exc}")
    else:
        check(name, False, "no RunError raised")


def sh(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def make_source_repo(name="toy"):
    path = Path(os.environ["NS_SOURCE_ROOT"]) / name
    path.mkdir(parents=True)
    sh(path, "git", "init", "-q", "-b", "main")
    (path / "toy.py").write_text("def hello():\n    return 'hi'\n")
    sh(path, "git", "add", "-A")
    sh(path, "git", "-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "init")
    sh(path, "git", "branch", "wip")
    return path


# ------------------------------------------------------------------ charters
declared = runs.check_charter(CHARTER)
check("charter declares its goals", declared["goals"] == ["G1", "G2"], declared["goals"])
check("charter declares its project", list(declared["projects"]) == ["toy"],
      list(declared["projects"]))
check("charter keeps the test command",
      declared["projects"]["toy"]["test_cmd"] == "pytest -q")

raises("empty charter is refused", lambda: runs.check_charter("   "), "empty")
raises("charter without goals is refused",
       lambda: runs.check_charter("# t\n## Projects\n- repo: toy goals: [] test_cmd: \"x\"\n"),
       "no goals")
raises("charter with goals out of order is refused",
       lambda: runs.check_charter(CHARTER.replace("- G1:", "- G3:")), "numbered")
raises("charter without projects is refused",
       lambda: runs.check_charter("# t\n## Goals\n- G1: a thing\n"), "no projects")
raises("project without a test command is refused",
       lambda: runs.check_charter(CHARTER.replace('   test_cmd: "pytest -q"', "")),
       "test_cmd")
raises("project citing an unknown goal is refused",
       lambda: runs.check_charter(CHARTER.replace("goals: [G1, G2]", "goals: [G1, G9]")),
       "G9")
raises("an oversized charter is refused",
       lambda: runs.check_charter(CHARTER + "x" * (256 * 1024)), "larger than")

# --------------------------------------------------------------------- queue
source = make_source_repo()
entry = runs.queue_add(title="Toy: explain itself", charter_md=CHARTER,
                       sources={"toy": {"source": str(source), "ref": "main"}},
                       run_until_hours=12)
check("queue entry lands on disk", (runs.QUEUE / f"{entry['id']}.json").exists())
check("queue entry keeps its charter", entry["charter_md"] == CHARTER)
check("queue entry gets a default roadmap", "M1 [G1]" in entry["roadmap_md"],
      entry["roadmap_md"][:80])
check("queue entry records the deadline", entry["run_until_hours"] == 12)

second = runs.queue_add(title="Second charter", charter_md=CHARTER,
                        sources={"toy": {"source": str(source)}})
check("queue is ordered", [e["id"] for e in runs.queue_list()] == [entry["id"], second["id"]])
runs.queue_move(second["id"], -1)
check("queue can be reordered",
      [e["id"] for e in runs.queue_list()] == [second["id"], entry["id"]])
runs.queue_remove(second["id"])
check("queue entry can be removed", [e["id"] for e in runs.queue_list()] == [entry["id"]])

raises("a clone source outside the coding root is refused",
       lambda: runs.check_source("toy", "/etc"), "must live under")
raises("a traversal source is refused",
       lambda: runs.check_source("toy", f"{os.environ['NS_SOURCE_ROOT']}/../../etc"),
       "must live under")
raises("a hostile repo name is refused",
       lambda: runs.check_source("../../etc/passwd", str(source)), "usable repository name")
raises("a bad ref is refused",
       lambda: runs.queue_add(title="x", charter_md=CHARTER,
                              sources={"toy": {"source": str(source), "ref": "a;rm -rf /"}}),
       "usable git ref")

# ---------------------------------------------------------------------- seed
message = runs.seed_repo("toy", str(source), "main")
bare = runs.repo_bare("toy")
check("bare repo is created", bare.exists(), message)
branches = subprocess.run(["git", "--git-dir", str(bare), "branch", "--format=%(refname:short)"],
                          capture_output=True, text=True).stdout.split()
check("integration branch exists", runs.INTEGRATION in branches, branches)
check("seeding again reuses the repo", "reused" in runs.seed_repo("toy", str(source), "main"))
runs.seed_repo("toy", str(source), "wip", fresh_clone=True)
check("a fresh clone keeps the old repo",
      any(p.name.startswith("toy.git.retired-") for p in runs.REPOS.iterdir()),
      [p.name for p in runs.REPOS.iterdir()])
head = subprocess.run(["git", "--git-dir", str(bare), "symbolic-ref", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
check("a fresh clone honours the chosen base ref", head == "refs/heads/wip", head)

# ---------------------------------------------------------------- activation
state = {}
run = runs.activate_next(state, log=lambda *a, **k: None, notify=lambda *a, **k: None)
check("the queue head becomes the active run", run is not None and run["run_no"] >= 1, run)
check("the charter is written", plan.CHARTER.exists() and plan.charter_text() == CHARTER)
check("the roadmap is written", plan.ROADMAP.exists())
check("the state is armed", state.get("charter_sha256") == plan.charter_hash())
check("the deadline comes from the charter", run["run_until_hours"] == 12)
check("the queue is empty afterwards", runs.queue_list() == [])
check("activation is a no-op while a run is active",
      runs.activate_next(dict(state)) is None)

bad = runs.queue_add(title="Bad", charter_md=CHARTER,
                     sources={"toy": {"source": str(source)}})
Path(bad["_path"] if "_path" in bad else runs.QUEUE / f"{bad['id']}.json")
broken = json.loads((runs.QUEUE / f"{bad['id']}.json").read_text())
broken["charter_md"] = "# nothing declared here"
(runs.QUEUE / f"{bad['id']}.json").write_text(json.dumps(broken))
plan.CHARTER.unlink()
run2 = runs.activate_next({}, log=lambda *a, **k: None, notify=lambda *a, **k: None)
check("an invalid charter does not become a run", run2 is None)
check("an invalid charter is moved aside", (runs.FAILED / f"{bad['id']}.json").exists())
check("an invalid charter leaves the queue", runs.queue_list() == [])
plan.CHARTER.write_text(CHARTER)

# ----------------------------------------------------------------- archival
plan.save_task({"id": "T-0001", "project": "toy", "roadmap_ref": "M1", "charter_goal": "G1",
                "title": "did a thing", "why": "because", "acceptance": ["true"],
                "allowed_paths": ["toy.py"], "protected_paths": [".github/**"],
                "max_diff_lines": 100, "timeout_min": 5, "max_turns": 10}, "done")
runs.USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
runs.USAGE_LOG.write_text(json.dumps({"ts": runs.ts(), "role": "merge", "task": "T-0001",
                                      "charter_goal": "G1", "cost_usd": 1.25}) + "\n")
stats = runs.run_stats()
check("stats count the merge", stats["merges"] == 1 and stats["cost_usd"] == 1.25, stats)

state_after = dict(state)
target = runs.finish_active(state_after, reason="test", log=lambda *a, **k: None,
                            notify=lambda *a, **k: None)
check("the run is archived", target is not None and (target / "CHARTER.md").exists(), target)
check("the archive keeps the tasks", (target / "tasks" / "done" / "T-0001.yaml").exists())
check("the archive keeps the ledger", (target / "usage.jsonl").exists())
result = (target / "RESULT.md").read_text()
check("RESULT.md records the merge", "merged: **1**" in result, result[:200])
check("RESULT.md records the spend", "$1.25" in result)
check("RESULT.md says where the work is", "nightshift/run-" in result)
tags = subprocess.run(["git", "--git-dir", str(bare), "tag"],
                      capture_output=True, text=True).stdout.split()
check("the run is tagged in the bare repo", any(t.startswith("nightshift/run-") for t in tags), tags)
check("the plan is cleared", not plan.CHARTER.exists() and not list(plan.DONE.glob("*.yaml")))
check("the bare repo survives", bare.exists())
check("the state is disarmed", state_after.get("charter_sha256") is None)
check("the ledger records the run", runs.runs_load()["history"][-1]["merges"] == 1)
check("the finished run is listed", runs.archived_runs()[0]["name"] == target.name)

# ------------------------------------------------------------------ control
runs.control_push("pause", by="test")
runs.control_push("finish", by="test")
popped = [c["cmd"] for c in runs.control_pop()]
check("control commands arrive in order", popped == ["pause", "finish"], popped)
check("control commands are read once", runs.control_pop() == [])
raises("an unknown command is refused", lambda: runs.control_push("rm -rf"), "unknown command")

print(f"\n{'ALL RUN TESTS PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
