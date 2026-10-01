"""Gate tests against real git repositories, one per rule.

Run: python3 tests/test_gates.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gates  # noqa: E402

BASE = "agent/integration"
TASK = {
    "id": "T-0001", "project": "toy", "roadmap_ref": "M1", "charter_goal": "G1",
    "title": "t", "why": "w", "acceptance": ["true"], "allowed_paths": ["src/**", "tests/**"],
    "protected_paths": ["Makefile", ".github/**"], "max_diff_lines": 400,
    "timeout_min": 10, "max_turns": 20, "status": "ready", "new_tests_required": True,
}
DONE = {"status": "done", "summary": "did the thing"}
failures = []


def sh(cwd, *args):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def make_repo(files: dict) -> Path:
    root = Path(tempfile.mkdtemp(prefix="ns-gate-"))
    sh(root, "git", "init", "-q", "-b", BASE)
    sh(root, "git", "config", "user.email", "t@example.com")
    sh(root, "git", "config", "user.name", "t")
    for name, body in files.items():
        f = root / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body)
    sh(root, "git", "add", "-A")
    sh(root, "git", "commit", "-qm", "base")
    sh(root, "git", "checkout", "-qb", "agent/T-0001")
    return root


def commit(root: Path, changes: dict, *, remove=(), message="T-0001: change"):
    for name, body in changes.items():
        f = root / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body)
    for name in remove:
        sh(root, "git", "rm", "-q", name)
    sh(root, "git", "add", "-A")
    sh(root, "git", "commit", "-qm", message)


def fake_sandbox(exit_code=0, output="ok"):
    return lambda tid, work, cmd, timeout_min: (exit_code, output)


def check(name, ok, detail=""):
    print(f"  [{'ok ' if ok else 'BAD'}] {name}" + ("" if ok else f" — {detail}"))
    if not ok:
        failures.append(name)


def expect(name, res, should_pass, must_mention=None):
    ok = res.ok == should_pass
    if ok and must_mention:
        ok = any(must_mention in f for f in res.failures)
    print(f"  [{'ok ' if ok else 'BAD'}] {name}" +
          ("" if ok else f" — ok={res.ok}, failures={res.failures[:2]}"))
    if not ok:
        failures.append(name)


BASE_FILES = {
    "src/app.py": "def add(a, b):\n    return a + b\n",
    "tests/test_app.py": "from src.app import add\n\ndef test_add():\n    assert add(1, 2) == 3\n",
    "Makefile": "test:\n\tpytest\n",
    ".github/workflows/ci.yml": "on: push\n",
}

print("\n--- gate 1: worker verdict ---")
r = make_repo(BASE_FILES)
commit(r, {"src/app.py": "def add(a, b):\n    return a + b\n\ndef sub(a, b):\n    return a - b\n",
           "tests/test_app.py": "from src.app import add, sub\n\ndef test_add():\n    assert add(1,2)==3\n\ndef test_sub():\n    assert sub(3,1)==2\n"})
expect("worker status=done passes", gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), True)
expect("worker status=blocked fails",
       gates.run_gates(TASK, r, BASE, {"status": "blocked", "summary": "x"}, fake_sandbox()),
       False, "not 'done'")
expect("missing worker JSON fails",
       gates.run_gates(TASK, r, BASE, {}, fake_sandbox()), False, "not 'done'")

print("\n--- gate 2: commits and clean tree ---")
r = make_repo(BASE_FILES)
expect("no commits fails", gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), False,
       "no commits")
r = make_repo(BASE_FILES)
commit(r, {"src/app.py": "x = 1\n", "tests/test_app.py": "def test_x():\n    assert True is not False\n"})
(r / "src" / "stray.py").write_text("leftover\n")
expect("dirty working tree fails", gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()),
       False, "not clean")

print("\n--- gate 3: diff size ---")
r = make_repo(BASE_FILES)
commit(r, {"src/big.py": "\n".join(f"line_{i} = {i}" for i in range(300)),
           "tests/test_big.py": "def test_big():\n    import src.big\n    assert src.big.line_0 == 0\n"})
expect("diff over the cap fails",
       gates.run_gates({**TASK, "max_diff_lines": 50}, r, BASE, DONE, fake_sandbox()),
       False, "limit is 50")
expect("diff under the cap passes",
       gates.run_gates({**TASK, "max_diff_lines": 500}, r, BASE, DONE, fake_sandbox()), True)

print("\n--- gate 4: scope ---")
r = make_repo(BASE_FILES)
commit(r, {"docs/readme.md": "hi\n", "tests/test_app.py": "def test_a():\n    assert 1 == 1\n"})
expect("path outside allowed_paths fails",
       gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), False, "outside allowed_paths")
r = make_repo(BASE_FILES)
commit(r, {"Makefile": "test:\n\tpytest -q\n", "tests/test_app.py": "def test_a():\n    assert 1 == 1\n"})
expect("protected path fails",
       gates.run_gates({**TASK, "allowed_paths": ["**/*"]}, r, BASE, DONE, fake_sandbox()),
       False, "protected_paths")

print("\n--- gate 5: the suite must not be weakened ---")
r = make_repo(BASE_FILES)
commit(r, {}, remove=["tests/test_app.py"])
expect("deleting a test file fails",
       gates.run_gates({**TASK, "new_tests_required": False}, r, BASE, DONE, fake_sandbox()),
       False, "was deleted")
r = make_repo(BASE_FILES)
commit(r, {"tests/test_app.py": "import pytest\n\n@pytest.mark.skip\ndef test_add():\n    assert False\n"})
expect("adding a skip marker fails",
       gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), False, "skip/xfail")
r = make_repo(BASE_FILES)
commit(r, {"tests/test_app.py": "import pytest\n\n@pytest.mark.xfail\ndef test_add():\n    assert False\n"})
expect("adding an xfail marker fails",
       gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), False, "skip/xfail")
r = make_repo(BASE_FILES)
commit(r, {"src/run.sh": "pytest || true\n", "tests/test_app.py": "def test_a():\n    assert 1 == 1\n"})
expect("'|| true' fails", gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), False, "|| true")
r = make_repo(BASE_FILES)
commit(r, {"tests/test_app.py": 'def test_a():\n    assert "|| true" not in open("run.sh").read()\n'})
expect("'|| true' inside a Python string is a test about it, not a command (run 4 T-0040)",
       gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), True)
r = make_repo(BASE_FILES)
commit(r, {"tests/test_app.py": 'import subprocess\n\ndef test_a():\n    subprocess.run("pytest", shell=True) or True || true\n'})
expect("'|| true' outside a string in a .py file still fails",
       gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), False, "|| true")
r = make_repo(BASE_FILES)
commit(r, {"src/ci.yaml": 'run: "pytest || true"\n', "tests/test_app.py": "def test_a():\n    assert 1 == 1\n"})
expect("a quoted '|| true' in YAML still runs, so it still fails",
       gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), False, "|| true")

print("\n--- gate 1 says why a worker stopped, when the loop knows ---")
r = make_repo(BASE_FILES)
stopped = gates.run_gates(TASK, r, BASE, {}, fake_sandbox(),
                          worker_stopped="turn limit reached (41 turns, limit 40)")
expect("a worker that ran out of turns is named as such",
       stopped, False, "turn limit reached")
check("and not as status=None", "status=None" not in stopped.report(), stopped.report())
expect("without a known reason, the old message stays",
       gates.run_gates(TASK, r, BASE, {}, fake_sandbox()), False, "status=None")
expect("a worker that reported 'blocked' keeps its own status",
       gates.run_gates(TASK, r, BASE, {"status": "blocked"}, fake_sandbox(),
                       worker_stopped="timed out"), False, "status='blocked'")

print("\n--- gate 6: new tests required ---")
r = make_repo(BASE_FILES)
commit(r, {"src/app.py": "def add(a, b):\n    return a + b\n\ndef mul(a, b):\n    return a * b\n"})
expect("source-only change fails when tests are required",
       gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), False, "no test file")
expect("source-only change passes when tests are not required",
       gates.run_gates({**TASK, "new_tests_required": False}, r, BASE, DONE, fake_sandbox()),
       True)

# A repo whose whole suite is a shell check script, like the Jekyll site's
# scripts/check-site.sh, still satisfies gate 6 by extending that script.
SITE_FILES = {
    "index.html": "<h1>hi</h1>\n",
    "scripts/check-site.sh": "#!/bin/bash\nset -e\ngrep -q '<h1' index.html\n",
}
SITE_TASK = {**TASK, "allowed_paths": ["index.html", "scripts/**", "_data/**"]}
r = make_repo(SITE_FILES)
commit(r, {"index.html": "<h1>hi</h1>\n<section id=\"work\"></section>\n"})
expect("check script repo: markup-only change fails",
       gates.run_gates(SITE_TASK, r, BASE, DONE, fake_sandbox()), False, "no test file")
r = make_repo(SITE_FILES)
commit(r, {"index.html": "<h1>hi</h1>\n<section id=\"work\"></section>\n",
           "scripts/check-site.sh": "#!/bin/bash\nset -e\ngrep -q '<h1' index.html\n"
                                    "grep -q 'id=\"work\"' index.html\n"})
expect("check script repo: extending check-site.sh satisfies gate 6",
       gates.run_gates(SITE_TASK, r, BASE, DONE, fake_sandbox()), True)
r = make_repo(SITE_FILES)
commit(r, {}, remove=["scripts/check-site.sh"])
expect("check script repo: deleting check-site.sh fails",
       gates.run_gates({**SITE_TASK, "new_tests_required": False}, r, BASE, DONE,
                       fake_sandbox()),
       False, "was deleted")

print("\n--- gate 7: secrets ---")
for secret, label in (("sk-ant-oat01-" + "A" * 40, "oauth token"),
                      ("sk-or-v1-" + "c" * 40, "openrouter key"),
                      ("BSA" + "D" * 25, "brave key"),
                      ("123456789:AA" + "e" * 33, "telegram token"),
                      ("ghp_" + "b" * 36, "github token"),
                      ('password = "hunter2hunter2"', "hard-coded password")):
    r = make_repo(BASE_FILES)
    commit(r, {"src/conf.py": f'TOKEN = "{secret}"\n' if "=" not in secret else secret + "\n",
               "tests/test_app.py": "def test_a():\n    assert 1 == 1\n"})
    expect(f"{label} in the diff fails",
           gates.run_gates(TASK, r, BASE, DONE, fake_sandbox()), False, "contain a")

print("\n--- gates 8/9: acceptance and lint ---")
r = make_repo(BASE_FILES)
commit(r, {"src/app.py": "def add(a, b):\n    return a + b\n",
           "tests/test_app.py": "def test_a():\n    assert 1 == 1\n"})
expect("failing acceptance command fails",
       gates.run_gates(TASK, r, BASE, DONE, fake_sandbox(1, "pytest: 1 failed")),
       False, "acceptance command failed")
expect("passing acceptance command passes",
       gates.run_gates(TASK, r, BASE, DONE, fake_sandbox(0)), True)
expect("failing lint fails",
       gates.run_gates({**TASK, "lint_cmd": "ruff check ."}, r, BASE, DONE, fake_sandbox(1)),
       False, "lint command failed")

print("\n--- the gate keeps what the failing command printed ---")
r = make_repo(BASE_FILES)
commit(r, {"src/app.py": "def add(a, b):\n    return a + b\n",
           "tests/test_app.py": "def test_a():\n    assert 1 == 1\n"})
failed = gates.run_gates(TASK, r, BASE, DONE,
                         fake_sandbox(1, "E   assert 1 == 2\n1 failed in 0.4s"))
out = failed.failing_output()
check("failing output names the command", "$ true" in out, out[:120])
check("failing output carries the error", "assert 1 == 2" in out, out[:120])
check("failing output records the exit code", "exit 1" in out, out[:120])
check("a passing gate run has no failing output",
      gates.run_gates(TASK, r, BASE, DONE, fake_sandbox(0, "1 passed")).failing_output() == "")
check("lint output is kept too",
      "ruff check ." in gates.run_gates({**TASK, "lint_cmd": "ruff check ."}, r, BASE, DONE,
                                        fake_sandbox(1, "F401 unused import")).failing_output())

print(f"\n{'ALL GATE TESTS PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
