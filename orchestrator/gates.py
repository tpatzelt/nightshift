"""Deterministic gates: the checks that do not depend on a model's judgement.

Nothing merges unless every gate passes. The reviewer runs only after these do,
so a model is never asked to compensate for a missing test or an out-of-scope edit.
"""
from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

# A repo without a tests/ directory can still have a suite: the Jekyll site's
# only gate is scripts/check-site.sh, and until it counted here every task with
# new_tests_required parked no matter how well it was done.
TEST_PATH_RE = re.compile(r"(^|/)(tests?|spec)/|(^|/)test_[^/]+\.py$|"
                          r"[^/]+_test\.(py|go|js|ts)$|\.(test|spec)\.(js|ts|tsx)$|"
                          r"(^|/)scripts/check-[^/]+\.sh$")

OR_TRUE = re.compile(r"^\+.*\|\|\s*true\b")

# Ways a diff can make the suite lie about itself.
WEAKENING_RULES = [
    (re.compile(r"^\+.*@pytest\.mark\.(skip|xfail)"), "adds a pytest skip/xfail marker"),
    (re.compile(r"^\+.*\bunittest\.skip\b"), "adds a unittest skip"),
    (re.compile(r"^\+.*\b(it|test|describe)\.(skip|todo)\b"), "skips a JS test"),
    (re.compile(r"^\+.*\bt\.Skip\("), "skips a Go test"),
    (OR_TRUE, "appends '|| true' to a command"),
    (re.compile(r"^\+.*--exitfirst.*--no-header.*-x\b"), "narrows the test run"),
    (re.compile(r"^\+.*\bcontinue-on-error:\s*true"), "makes CI ignore failures"),
    (re.compile(r"^\+.*\bassert\s+True\s*$"), "adds a tautological assertion"),
]

SECRET_RULES = [
    (re.compile(r"sk-ant-(oat|api)[0-9a-zA-Z\-_]{10,}"), "Claude credential"),
    # Live keys are now handed to agents so they can exercise the real code paths;
    # that makes leaking one into a commit the obvious new failure mode.
    (re.compile(r"\bsk-or-v1-[0-9a-f]{32,}"), "OpenRouter key"),
    (re.compile(r"\bBSA[A-Za-z0-9_\-]{20,}"), "Brave Search key"),
    (re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_\-]{30,}"), "Telegram bot token"),
    (re.compile(r"\bghp_[0-9A-Za-z]{30,}"), "GitHub token"),
    (re.compile(r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*"
                r"['\"][^'\"\s]{12,}['\"]"), "hard-coded credential"),
]


# A Python string literal on one line. In a .py file, '|| true' inside one is a
# test asserting its absence (run 4's T-0040 parked on exactly that), not a
# command; in a shell script, YAML or Dockerfile a quoted '|| true' still runs.
PY_STRING_RE = re.compile(r"""(?:[rbfu]{0,2})("([^"\\]|\\.)*"|'([^'\\]|\\.)*')""", re.I)


def weakening_hit(pattern: re.Pattern, line: str, path: str) -> bool:
    if pattern is OR_TRUE and path.endswith(".py"):
        return bool(pattern.search(PY_STRING_RE.sub('""', line)))
    return bool(pattern.search(line))


@dataclass
class GateResult:
    ok: bool = True
    failures: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    def fail(self, reason: str) -> None:
        self.ok = False
        self.failures.append(reason)

    def report(self) -> str:
        if self.ok:
            return "all gates passed"
        return "gate failures:\n" + "\n".join(f"  - {f}" for f in self.failures)

    def failing_output(self, per_command: int = 1000) -> str:
        """What the failing acceptance/lint commands actually printed.

        `report()` names the command that failed, which says what ran but never
        what went wrong: the next attempt reads the notes, sees its own command
        echoed back and has to rediscover the error. This returns the tail of
        every command that exited non-zero, newest gate run first.
        """
        chunks = []
        for label in ("acceptance", "lint"):
            for entry in self.details.get(label, []):
                if entry.get("exit"):
                    tail = (entry.get("tail") or "").strip()[-per_command:]
                    chunks.append(f"$ {entry['cmd']}   (exit {entry['exit']})\n"
                                  f"{tail or '(no output)'}")
        return "\n\n".join(chunks)


