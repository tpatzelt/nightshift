"""state.json under two writers: the main loop and the command listener.

Run: python3 tests/test_state.py
"""
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(tempfile.mkdtemp(prefix="ns-state-"))
os.environ["NS_DATA_DIR"] = str(ROOT / "data")
os.environ["NS_ARCHIVE_DIR"] = str(ROOT / "charters")
os.environ["NS_SOURCE_ROOT"] = str(ROOT / "coding")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nightshift as ns  # noqa: E402

failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else f'  -> {detail}'}")
    if not ok:
        failures.append(name)


ns.STATE_DIR.mkdir(parents=True, exist_ok=True)
ns.state_save(ns._default_state())

# A command arriving while the loop is mid-iteration: the loop armed a charter
# after the listener read state, and the listener's save must not undo it.
loop_state = ns.state_load()

listener_done = threading.Event()


def listener():
    state = ns.state_load()
    time.sleep(0.05)
    state["finish_requested"] = True
    ns.state_save(state)
    listener_done.set()


thread = threading.Thread(target=listener)
thread.start()

loop_state.update(charter_sha256="abc123", armed_at="2026-09-24T15:00:00+0200",
                  finish_requested=False)
time.sleep(0.1)
ns.state_save(loop_state)
thread.join()

final = ns._read_state_file()
check("the loop's arming survives a concurrent command",
      final["charter_sha256"] == "abc123", final)
check("the listener's command survives the loop's save",
      final["finish_requested"] is True, final)
check("the caller's dict is refreshed by the merge",
      loop_state["finish_requested"] is True, loop_state)

# The reverse order: the listener writes last, from a snapshot it took before the
# loop cleared the task in flight. The snapshot is per thread - which is what the
# loop and the listener are - so this half runs the listener on its own thread.
ns.state_save({**ns._read_state_file(), "current_task": "T-0042", "merges_total": 0})
loop_state = ns.state_load()


def stale_listener():
    stale = ns.state_load()               # sees T-0042 in flight
    ready.set()
    written.wait(2)
    stale["paused"] = True
    stale["pause_reason"] = "paused from phone"
    ns.state_save(stale)


ready, written = threading.Event(), threading.Event()
thread = threading.Thread(target=stale_listener)
thread.start()
ready.wait(2)
loop_state["current_task"] = None         # the task finished meanwhile
loop_state["merges_total"] = 7
ns.state_save(loop_state)
written.set()
thread.join()

final = ns._read_state_file()
check("a stale listener cannot revive a finished task", final["current_task"] is None, final)
check("the listener's pause is applied", final["paused"] is True, final)
check("the loop's counters survive", final["merges_total"] == 7, final)

# A key only one writer knows about is never dropped.
first = ns.state_load()
second = ns.state_load()
first["new_field"] = "kept"
ns.state_save(first)
second["merges_total"] = 9
ns.state_save(second)
check("a field written by the other thread is kept",
      ns._read_state_file().get("new_field") == "kept", ns._read_state_file())

print(f"\n{'ALL STATE TESTS PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
