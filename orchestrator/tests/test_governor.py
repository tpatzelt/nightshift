"""Rate-limit detection, reset parsing, phone-command parsing and JSON extraction.

Run: python3 tests/test_governor.py
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nightshift as ns  # noqa: E402

# Never let a test write to the live state file or the orchestrator log.
_sandbox = Path(tempfile.mkdtemp(prefix="ns-gov-test-"))
ns.STATE_FILE = _sandbox / "state.json"
ns.ORCH_LOG = _sandbox / "orchestrator.log"
ns.USAGE_LOG = _sandbox / "usage.jsonl"
ns.HEARTBEAT = _sandbox / "heartbeat"

failures = []


def check(name, got, want):
    ok = got == want
    print(f"  [{'ok ' if ok else 'BAD'}] {name}" + ("" if ok else f" — got {got!r}, want {want!r}"))
    if not ok:
        failures.append(name)


def result(*, info=None, text="", stderr="", api_status=None, subtype="success"):
    r = ns.AgentResult("worker", "T-0001", Path("/tmp/x.jsonl"))
    r.rate_limit_info = info or {}
    r.result = {"result": text, "subtype": subtype, "api_error_status": api_status,
                "is_error": False, "num_turns": 1}
    r.stderr = stderr
    r.exit_code = 0
    return r


print("\n--- structured rate_limit_event (what the stream actually emits) ---")
allowed = {"status": "allowed", "resetsAt": 1790088600, "rateLimitType": "five_hour",
           "unifiedWindows": {"five_hour": {"utilization": 0.1, "resetsAt": 1790088600},
                              "seven_day": {"utilization": 0.04, "resetsAt": 1790175600}}}
check("status=allowed is not a limit", result(info=allowed).rate_limited, False)
check("the event's own resetsAt wins (the window that blocked us)",
      result(info=allowed).reset_epoch(), 1790088600.0)

soon, late = 1790088600, 1790175600
check("without a top-level resetsAt, rateLimitType picks the window",
      result(info={"status": "rejected", "rateLimitType": "five_hour",
                   "unifiedWindows": {"five_hour": {"resetsAt": soon},
                                      "seven_day": {"resetsAt": late}}}).reset_epoch(),
      float(soon))
check("with neither, the soonest reset wins, never the latest",
      result(info={"status": "rejected",
                   "unifiedWindows": {"five_hour": {"resetsAt": soon},
                                      "seven_day": {"resetsAt": late}}}).reset_epoch(),
      float(soon))
check("a daily window resetting sooner is not overridden by a weekly one",
      result(info={"status": "rejected", "rateLimitType": "daily",
                   "unifiedWindows": {"daily": {"resetsAt": soon},
                                      "weekly": {"resetsAt": late}}}).reset_epoch(),
      float(soon))
check("utilization is reported per window",
      result(info=allowed).utilization(), {"five_hour": 0.1, "seven_day": 0.04})

check("allowed_warning is NOT a limit: the request still went through",
      result(info={**allowed, "status": "allowed_warning",
                   "unifiedWindows": {"five_hour": {"utilization": 0.9,
                                                    "resetsAt": 1790088600}}}).rate_limited,
      False)
check("allowed_warning does not become a limit through the prose fallback either",
      result(info={**allowed, "status": "allowed_warning"},
             text="you are approaching your usage limit").rate_limited, False)

rejected = {**allowed, "status": "rejected"}
check("status=rejected is a limit", result(info=rejected).rate_limited, True)
check("status=blocked is a limit",
      result(info={**allowed, "status": "blocked"}).rate_limited, True)
check("no rate_limit_event and clean text is not a limit", result().rate_limited, False)
check("no rate_limit_event means no reset epoch", result().reset_epoch(), None)

print("\n--- fallbacks when no structured event arrives ---")
check("api_error_status 429 is a limit", result(api_status=429).rate_limited, True)
check("api_error_status '429' is a limit", result(api_status="429").rate_limited, True)
for phrase in ("Claude usage limit reached",
               "You've hit your usage limit, resets at 3:00pm",
               "limit reached for this window",
               "rate_limit_error",
               "429 Too Many Requests"):
    check(f"prose {phrase[:28]!r} is a limit", result(text=phrase).rate_limited, True)
check("stderr wording also counts",
      result(stderr="error: usage limit reached").rate_limited, True)
check("ordinary prose is not a limit",
      result(text="I refactored the parser and all tests pass.").rate_limited, False)

print("\n--- NS_FAKE_LIMIT (dry-run switch) ---")
os.environ["NS_FAKE_LIMIT"] = "1"
check("NS_FAKE_LIMIT forces a limit", result().rate_limited, True)
os.environ["NS_FAKE_LIMIT"] = "0"
check("NS_FAKE_LIMIT=0 does not", result().rate_limited, False)

print("\n--- reset hints from prose ---")
check("clock time is picked up", result(text="resets at 3:00pm").reset_hint(), "3:00pm")
check("iso timestamp is picked up",
      result(text="resets at 2026-09-23T04:00").reset_hint(), "2026-09-23T04:00")
check("retry-after is picked up", result(text='"retry-after": "600"').reset_hint(), "600")

print("\n--- governor sleep decisions ---")
cfg = {"governor": {"limit_backoff_min": [15, 30, 60, 120], "other_error_backoff_min": [5, 10, 20],
                    "max_other_errors": 6, "weekly_cap_notify_hours": 24}}
gov = ns.Governor(cfg)
state = {}
future = time.time() + 3600
gov.on_limit(state, result(info={**rejected, "resetsAt": future,
                                 "unifiedWindows": {"five_hour": {"resetsAt": future}}}))
check("a real reset time is used, plus a cushion",
      round(state["limit_until"] - future), 120)

state = {}
gov.on_limit(state, result(info={"status": "rejected"}))
check("no reset time falls back to the first backoff (15 min)",
      round((state["limit_until"] - time.time()) / 60), 15)
gov.on_limit(state, result(info={"status": "rejected"}))
check("the backoff escalates to 30 min",
      round((state["limit_until"] - time.time()) / 60), 30)

print("\n--- phone commands ---")
SECRET = "k7Q"
check("signed pause parses", ns.parse_command("k7Q: pause", SECRET), ["pause"])
check("no space after the colon parses", ns.parse_command("k7Q:resume", SECRET), ["resume"])
check("no colon parses", ns.parse_command("k7Q stop", SECRET), ["stop"])
check("case is normalised", ns.parse_command("k7Q: STATUS", SECRET), ["status"])
check("unsigned command ignored", ns.parse_command("pause", SECRET), [])
check("wrong secret ignored", ns.parse_command("xyz: pause", SECRET), [])
check("unknown verb ignored", ns.parse_command("k7Q: delete everything", SECRET), [])
check("empty message ignored", ns.parse_command("", SECRET), [])
check("secret alone ignored", ns.parse_command("k7Q:", SECRET), [])

print("\n--- final-message JSON extraction ---")
check("bare object", ns.extract_json_object('{"status":"done"}'), {"status": "done"})
check("object after prose",
      ns.extract_json_object('Here is my result:\n\n{"status":"done","summary":"x"}'),
      {"status": "done", "summary": "x"})
check("object inside a fenced block",
      ns.extract_json_object('```json\n{"verdict":"approve"}\n```'), {"verdict": "approve"})
check("last object wins when several appear",
      ns.extract_json_object('{"a":1} then {"b":2}'), {"b": 2})
check("nested objects survive",
      ns.extract_json_object('{"ops":[{"op":"add_task","task":{"id":"T-0002"}}]}'),
      {"ops": [{"op": "add_task", "task": {"id": "T-0002"}}]})
check("prose with braces but no JSON", ns.extract_json_object("use {} for an empty dict"), {})
check("no object at all", ns.extract_json_object("nothing here"), None)

print("\n--- liveness: a loop that is waiting is not a loop that is stuck ---")
ns.HEARTBEAT.write_text("stale\n")
ns._PROGRESS.update(at=0.0, beat=0.0, ping=0.0)
ns.mark_progress("unit test", force=True)
check("mark_progress moves the watchdog clock", ns._PROGRESS["at"] > 0.0, True)
check("mark_progress names the step", ns._PROGRESS["step"], "unit test")
check("mark_progress rewrites the heartbeat", ns.HEARTBEAT.read_text() != "stale\n", True)

beats = []
_real_heartbeat = ns.heartbeat
ns.heartbeat = lambda: beats.append(time.time())
limited = {"limit_until": time.time() + 0.4}
ns.Governor({"governor": {"limit_backoff_min": [15], "max_other_errors": 6,
                          "other_error_backoff_min": [5]}}).wait_if_limited(limited)
ns.heartbeat = _real_heartbeat
check("a quota wait keeps beating", len(beats) >= 1, True)
check("a quota wait ends by clearing the limit", limited["limit_until"], None)
check("a quota wait leaves the step visible", ns._PROGRESS["step"], "quota limit")

print("\n--- planner idle throttle: an empty backlog must not drive an Opus loop ---")
# run_planner reports whether it added work. When it did not, the backlog is still
# empty next iteration, so only the clock stops the loop asking again immediately.
_real_cfg = ns.load_config
ns.load_config = lambda: {"planner": {"idle_retry_min": 30, "merges_between_runs": 8,
                                      "daily_at_hour": 6}}
try:
    check("no planner run yet: idle run allowed",
          ns.planner_idle_ok({"last_planner_run": None}), True)
    check("a planner run a moment ago blocks the next idle run",
          ns.planner_idle_ok({"last_planner_run": ns.ts()}), False)
    old_run = (ns.now() - __import__("datetime").timedelta(minutes=31)).isoformat()
    check("a planner run 31 min ago allows the next idle run",
          ns.planner_idle_ok({"last_planner_run": old_run}), True)
    check("a forced planner_due ignores the throttle",
          ns.planner_due({"planner_due": True, "last_planner_run": ns.ts()}), True)
finally:
    ns.load_config = _real_cfg

print(f"\n{'ALL GOVERNOR TESTS PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
