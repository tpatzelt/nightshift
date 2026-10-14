"""Retries build on the attempt before them, against a real bare repo.

Run: python3 tests/test_attempts.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(tempfile.mkdtemp(prefix="ns-attempts-"))
os.environ["NS_DATA_DIR"] = str(ROOT / "data")
os.environ["NS_ARCHIVE_DIR"] = str(ROOT / "charters")
os.environ["NS_SOURCE_ROOT"] = str(ROOT / "coding")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nightshift as ns  # noqa: E402
import runs  # noqa: E402

failures = []


def check(name, ok, detail=""):
    print(f"  [{'ok ' if ok else 'BAD'}] {name}" + ("" if ok else f" — {detail}"))
    if not ok:
        failures.append(name)


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def set_run(run_no):
    runs.STATE_DIR.mkdir(parents=True, exist_ok=True)
    runs.ACTIVE_FILE.write_text(json.dumps({"run_no": run_no}))


def task(tid, **over):
    return {"id": tid, "project": "toy", "title": "t", "why": "w", "charter_goal": "G1",
            "roadmap_ref": "M1", "acceptance": ["true"], "allowed_paths": ["src/**"],
            "protected_paths": [], "max_diff_lines": 400, "timeout_min": 45,
            "max_turns": 60, "attempts": 0, "notes": [], **over}


def advance_integration(files: dict, message: str):
    """Land a commit on agent/integration in the bare repo, as a merge would."""
    tmp = Path(tempfile.mkdtemp(prefix="ns-int-"))
    sh(tmp, "git", "clone", "-q", "--branch", ns.INTEGRATION, str(ns.repo_path("toy")), "c")
    c = tmp / "c"
    for name, body in files.items():
        (c / name).parent.mkdir(parents=True, exist_ok=True)
        (c / name).write_text(body)
    sh(c, "git", "add", "-A")
    sh(c, "git", "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qm", message)
    sh(c, "git", "push", "-q", "origin", ns.INTEGRATION)


# a bare repo with an integration branch, as runs.seed_repo leaves it
src = ROOT / "src"
src.mkdir()
sh(src, "git", "init", "-q", "-b", ns.INTEGRATION)
(src / "src").mkdir()
(src / "src" / "app.py").write_text("A = 1\n")
(src / "src" / "shared.py").write_text("S = 1\n")
sh(src, "git", "add", "-A")
sh(src, "git", "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qm", "base")
ns.repo_path("toy").parent.mkdir(parents=True)
sh(ROOT, "git", "clone", "-q", "--bare", str(src), str(ns.repo_path("toy")))
set_run(7)

print("\n--- a first attempt starts clean ---")
work = ns.prepare_worktree(task("T-0005"))
check("no starting-point section on a first attempt",
      "## Starting point" not in (work / ".nightshift" / "TASK.md").read_text())
check("TASK.md states the turn budget",
      "60 turns and 45 minutes" in (work / ".nightshift" / "TASK.md").read_text())

print("\n--- an unmerged attempt is saved, uncommitted work included ---")
(work / "src" / "feature.py").write_text("F = 1\n")
sh(work, "git", "add", "-A")
sh(work, "git", "commit", "-qm", "T-0005: feature")
(work / "src" / "half.py").write_text("H = 1\n")             # never committed
(work / "site-out").mkdir()
(work / "site-out" / "index.html").write_text("<html>\n")      # build output, out of scope
(work / ".nightshift" / "PROGRESS.md").write_text("done: feature\nleft: half.py tests\n")
saved = ns.save_attempt(task("T-0005"), work)
check("save_attempt returns the saved sha", bool(saved), str(saved))
refs = sh(ns.repo_path("toy"), "git", "for-each-ref", "--format=%(refname)")
check("the attempt is kept under a run-scoped ref",
      "refs/nightshift/run-7/attempts/T-0005" in refs, refs)
check("no branch is added to the bare repo",
      "refs/heads/agent/T-0005" not in refs, refs)
files = sh(work, "git", "show", "--name-only", "--format=", "HEAD")
check("uncommitted work went into the saved commit", "src/half.py" in files, files)
check("the handoff note stays out of git", ".nightshift" not in files, files)
check("untracked files outside allowed_paths are left behind", "site-out" not in files, files)
check("the handoff note is read back", "left: half.py tests" in ns.read_handoff(work))

print("\n--- the retry continues from it, rebased onto a moved integration ---")
advance_integration({"src/other.py": "O = 1\n"}, "T-0004: unrelated merge")
work = ns.prepare_worktree(task("T-0005", attempts=1))
task_md = (work / ".nightshift" / "TASK.md").read_text()
check("retry has the earlier files", (work / "src" / "feature.py").exists()
      and (work / "src" / "half.py").exists())
check("retry has the newer integration commit", (work / "src" / "other.py").exists())
check("retry branch is ahead of integration by the carried commits",
      sh(work, "git", "rev-list", "--count", f"{ns.INTEGRATION}..HEAD").strip() == "2")
check("TASK.md tells the worker where it starts",
      "2 commit(s) from your previous attempt" in task_md, task_md[-600:])
check("the retry is on its own task branch",
      sh(work, "git", "branch", "--show-current").strip() == "agent/T-0005")

print("\n--- saved commits that conflict are dropped, not forced ---")
work = ns.prepare_worktree(task("T-0006"))
(work / "src" / "shared.py").write_text("S = 2\n")
sh(work, "git", "commit", "-qam", "T-0006: change shared")
ns.save_attempt(task("T-0006"), work)
advance_integration({"src/shared.py": "S = 3\n"}, "T-0008: conflicting merge")
work = ns.prepare_worktree(task("T-0006", attempts=1))
task_md = (work / ".nightshift" / "TASK.md").read_text()
check("a conflicting attempt starts clean",
      (work / "src" / "shared.py").read_text() == "S = 3\n")
check("no rebase is left in progress", not (work / ".git" / "rebase-merge").exists())
check("TASK.md says why it starts clean", "no longer apply" in task_md, task_md[-400:])

print("\n--- a re-issued task can continue a parked one ---")
work = ns.prepare_worktree(task("T-0009", continue_from="T-0005"))
check("continue_from carries the parked task's files",
      (work / "src" / "feature.py").exists())
check("TASK.md names the task it continues",
      "from T-0005" in (work / ".nightshift" / "TASK.md").read_text())
work = ns.prepare_worktree(task("T-0010", continue_from="T-0099"))
check("continue_from a task with nothing saved starts clean and says so",
      "T-0099 left no saved commits" in (work / ".nightshift" / "TASK.md").read_text())

print("\n--- a new run never inherits an old run's attempt ---")
set_run(8)
work = ns.prepare_worktree(task("T-0005", attempts=1))
check("run 8's T-0005 starts from integration",
      not (work / "src" / "feature.py").exists())
check("nothing to save when the worker committed nothing",
      ns.save_attempt(task("T-0005"), work) is None)

print("\n--- the planner sees how much budget workers used ---")
report = ns.budget_report([
    {"role": "worker", "task": "T-0001", "num_turns": 30, "max_turns": 60,
     "wall_sec": 600, "cost_usd": 0.5},
    {"role": "reviewer", "task": "T-0001", "num_turns": 5},
    {"role": "worker", "task": "T-0002", "num_turns": 61, "max_turns": 60,
     "wall_sec": 1800, "cost_usd": 1.9},
    {"role": "worker", "task": "T-0003", "num_turns": 12, "timed_out": True,
     "wall_sec": 2700, "cost_usd": 1.1},
])
check("budget report counts runs that ran out", report.startswith("2 of the last 3"), report)
check("budget report names the turn limit", "T-0002: 61 turns of 60" in report
      and "hit the turn limit" in report, report)
check("budget report names the timeout", "timed out" in report, report)
check("an empty usage log says so", ns.budget_report([]) == "(no worker runs yet)")

print(f"\n{'ALL ATTEMPT TESTS PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