def git(work: Path, *args: str, check: bool = True, timeout: int = 120) -> str:
    proc = subprocess.run(["git", "-C", str(work), *args], capture_output=True,
                          text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])}: {proc.stderr.strip()[:300]}")
    return proc.stdout


def path_allowed(path: str, allowed: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) or
               fnmatch.fnmatch(path, pattern.rstrip("/") + "/*")
               for pattern in allowed)


def path_protected(path: str, protected: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) or
               fnmatch.fnmatch(path, pattern.rstrip("/") + "/*")
               for pattern in protected)


def run_gates(task: dict, work: Path, base: str, worker_json: dict | None,
              run_in_sandbox, worker_stopped: str | None = None) -> GateResult:
    """Static gates 1-7 here; 8-9 execute in a jailed container via run_in_sandbox."""
    res = GateResult()
    tid = task["id"]

    # 1. the worker's own verdict
    status = (worker_json or {}).get("status")
    if status != "done":
        # "status=None" read the same whether the worker ran out of turns or was
        # killed, and the planner had to guess which; say so when the loop knows.
        res.fail(f"worker stopped before reporting: {worker_stopped}"
                 if worker_stopped and status is None
                 else f"worker reported status={status!r}, not 'done'")
        res.details["worker_summary"] = (worker_json or {}).get("summary", "")
        return res  # nothing else is worth checking

    # 2. commits exist and the tree is clean
    dirty = git(work, "status", "--porcelain").strip()
    if dirty:
        res.fail(f"working tree is not clean: {dirty.splitlines()[:5]}")
    commits = git(work, "rev-list", "--count", f"{base}..HEAD").strip()
    res.details["commits"] = commits
    if commits == "0":
        res.fail("branch has no commits")
        return res

    # 3. diff size
    diff = git(work, "diff", "--unified=3", f"{base}...HEAD")
    changed_lines = sum(1 for ln in diff.splitlines()
                        if (ln.startswith("+") or ln.startswith("-"))
                        and not ln.startswith(("+++", "---")))
    res.details["diff_lines"] = changed_lines
    if changed_lines > task["max_diff_lines"]:
        res.fail(f"diff is {changed_lines} lines, limit is {task['max_diff_lines']}")

    # 4. scope
    name_status = git(work, "diff", "--name-status", f"{base}...HEAD").strip()
    changes = [ln.split("\t") for ln in name_status.splitlines() if ln.strip()]
    paths = [parts[-1] for parts in changes]
    res.details["files_changed"] = len(paths)
    for path in paths:
        if not path_allowed(path, task["allowed_paths"]):
            res.fail(f"{path} is outside allowed_paths")
        if path_protected(path, task["protected_paths"]):
            res.fail(f"{path} is in protected_paths")

    # 5. the test suite must not be weakened
    for parts in changes:
        code, path = parts[0], parts[-1]
        if TEST_PATH_RE.search(path) and code.startswith(("D", "R")):
            res.fail(f"test file {path} was {'deleted' if code.startswith('D') else 'renamed'}")
    current = ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[4:].removeprefix("b/")
            continue
        for pattern, why in WEAKENING_RULES:
            if weakening_hit(pattern, line, current):
                res.fail(f"diff {why}: {line.strip()[:90]}")

    # 6. new behaviour needs new tests
    if task.get("new_tests_required", True):
        touched_tests = [p for p in paths if TEST_PATH_RE.search(p)]
        res.details["test_files_touched"] = touched_tests
        if not touched_tests:
            res.fail("new_tests_required is set but no test file was added or changed")

    # 7. secrets
    for line in diff.splitlines():
        if not line.startswith("+"):
            continue
        for pattern, what in SECRET_RULES:
            if pattern.search(line):
                res.fail(f"diff appears to contain a {what}")

    if not res.ok:
        return res  # do not spend a container on a diff that already failed

    # 8/9. acceptance and lint, in a jailed container with no network beyond the proxy
    for label, commands in (("acceptance", task["acceptance"]),
                            ("lint", [task["lint_cmd"]] if task.get("lint_cmd") else [])):
        for command in commands:
            code, output = run_in_sandbox(tid, work, command,
                                          timeout_min=max(5, task["timeout_min"] // 2))
            res.details.setdefault(label, []).append(
                {"cmd": command, "exit": code, "tail": output[-1500:]})
            if code != 0:
                res.fail(f"{label} command failed ({code}): {command}")

    return res
