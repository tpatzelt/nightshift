"""Validator tests — the rules that stop a drifting planner from widening its own leash.

Run: python3 tests/test_plan.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import plan  # noqa: E402

GOALS = ["G1", "G2"]
BASE = {
    "id": "T-0001", "project": "foo", "roadmap_ref": "M1", "charter_goal": "G1",
    "title": "Parse config file", "why": "M1 needs config loading",
    "acceptance": ["make test"], "allowed_paths": ["src/**", "tests/**"],
    "protected_paths": ["Makefile", ".github/**"], "max_diff_lines": 400,
    "timeout_min": 45, "max_turns": 60, "status": "ready",
}

failures = []


def check(name, fn, *, raises=False):
    try:
        fn()
        ok = not raises
        detail = "" if ok else "expected PlanError, none raised"
    except plan.PlanError as exc:
        ok = raises
        detail = "" if ok else f"unexpected PlanError: {exc}"
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    print(f"  [{'ok ' if ok else 'BAD'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def task(**over):
    return {**BASE, **over}


print("\n--- task schema ---")
check("valid task accepted", lambda: plan.validate_task(task(), goals=GOALS))
check("missing field rejected",
      lambda: plan.validate_task({k: v for k, v in BASE.items() if k != "acceptance"},
                                 goals=GOALS), raises=True)
check("bad id shape rejected", lambda: plan.validate_task(task(id="TASK1"), goals=GOALS),
      raises=True)
check("goal outside charter rejected",
      lambda: plan.validate_task(task(charter_goal="G9"), goals=GOALS), raises=True)
check("catch-all allowed_paths rejected",
      lambda: plan.validate_task(task(allowed_paths=["**"]), goals=GOALS), raises=True)
check("max_diff_lines above ceiling rejected",
      lambda: plan.validate_task(task(max_diff_lines=801), goals=GOALS), raises=True)
check("max_diff_lines at ceiling accepted",
      lambda: plan.validate_task(task(max_diff_lines=800), goals=GOALS))
check("unknown status rejected", lambda: plan.validate_task(task(status="wip"), goals=GOALS),
      raises=True)
check("empty acceptance rejected", lambda: plan.validate_task(task(acceptance=[]), goals=GOALS),
      raises=True)

# Acceptance lines run under bash verbatim. T-0069 parked after two worker attempts
# because its acceptance was written as English, and neither the worker nor the gate
# could tell a bad spec from a bad diff.
def strict(**over):
    return lambda: plan.validate_task(task(**over), goals=GOALS,
                                      acceptance_must_run=True)


check("shell-runnable acceptance accepted",
      strict(acceptance=["uv run pytest -q",
                         "! grep -qF 'assert \"x\" in reply' tests/t.py",
                         "CI=1 make test"]))
check("acceptance with a bash syntax error rejected",
      strict(acceptance=["uv run pytest -q passes (388 passed, 1 skipped)"]), raises=True)
check("acceptance written as an English sentence rejected",
      strict(acceptance=["Each of the five tests asserts the reply with == "
                         "against the full string"]), raises=True)
check("capitalised two-word command still accepted",
      strict(acceptance=["Rscript tests/run.R"]))
check("blank acceptance line rejected", strict(acceptance=["   "]), raises=True)
# Parked and done files are history: a loader that refused them would take the
# planner, the auditor and the status command down with it.
check("prose acceptance already on disk still loads",
      lambda: plan.validate_task(
          task(acceptance=["uv run pytest -q passes (388 passed, 1 skipped)"]),
          goals=GOALS))


def normalises(field, given, want):
    def run():
        got = plan.validate_task(task(**{field: given}), goals=GOALS)[field]
        assert got == want, f"got {got!r}"
    return run


check("notes given as a string become a list",
      normalises("notes", "one long planner note", ["one long planner note"]))
check("notes given as null become an empty list", normalises("notes", None, []))
check("depends_on given as a string becomes a list",
      normalises("depends_on", "T-0002", ["T-0002"]))
check("acceptance given as a string becomes a list",
      normalises("acceptance", "make test", ["make test"]))
check("allowed_paths given as a string becomes a list",
      normalises("allowed_paths", "src/**", ["src/**"]))

print("\n--- planner ops ---")
existing = {"T-0001": plan.validate_task(task(), goals=GOALS)}


def ops(*items):
    return plan.validate_planner_output({"ops": list(items)}, goals=GOALS, existing=existing)


def accepted_count(*items):
    return len(ops(*items))


def expect(name, n, *items):
    got = accepted_count(*items)
    ok = got == n
    print(f"  [{'ok ' if ok else 'BAD'}] {name} — accepted {got}, expected {n}")
    if not ok:
        failures.append(name)


expect("valid add_task accepted", 1,
       {"op": "add_task", "task": task(id="T-0002")})
expect("add_task with unknown goal rejected", 0,
       {"op": "add_task", "task": task(id="T-0003", charter_goal="G7")})
expect("add_task duplicating an id rejected", 0,
       {"op": "add_task", "task": task(id="T-0001")})
expect("more than 10 new tasks: first 10 accepted", 10,
       *[{"op": "add_task", "task": task(id=f"T-01{i:02d}")} for i in range(12)])
expect("update_task shrinking protected_paths rejected", 0,
       {"op": "update_task", "id": "T-0001", "fields": {"protected_paths": ["Makefile"]}})
expect("update_task extending protected_paths accepted", 1,
       {"op": "update_task", "id": "T-0001",
        "fields": {"protected_paths": ["Makefile", ".github/**", "docs/**"]}})
expect("update_task resetting attempts rejected", 0,
       {"op": "update_task", "id": "T-0001", "fields": {"attempts": 0}}
       if existing["T-0001"].get("attempts", 0) > 0 else
       {"op": "update_task", "id": "T-0001", "fields": {"attempts": -1}})
expect("update_task raising max_diff_lines past the ceiling rejected", 0,
       {"op": "update_task", "id": "T-0001", "fields": {"max_diff_lines": 5000}})
expect("park_task without a reason rejected", 0, {"op": "park_task", "id": "T-0001"})
expect("park_task with a reason accepted", 1,
       {"op": "park_task", "id": "T-0001", "reason": "blocked on G2"})
expect("milestone citing unknown goal rejected", 0,
       {"op": "add_milestone", "id": "M4", "charter_goal": "G9", "title": "x",
        "exit_criteria": "y"})
expect("valid milestone accepted", 1,
       {"op": "add_milestone", "id": "M4", "charter_goal": "G2", "title": "x",
        "exit_criteria": "y"})
expect("reorder with unknown id rejected", 0, {"op": "reorder", "ids": ["T-0404"]})
expect("unsupported op rejected", 0, {"op": "delete_everything"})
expect("reorder may reference a task added in the same batch", 2,
       {"op": "add_task", "task": task(id="T-0200")},
       {"op": "reorder", "ids": ["T-0001", "T-0200"]})
expect("update_task may target a task added in the same batch", 2,
       {"op": "add_task", "task": task(id="T-0201")},
       {"op": "update_task", "id": "T-0201", "fields": {"max_turns": 40}})
expect("one bad op does not sink the good ones", 1,
       {"op": "add_milestone", "id": "M5", "charter_goal": "G1", "title": "x",
        "exit_criteria": "y"},
       {"op": "reorder", "ids": ["T-0404"]})

print("\n--- adr ---")
check("adr required", lambda: plan.validate_adr({"ops": []}), raises=True)
check("adr missing a section rejected",
      lambda: plan.validate_adr({"adr": {"title": "t", "context": "c", "decision": "d"}}),
      raises=True)
check("complete adr accepted",
      lambda: plan.validate_adr({"adr": {"title": "t", "context": "c", "decision": "d",
                                         "consequences": "x"}}))

print("\n--- reviewer ---")
GOOD = {"aligned": True, "meets_acceptance_intent": True, "scope_ok": True,
        "tests_meaningful": True, "risk": "low", "verdict": "approve",
        "notes": "looks right"}
check("valid review accepted", lambda: plan.validate_reviewer_output(dict(GOOD)))
check("non-boolean flag rejected",
      lambda: plan.validate_reviewer_output({**GOOD, "aligned": "yes"}), raises=True)
check("unknown verdict rejected",
      lambda: plan.validate_reviewer_output({**GOOD, "verdict": "lgtm"}), raises=True)
check("unknown risk rejected",
      lambda: plan.validate_reviewer_output({**GOOD, "risk": "spicy"}), raises=True)
check("empty notes rejected",
      lambda: plan.validate_reviewer_output({**GOOD, "notes": "  "}), raises=True)


def merge_check(name, review, want):
    got = plan.review_passes(review)
    ok = got == want
    print(f"  [{'ok ' if ok else 'BAD'}] {name} — merges={got}, expected {want}")
    if not ok:
        failures.append(name)


merge_check("approve + low risk merges", GOOD, True)
merge_check("approve but high risk does not merge", {**GOOD, "risk": "high"}, False)
merge_check("approve but not aligned does not merge", {**GOOD, "aligned": False}, False)
merge_check("approve but scope_ok false does not merge", {**GOOD, "scope_ok": False}, False)
merge_check("approve but tests not meaningful does not merge",
            {**GOOD, "tests_meaningful": False}, False)
merge_check("revise does not merge", {**GOOD, "verdict": "revise"}, False)

print(f"\n{'ALL PLAN TESTS PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
