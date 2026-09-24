#!/usr/bin/env python3
"""NIGHTSHIFT PreToolUse guard — defence in depth behind the managed deny rules.

Claude Code runs this before Bash, Edit, Write, MultiEdit and NotebookEdit and
passes the tool call as JSON on stdin. Exit 2 blocks the call and returns the
stderr text to the model; exit 0 allows it.

The network jail (§3) and the managed deny rules are the primary controls. This
hook exists so a single bypass in either one is not enough on its own, and so
every attempt is recorded in /work/.nightshift/guard.log for Tim to read later.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORK = Path("/work")
LOG = WORK / ".nightshift" / "guard.log"

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Read"}
PATH_KEYS = ("file_path", "notebook_path", "path")

# Each entry: (compiled pattern, why). Matched against the whole Bash command,
# so a pipeline or a && chain is caught wherever the offending part sits.
BASH_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:^|[\s;&|(`])(curl|wget|nc|ncat|socat|telnet|ssh|scp|sftp|rsync)\b"),
     "network tools are not available in the sandbox; use the proxy-aware "
     "package managers or report blocked"),
    (re.compile(r"\bgit\s+(push|remote|clone\s+(?:ssh|https?)://)"),
     "agents never push or add remotes; work stays on the local branch"),
    (re.compile(r"\bgit\s+config\s+--global\b"),
     "global git config is shared state and must not be changed"),
    (re.compile(r"\bsudo\b|\bsu\s|\bdoas\b"),
     "there is no privilege escalation in the sandbox"),
    (re.compile(r"\bdocker\b|\bpodman\b|\bnerdctl\b|/var/run/docker\.sock"),
     "agents have no access to any Docker daemon"),
    (re.compile(r"(^|[\s;&|(])(\.?/)?(etc/|proc/\d+/environ|proc/self/environ)"),
     "/etc and process environments are off limits"),
    (re.compile(r"~/\.claude|/home/\w+/\.claude|\$HOME/\.claude|\.claude\.json"),
     "Claude Code's own configuration must not be read or modified"),
    (re.compile(r"/etc/claude-code|managed-settings\.json"),
     "the managed policy file must not be read or modified"),
    (re.compile(r"\b(mount|umount|losetup|nsenter|unshare|setcap)\b"),
     "namespace and mount operations are not permitted"),
    (re.compile(r"chmod\s+[^\n;|&]*(\+s|[24][0-7]{3})"),
     "setuid/setgid bits are not permitted"),
    (re.compile(r":\(\)\s*\{.*\}\s*;?\s*:|\bfork\s*bomb\b"),
     "fork bomb pattern"),
    (re.compile(r"\bnpm\s+config\s+set\s+registry|\bpip\s+config\s+set\b|"
                r"--index-url|--extra-index-url|PIP_INDEX_URL|npm_config_registry"),
     "package registries are fixed by the sandbox and must not be overridden"),
    (re.compile(r"\b(shutdown|reboot|halt|poweroff)\b"),
     "power management is not available"),
    (re.compile(r"/secrets\b|oauth_token|CLAUDE_CODE_OAUTH_TOKEN|ANTHROPIC_API_KEY"),
     "credentials are never readable from a task"),
]


def ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def audit(decision: str, tool: str, detail: str, reason: str = "") -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": ts(), "decision": decision, "tool": tool,
                "task": os.environ.get("NS_TASK_ID", ""),
                "detail": detail[:1000], "reason": reason,
            }) + "\n")
    except OSError:
        pass  # a read-only or full /work must not turn into an allow


def block(tool: str, detail: str, reason: str) -> None:
    audit("block", tool, detail, reason)
    print(f"NIGHTSHIFT guard blocked this call: {reason}", file=sys.stderr)
    sys.exit(2)


def allow(tool: str, detail: str) -> None:
    audit("allow", tool, detail)
    sys.exit(0)


def protected_globs() -> list[str]:
    raw = os.environ.get("NS_PROTECTED", "")
    return [p for p in raw.split(":") if p.strip()]


def check_bash(command: str) -> None:
    if not command.strip():
        block("Bash", command, "empty command")
    for pattern, reason in BASH_RULES:
        if pattern.search(command):
            block("Bash", command, reason)
    allow("Bash", command)


def check_path(tool: str, raw_path: str) -> None:
    if not raw_path:
        block(tool, raw_path, "no file path in the tool call")
    try:
        resolved = Path(raw_path).resolve()
    except (OSError, ValueError) as exc:
        block(tool, raw_path, f"path could not be resolved ({exc})")
    # /work is the only writable surface; /plan is read-only and may be read.
    if tool == "Read" and (resolved == Path("/plan") or Path("/plan") in resolved.parents):
        allow(tool, str(resolved))
    if resolved != WORK and WORK not in resolved.parents:
        block(tool, str(resolved), "path is outside /work")
    rel = str(resolved.relative_to(WORK))
    for glob in protected_globs():
        if fnmatch.fnmatch(rel, glob) or fnmatch.fnmatch(rel, glob.rstrip("/") + "/*"):
            block(tool, rel, f"path matches the task's protected_paths ({glob})")
    if rel.startswith(".nightshift"):
        block(tool, rel, ".nightshift is orchestrator bookkeeping, not task scope")
    allow(tool, str(resolved))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        block("unknown", "", f"hook payload was not valid JSON ({exc})")
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    if tool == "Bash":
        check_bash(str(tool_input.get("command", "")))
    if tool in FILE_TOOLS:
        for key in PATH_KEYS:
            if tool_input.get(key):
                check_path(tool, str(tool_input[key]))
        block(tool, json.dumps(tool_input)[:200], "file tool call carried no path")
    allow(tool, json.dumps(tool_input)[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
