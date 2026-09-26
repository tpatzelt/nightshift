#!/usr/bin/env python3
"""NIGHTSHIFT orchestrator.

Runs unattended inside the nightshift Compose project and drives throwaway Claude
Code agent containers on the inner (DinD) daemon. Phase 1 provides the plumbing:
config, state, logging, notifications, the dead-man's switch and the docker client.
Later phases build the plan/gate/review loop on top of it.

Talks to the inner daemon only, through DOCKER_HOST=tcp://dind:2376.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

import gates
import plan
import runs

APP = Path(__file__).resolve().parent
DATA = Path(os.environ.get("NS_DATA_DIR", "/data"))
PLAN = DATA / "plan"
STATE_DIR = DATA / "state"
LOGS = DATA / "logs"
STATE_FILE = STATE_DIR / "state.json"
HEARTBEAT = STATE_DIR / "heartbeat"
USAGE_LOG = STATE_DIR / "usage.jsonl"
STOP_FILE = DATA / "STOP"
ORCH_LOG = LOGS / "orchestrator.log"

CONFIG_PATH = APP / "config.yaml"
INTEGRATION = "agent/integration"


# --------------------------------------------------------------------------- util
def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def ts() -> str:
    return now().strftime("%Y-%m-%dT%H:%M:%S%z")


def log(msg: str, *, level: str = "INFO") -> None:
    line = f"{ts()} [{level}] {msg}"
    print(line, flush=True)
    try:
        ORCH_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ORCH_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as exc:  # a full disk must never kill the loop
        print(f"{ts()} [WARN] cannot write {ORCH_LOG}: {exc}", flush=True)


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


CLIP_MARKER = "\n  […clipped…]\n"


def clip(text: str, limit: int) -> str:
    """Shorten a reason to `limit` characters, keeping both of its ends.

    A reviewer's verdict opens with what the work got right and names the
    defect last, so text[:limit] threw away the only part the next attempt
    needed. T-0014 was parked on a reason that stopped at "...the mktemp gate
    shows it fails when _data/projects.yml is removed, " and the re-issues
    never learned what to fix. A gate report is the other way round, failures
    first, so neither end can be the one to drop.
    """
    text = text.strip()
    if len(text) <= limit:
        return text
    head = max(0, limit * 2 // 5)
    tail = max(0, limit - head - len(CLIP_MARKER))
    if not tail:
        return text[:limit]
    return text[:head].rstrip() + CLIP_MARKER + text[-tail:].lstrip()


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


# -------------------------------------------------------------------------- state
def _default_state() -> dict:
    return {
        "version": 1,
        "paused": False,
        "pause_reason": "",
        "current_task": None,
        "consecutive_failures": 0,
        "merges_total": 0,
        "merges_since_planner": 0,
        "charter_sha256": None,
        "last_ntfy_cmd_id": None,
        "last_planner_run": None,
        "last_auditor_run": None,
        "last_housekeeping": None,
        "limit_until": None,
        "other_error_streak": 0,
        # Consecutive planner runs that validated and applied nothing: the
        # charter's own way of saying it has run out of work.
        "idle_planner_streak": 0,
        "finish_requested": False,
    }


# state.json has two writers - the main loop and the command listener - and used
# to be written whole from whichever dict the thread happened to be holding. A
# command that arrived while the loop was mid-iteration therefore wrote back the
# loop's state as it had been seconds earlier: a `finish` landing during the ntfy
# poll silently un-armed a charter the loop had just armed. Each writer now merges
# against what is actually on disk, keeping only the fields it changed itself.
_STATE_LOCK = threading.RLock()
_SEEN = threading.local()


def _read_state_file() -> dict:
    if not STATE_FILE.exists():
        return _default_state()
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log(f"state.json unreadable ({exc}); starting from defaults", level="ERROR")
        return _default_state()


def state_load() -> dict:
    with _STATE_LOCK:
        data = _read_state_file()
    _SEEN.snapshot = dict(data)          # what this thread was handed
    return data


def state_save(state: dict) -> None:
    """Write this thread's changes without undoing another thread's.

    Three-way merge: a key this thread did not touch takes the value on disk, so
    a listener saving `paused` cannot revive a `current_task` the loop has since
    cleared, and the loop cannot un-pause itself by saving a stale snapshot.
    """
    with _STATE_LOCK:
        seen = getattr(_SEEN, "snapshot", None)
        merged = dict(state)
        if seen is not None:
            disk = _read_state_file()
            for key, value in disk.items():
                unchanged_here = key in seen and state.get(key) == seen.get(key)
                if (unchanged_here or key not in state) and value != state.get(key):
                    merged[key] = value
        write_atomic(STATE_FILE, json.dumps(merged, indent=2, sort_keys=True) + "\n")
        _SEEN.snapshot = dict(merged)
        state.update(merged)             # the caller's dict must not go stale


def heartbeat() -> None:
    write_atomic(HEARTBEAT, ts() + "\n")


# ------------------------------------------------------------------ notifications
def ntfy(message: str, *, title: str = "nightshift", priority: str = "default",
         tags: str = "", topic_suffix: str = "") -> bool:
    """Push to ntfy. Never raises: a failed notification must not stop the loop."""
    topic = env("NTFY_TOPIC")
    server = env("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
    if not topic:
        log("NTFY_TOPIC unset, cannot notify", level="WARN")
        return False
    url = f"{server}/{topic}{topic_suffix}"
    # HTTP headers are latin-1; an emoji in a title raises UnicodeEncodeError and
    # would otherwise take down the very notification reporting a success.
    def header_safe(value: str) -> str:
        return value.encode("latin-1", "replace").decode("latin-1")

    headers = {"Title": header_safe(title), "Priority": priority}
    if tags:
        headers["Tags"] = header_safe(tags)
    req = urllib.request.Request(url, data=message.encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= resp.status < 300
            log(f"ntfy -> {url} ({resp.status})")
            return ok
    except (urllib.error.URLError, OSError) as exc:
        log(f"ntfy failed: {exc}", level="WARN")
        return False


def hc_ping(suffix: str = "", body: str = "") -> bool:
    """Ping the healthchecks.io dead-man's switch. Never raises."""
    base = env("HC_PING_URL")
    if not base:
        return False
    url = base.rstrip("/") + suffix
    data = body.encode("utf-8") if body else None
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, data=data, method="POST"), timeout=15
        ) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, OSError) as exc:
        log(f"healthchecks ping failed: {exc}", level="WARN")
        return False


# ------------------------------------------------------------------------ liveness
# The watchdog and the container healthcheck both ask the same question: when did
# the loop last make progress? Only the top of the main loop used to answer it, so
# everything the loop legitimately waits on - a 45-minute agent run, a three-hour
# quota sleep - read as a hang, and the watchdog restarted a process that was doing
# exactly what it should. Anything that waits now says so here instead.
_PROGRESS = {"at": time.time(), "step": "startup", "beat": 0.0, "ping": 0.0}
_BEAT_EVERY_SEC = 15      # the heartbeat file is cheap, but not once per streamed event
_PING_EVERY_SEC = 300     # healthchecks.io is a dead-man's switch, not a metric


def mark_progress(step: str | None = None, *, force: bool = False) -> None:
    """Record that the loop is alive, and refresh the signals that report it."""
    moment = time.time()
    _PROGRESS["at"] = moment
    if step:
        _PROGRESS["step"] = step
    if force or moment - _PROGRESS["beat"] >= _BEAT_EVERY_SEC:
        _PROGRESS["beat"] = moment
        heartbeat()
    if force or moment - _PROGRESS["ping"] >= _PING_EVERY_SEC:
        _PROGRESS["ping"] = moment
        hc_ping()


# ------------------------------------------------------------------- docker (inner)
class DockerError(RuntimeError):
    pass


def docker(*args: str, timeout: int = 120, check: bool = True,
           stdin: str | None = None) -> subprocess.CompletedProcess:
    """Run the docker CLI against the inner daemon."""
    cmd = ["docker", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          input=stdin)
    if check and proc.returncode != 0:
        raise DockerError(
            f"docker {' '.join(args[:4])} exited {proc.returncode}: "
            f"{proc.stderr.strip()[:500]}"
        )
    return proc


def inner_daemon_id() -> str:
    return docker("info", "--format", "{{.ID}}", timeout=60).stdout.strip()


# --------------------------------------------------------------------------- disk
def disk_free_gb(path: Path = DATA) -> float:
    usage = shutil.disk_usage(path)
    return usage.free / (1024 ** 3)


def disk_used_pct(path: Path = DATA) -> float:
    usage = shutil.disk_usage(path)
    return 100.0 * usage.used / usage.total



# ----------------------------------------------------------------------- jail
# Everything below runs on the inner daemon. The jail network is --internal, so
# it has no route out at all; the squid proxy is dual-homed (jail + inner bridge)
# and is the only door. The DOCKER-USER rules in firewall.sh are the second layer.
def jail_cfg() -> dict:
    return {
        "net": env("NS_JAIL_NET", "nightshift-jail"),
        "subnet": env("NS_JAIL_SUBNET", "172.30.99.0/24"),
        "proxy_ip": env("NS_PROXY_IP", "172.30.99.2"),
        "proxy_port": env("NS_PROXY_PORT", "3128"),
        "squid_image": env("NS_SQUID_IMAGE"),
        "alpine_image": env("NS_ALPINE_IMAGE"),
        "netadmin_tag": env("NS_NETADMIN_IMAGE_TAG", "nightshift-netadmin:3.22-1"),
        "agent_tag": env("NS_AGENT_IMAGE_TAG"),
        "node_image": env("NS_NODE_IMAGE"),
        "uv_image": env("NS_UV_IMAGE"),
        "agent_python": env("NS_AGENT_PYTHON", "3.14"),
        "cc_version": env("NS_CLAUDE_CODE_VERSION"),
    }


def proxy_url() -> str:
    c = jail_cfg()
    return f"http://{c['proxy_ip']}:{c['proxy_port']}"


def image_exists(tag: str) -> bool:
    return docker("image", "inspect", tag, check=False, timeout=60).returncode == 0


def ensure_images(rebuild: bool = False) -> None:
    c = jail_cfg()
    if rebuild or not image_exists(c["agent_tag"]):
        log(f"building {c['agent_tag']} on the inner daemon")
        docker("build", "--build-arg", f"NS_NODE_IMAGE={c['node_image']}",
               "--build-arg", f"NS_UV_IMAGE={c['uv_image']}",
               "--build-arg", f"NS_AGENT_PYTHON={c['agent_python']}",
               "--build-arg", f"NS_CLAUDE_CODE_VERSION={c['cc_version']}",
               "-t", c["agent_tag"], "/sandbox", timeout=1800)
    if rebuild or not image_exists(c["netadmin_tag"]):
        log(f"building {c['netadmin_tag']} on the inner daemon")
        docker("build", "--build-arg", f"NS_ALPINE_IMAGE={c['alpine_image']}",
               "-t", c["netadmin_tag"], "/sandbox/netadmin", timeout=900)


def ensure_jail_network() -> None:
    c = jail_cfg()
    if docker("network", "inspect", c["net"], check=False, timeout=60).returncode == 0:
        return
    log(f"creating internal network {c['net']} {c['subnet']}")
    docker("network", "create", "--internal", "--subnet", c["subnet"], c["net"],
           timeout=60)


def prepare_proxy_logs() -> None:
    """Own squid's log directory before the dind daemon invents it.

    squid runs as its own unprivileged user and dies on start with "Cannot open
    /var/log/squid/access.log for writing" unless this bind source exists and is
    writable. Left to itself the daemon creates it root-owned, squid crash-loops,
    and because the proxy is the jail's only route out the visible symptom is
    agents that cannot reach the API at all - with nothing in the orchestrator's
    own log to say why.
    """
    proxy_logs = LOGS / "proxy"
    try:
        if proxy_logs.exists() and not os.access(proxy_logs, os.W_OK):
            shutil.rmtree(proxy_logs)
        proxy_logs.mkdir(parents=True, exist_ok=True)
        os.chmod(proxy_logs, 0o777)      # squid's uid is not ours and not fixed
    except OSError as exc:
        log(f"cannot prepare {proxy_logs} for squid: {exc}", level="ERROR")


def ensure_proxy(restart: bool = False) -> None:
    c = jail_cfg()
    prepare_proxy_logs()
    # status=running matters: a crash-looping squid still answers `docker ps`,
    # so without it a proxy that can never start is mistaken for a healthy one
    # and never rebuilt.
    running = docker("ps", "-q", "--filter", "name=^nightshift-proxy$",
                     "--filter", "status=running",
                     check=False, timeout=60).stdout.strip()
    if running and not restart:
        return
    docker("rm", "-f", "nightshift-proxy", check=False, timeout=120)
    log("starting nightshift-proxy")
    docker("run", "-d", "--name", "nightshift-proxy", "--label", "nightshift=1",
           "--restart", "unless-stopped",
           "--network", c["net"], "--ip", c["proxy_ip"],
           "--cap-drop", "ALL", "--cap-add", "SETUID", "--cap-add", "SETGID",
           "--cap-add", "DAC_OVERRIDE", "--security-opt", "no-new-privileges",
           "--memory", "512m", "--pids-limit", "256",
           "-v", "/proxy/squid.conf:/etc/squid/squid.conf:ro",
           "-v", "/proxy/allowlist.txt:/etc/squid/allowlist.txt:ro",
           "-v", "/data/logs/proxy:/var/log/squid",
           c["squid_image"], timeout=300)
    # Dual-homed: the jail side is internal, this side is the only route out.
    docker("network", "connect", "bridge", "nightshift-proxy", timeout=60)
    docker("restart", "nightshift-proxy", timeout=120)


def apply_firewall() -> str:
    """Run the iptables helper inside DinD's own network namespace."""
    c = jail_cfg()
    proc = docker("run", "--rm", "--network", "host",
                  "--cap-add", "NET_ADMIN", "--cap-add", "NET_RAW",
                  "-v", "/dind-init:/dind-init:ro",
                  c["netadmin_tag"], "/dind-init/firewall.sh",
                  c["subnet"], c["proxy_ip"], c["proxy_port"], timeout=180)
    return proc.stdout.strip()


def ensure_jail(rebuild: bool = False, restart_proxy: bool = False) -> None:
    ensure_images(rebuild)
    ensure_jail_network()
    ensure_proxy(restart_proxy)
    log(apply_firewall().replace("\n", " | "))


def cmd_setup(argv: list[str]) -> int:
    ensure_jail(rebuild="--rebuild" in argv, restart_proxy="--restart-proxy" in argv)
    print("jail ready")
    return 0



# --------------------------------------------------------------- agent contract
# One way to start an agent, used by every role. The jail, the managed deny rules
# and the guard hook are what make --permission-mode bypassPermissions acceptable.
RATE_LIMIT_PATTERNS = [
    re.compile(r"usage limit reached", re.I),
    re.compile(r"\busage limit\b", re.I),
    re.compile(r"\blimit reached\b", re.I),
    re.compile(r"rate[_ ]limit", re.I),
    re.compile(r"\bresets? at\b", re.I),
    re.compile(r"\b429\b"),
    re.compile(r"too many requests", re.I),
]
RESET_PATTERNS = [
    re.compile(r"resets? at\s+([0-9]{1,2}:[0-9]{2}\s*(?:am|pm)?)", re.I),
    re.compile(r"resets? at\s+([0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2})", re.I),
    re.compile(r'"retry-after"\s*:\s*"?(\d+)"?', re.I),
    re.compile(r"retry[- ]after[:= ]\s*(\d+)", re.I),
]


class AgentResult:
    """Everything the loop needs to decide what happens next."""

    def __init__(self, role: str, task_id: str, log_path: Path):
        self.role = role
        self.task_id = task_id
        self.log_path = log_path
        self.exit_code: int = -1
        self.result: dict = {}
        self.stderr: str = ""
        self.timed_out: bool = False
        self.rate_limit_info: dict = {}

    @property
    def is_error(self) -> bool:
        return bool(self.result.get("is_error")) or self.exit_code != 0

    @property
    def text(self) -> str:
        return str(self.result.get("result", ""))

    @property
    def num_turns(self) -> int:
        return int(self.result.get("num_turns", 0))

    @property
    def cost_usd(self) -> float:
        return float(self.result.get("total_cost_usd", 0.0) or 0.0)

    @property
    def permission_denials(self) -> list:
        return self.result.get("permission_denials") or []

    @property
    def rate_limited(self) -> bool:
        if env("NS_FAKE_LIMIT") == "1":
            return True
        # The stream emits rate_limit_event records with a machine-readable status.
        # "allowed_warning" means the window is nearly spent but THIS request went
        # through, so it must not stop the run: treat every allowed* status as fine
        # and back off only when a request was actually refused.
        status = str(self.rate_limit_info.get("status", "")).lower()
        if status.startswith("allowed"):
            return False
        if status:
            return True
        if self.result.get("api_error_status") in (429, "429"):
            return True
        haystack = f"{self.text}\n{self.stderr}\n{self.result.get('subtype', '')}"
        return any(p.search(haystack) for p in RATE_LIMIT_PATTERNS)

    def reset_epoch(self) -> float | None:
        """Unix time to retry at: the reset of the window that actually blocked us.

        Several windows are reported at once (five_hour, seven_day, ...). Taking the
        latest of them is wrong: a five-hour limit that clears in two hours would
        otherwise sleep until the seven-day window rolls over, days later. Prefer
        the event's own resetsAt, then the window named by rateLimitType, and
        otherwise the soonest reset — sleeping too little only costs one retry,
        while sleeping too long costs the whole run.
        """
        info = self.rate_limit_info
        if not info:
            return None
        windows = info.get("unifiedWindows") or {}

        if info.get("resetsAt"):
            return float(info["resetsAt"])

        named = windows.get(str(info.get("rateLimitType", "")))
        if isinstance(named, dict) and named.get("resetsAt"):
            return float(named["resetsAt"])

        candidates = [float(w["resetsAt"]) for w in windows.values()
                      if isinstance(w, dict) and w.get("resetsAt")]
        return min(candidates) if candidates else None

    def utilization(self) -> dict:
        windows = (self.rate_limit_info.get("unifiedWindows") or {})
        return {k: v.get("utilization") for k, v in windows.items()
                if isinstance(v, dict)}

    def reset_hint(self) -> str:
        haystack = f"{self.text}\n{self.stderr}"
        for pattern in RESET_PATTERNS:
            m = pattern.search(haystack)
            if m:
                return m.group(1)
        return ""

    def summary(self) -> str:
        return (f"{self.role}/{self.task_id}: exit={self.exit_code} "
                f"error={self.is_error} turns={self.num_turns} "
                f"cost=${self.cost_usd:.4f}"
                + (" RATE-LIMITED" if self.rate_limited else "")
                + (" TIMEOUT" if self.timed_out else ""))


def read_token() -> str:
    token = Path("/secrets/oauth_token").read_text().strip()
    if not token:
        raise RuntimeError("/secrets/oauth_token is empty")
    return token


def project_env(project: str) -> dict[str, str]:
    """Per-project API credentials, read from /secrets/<project>.env.

    The file is never mounted into an agent. Keys are declared to docker by name
    only (`-e KEY`), with the values supplied through the orchestrator's own
    environment, so they never appear in argv, in `docker inspect`, or in a log.
    """
    if not project:
        return {}
    path = Path("/secrets") / f"{project}.env"
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.isidentifier():
            values[key] = value.strip().strip("\"'")
    return values


def run_agent(role: str, task_id: str, prompt: str, *, model: str,
              work_dir: str, writable: bool, timeout_min: int, max_turns: int,
              protected: str = "", extra_mounts: list[str] | None = None,
              project: str = "") -> AgentResult:
    cfg = load_config()["agent"]
    c = jail_cfg()
    stamp = now().strftime("%Y%m%d-%H%M%S")
    name = f"ns-{role}-{task_id}-{stamp}"
    log_dir = LOGS / task_id
    log_dir.mkdir(parents=True, exist_ok=True)
    out = AgentResult(role, task_id, log_dir / f"{role}-{stamp}.jsonl")

    mount = f"{work_dir}:/work" + ("" if writable else ":ro")
    argv = [
        "docker", "run", "--rm", "--label", "nightshift=1", "--name", name,
        "--network", c["net"],
        "--user", "1000:1000",
        "--read-only",
        # exec is required: virtualenvs put their interpreters and compiled
        # extension modules under /tmp, and Docker mounts tmpfs noexec by
        # default. It costs nothing — /work is an exec-capable bind mount
        # already, so noexec here never blocked a determined agent.
        "--tmpfs", f"/tmp:rw,exec,size={cfg['tmp_size']},mode=1777",
        # Docker mounts a tmpfs root-owned by default, which would leave the agent
        # unable to write its own HOME (uv, npm and git all need it).
        "--tmpfs", f"/home/agent:rw,size={cfg['home_size']},mode=0700,uid=1000,gid=1000",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", str(cfg["pids_limit"]),
        "--memory", str(cfg["memory"]), "--cpus", str(cfg["cpus"]),
        # The token is inherited from the orchestrator's environment (bare -e), so
        # it never appears in argv or in docker inspect output. The proxy settings
        # are passed by value instead: putting them in the CLI's own environment
        # would send the docker client itself through the jail's proxy.
        "-e", "CLAUDE_CODE_OAUTH_TOKEN",
        "-e", f"HTTPS_PROXY={proxy_url()}",
        "-e", f"HTTP_PROXY={proxy_url()}",
        # Without this, a test that starts its own server on localhost sends the
        # request to the proxy, which correctly refuses it.
        "-e", "NO_PROXY=localhost,127.0.0.1,::1",
        "-e", "no_proxy=localhost,127.0.0.1,::1",
        "-e", f"NS_PROTECTED={protected}",
        "-e", f"NS_TASK_ID={task_id}",
        # Project API keys, by name only, same reasoning as the OAuth token above.
        *[arg for key in sorted(project_env(project)) for arg in ("-e", key)],
        "-v", mount,
        "-v", "/data/plan:/plan:ro",
        *[arg for m in (extra_mounts or []) for arg in ("-v", m)],
        c["agent_tag"],
        "timeout", f"{timeout_min}m",
        "claude", "-p", prompt,
        "--model", model,
        "--max-turns", str(max_turns),
        "--output-format", "stream-json", "--verbose",
        "--permission-mode", "bypassPermissions",
    ]

    child_env = dict(os.environ)
    child_env["CLAUDE_CODE_OAUTH_TOKEN"] = read_token()
    child_env.update(project_env(project))

    log(f"run_agent {role} {task_id} model={model} timeout={timeout_min}m "
        f"turns<={max_turns} rw={writable}")
    started = time.time()
    mark_progress(f"{role} {task_id}", force=True)
    with out.log_path.open("w", encoding="utf-8") as sink:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, env=child_env, bufsize=1)
        assert proc.stdout is not None
        for line in proc.stdout:              # tee: every event is kept on disk
            sink.write(line)
            mark_progress()                   # an agent still streaming is not a hang
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "result":
                out.result = event
            elif event.get("type") == "rate_limit_event":
                # Structured and authoritative — far better than reading prose.
                out.rate_limit_info = event.get("rate_limit_info") or {}
        out.stderr = (proc.stderr.read() if proc.stderr else "")[-4000:]
        out.exit_code = proc.wait()

    # GNU timeout reports 124; the wrapper is the outer bound on a stuck agent.
    out.timed_out = out.exit_code == 124
    record_usage(out, time.time() - started, model)
    log(out.summary())
    return out


def record_usage(res: AgentResult, wall_sec: float, model: str) -> None:
    entry = {
        "ts": ts(), "role": res.role, "task": res.task_id, "model": model,
        "exit_code": res.exit_code, "is_error": res.is_error,
        "timed_out": res.timed_out, "rate_limited": res.rate_limited,
        "num_turns": res.num_turns, "cost_usd": round(res.cost_usd, 6),
        "wall_sec": round(wall_sec, 1),
        "usage": res.result.get("usage", {}),
        "rate_limit": res.rate_limit_info,
        "permission_denials": len(res.permission_denials),
        "log": str(res.log_path),
    }
    try:
        USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with USAGE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError as exc:
        log(f"cannot append to usage.jsonl: {exc}", level="WARN")


def extract_json_object(text: str) -> dict | None:
    """Pull the last complete JSON object out of an agent's final message."""
    depth = 0
    start = -1
    best = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start >= 0:
                chunk = text[start:i + 1]
                try:
                    best = json.loads(chunk)
                except json.JSONDecodeError:
                    pass
    return best


def kill_agent_containers() -> int:
    ids = docker("ps", "-q", "--filter", "label=nightshift=1",
                 "--filter", "name=^ns-", check=False, timeout=60).stdout.split()
    for cid in ids:
        docker("kill", cid, check=False, timeout=60)
    return len(ids)


# ----------------------------------------------------------------------- commands
def cmd_selftest() -> int:
    """Phase 1 verification: prove the plumbing works, then report."""
    cfg = load_config()
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    print("\n=== NIGHTSHIFT selftest ===")
    print(f"time: {ts()}  tz={env('TZ', 'unset')}")

    # 1. writable data tree
    try:
        heartbeat()
        check("write /data/state/heartbeat", HEARTBEAT.exists(),
              HEARTBEAT.read_text().strip())
    except OSError as exc:
        check("write /data/state/heartbeat", False, str(exc))

    for sub in ("plan", "plan/backlog", "repos", "work", "state", "logs", "digests",
                "backup"):
        check(f"/data/{sub} exists", (DATA / sub).is_dir())

    # 1b. the queue the dashboard writes into, and the two trees it reads
    for folder in (runs.QUEUE, runs.CONTROL):
        folder.mkdir(parents=True, exist_ok=True)
        check(f"{folder} exists", folder.is_dir())
    check("charters/ writable (a finished run is archived there)",
          runs.ARCHIVE.is_dir() and os.access(runs.ARCHIVE, os.W_OK), str(runs.ARCHIVE))
    repos = runs.available_repos() if runs.SOURCE_ROOT.is_dir() else []
    check(f"{runs.SOURCE_ROOT} readable (charter projects are cloned from it)",
          runs.SOURCE_ROOT.is_dir(),
          f"{len(repos)} repo(s) offered: {', '.join(r['name'] for r in repos[:6])}")
    queued = runs.queue_list()
    active = runs.active_run()
    check("run state readable", True,
          f"active: {('run %s — %s' % (active['run_no'], active['title'])) if active else 'none'}"
          f" · queued: {len(queued)}")

    # 2. inner docker daemon
    try:
        info = docker("info", "--format",
                      "{{.ID}}|{{.ServerVersion}}|{{.OperatingSystem}}|"
                      "{{.Driver}}|{{.DockerRootDir}}", timeout=60).stdout.strip()
        did, ver, os_name, driver, root = info.split("|")
        check("inner docker daemon reachable", True, f"{ver} ({os_name})")
        print(f"         inner daemon ID : {did}")
        print(f"         storage driver  : {driver}  root={root}")
        print(f"         DOCKER_HOST     : {env('DOCKER_HOST')}")
    except (DockerError, ValueError, subprocess.SubprocessError) as exc:
        check("inner docker daemon reachable", False, str(exc))

    # 3. the inner daemon must NOT be the host daemon
    try:
        containers = docker("ps", "-a", "--format", "{{.Names}}", timeout=60).stdout.split()
        check("inner daemon is isolated from the host", True,
              f"{len(containers)} container(s) inside: {containers or 'none'}")
    except DockerError as exc:
        check("inner daemon is isolated from the host", False, str(exc))

    # 4. no secrets leaked into /data
    leaked = [str(p) for p in DATA.rglob("oauth_token")]
    check("no oauth_token under /data", not leaked, ", ".join(leaked))
    check("/secrets mounted read-only", not os.access("/secrets", os.W_OK))

    # 5. disk headroom
    free = disk_free_gb()
    check(f"free space > {cfg['disk']['pause_free_gb']} GB (pause threshold)",
          free > cfg["disk"]["pause_free_gb"],
          f"{free:.1f} GB free, {disk_used_pct():.0f}% used")

    # 6. notifications
    topic = env("NTFY_TOPIC")
    check("NTFY_TOPIC set", bool(topic), topic)
    check("CMD_SECRET set", bool(env("CMD_SECRET")))
    if topic:
        check("ntfy push accepted", ntfy(
            f"Checkpoint 1 selftest at {ts()}.\n"
            f"Inner Docker daemon reachable, /data writable, {free:.1f} GB free.\n"
            f"Reply with commands on {topic}-cmd (prefix: {env('CMD_SECRET')}: status).",
            title="NIGHTSHIFT: hello from the orchestrator",
            priority="default", tags="rocket"))

    # 7. dead-man's switch
    if env("HC_PING_URL"):
        check("healthchecks.io ping accepted", hc_ping(body=f"selftest {ts()}"))
    else:
        check("HC_PING_URL set", False, "paste the ping URL into ~/nightshift/.env")

    print(f"\n{'ALL CHECKS PASSED' if not failures else 'FAILED: ' + ', '.join(failures)}\n")
    return 0 if not failures else 1


# ------------------------------------------------------------------ repos/work
def repo_path(project: str) -> Path:
    return DATA / "repos" / f"{project}.git"


def prepare_worktree(task: dict) -> Path:
    """Fresh clone of the bare repo on a branch of its own. Never reused."""
    work = DATA / "work" / task["id"]
    if work.exists():
        shutil.rmtree(work)
    work.parent.mkdir(parents=True, exist_ok=True)
    bare = repo_path(task["project"])
    if not bare.exists():
        raise RuntimeError(f"no bare repo at {bare}")
    gates.git(DATA / "work", "clone", "--branch", INTEGRATION, str(bare), str(work))
    gates.git(work, "checkout", "-b", f"agent/{task['id']}")
    gates.git(work, "config", "user.name", "NIGHTSHIFT worker")
    gates.git(work, "config", "user.email", "nightshift@localhost")

    # Local-only excludes: the orchestrator's own bookkeeping directory and the
    # build artifacts that running the tests produces are not the agent's doing,
    # and must not make the "clean working tree" gate fail. info/exclude never
    # becomes part of the repository or the diff.
    (work / ".git" / "info").mkdir(parents=True, exist_ok=True)
    (work / ".git" / "info" / "exclude").write_text(
        "\n".join([".nightshift/", "__pycache__/", "*.py[cod]", ".pytest_cache/",
                    ".ruff_cache/", ".mypy_cache/", ".venv/", "venv/", "node_modules/",
                    ".coverage", "htmlcov/", "*.egg-info/", "dist/", "build/", ""]),
        encoding="utf-8")

    notes = "\n".join(f"- {n}" for n in task.get("notes", [])) or "- (first attempt)"
    meta = work / ".nightshift"
    meta.mkdir(exist_ok=True)
    (meta / "TASK.md").write_text(
        f"# {task['id']}: {task['title']}\n\n"
        f"**Charter goal:** {task['charter_goal']}  \n"
        f"**Milestone:** {task['roadmap_ref']}  \n"
        f"**Why:** {task['why']}\n\n"
        f"## Acceptance (all must exit 0)\n"
        + "".join(f"- `{c}`\n" for c in task["acceptance"])
        + f"\n## Paths you may touch\n"
        + "".join(f"- `{p}`\n" for p in task["allowed_paths"])
        + f"\n## Paths you must not touch\n"
        + "".join(f"- `{p}`\n" for p in task["protected_paths"])
        + f"\n## Limits\n- diff at most {task['max_diff_lines']} lines\n"
        f"- new tests required: {task.get('new_tests_required', True)}\n"
        f"- attempt {task.get('attempts', 0) + 1} of 2\n"
        f"\n## Notes from earlier attempts\n{notes}\n", encoding="utf-8")
    return work


def sandbox_exec(task_id: str, work: Path, command: str, timeout_min: int,
                 project: str = "") -> tuple[int, str]:
    """Run one acceptance/lint command in a jailed container, on a copy of the branch."""
    c = jail_cfg()
    cfg = load_config()["agent"]
    argv = [
        "docker", "run", "--rm", "--label", "nightshift=1",
        "--network", c["net"], "--user", "1000:1000", "--read-only",
        # exec is required: virtualenvs put their interpreters and compiled
        # extension modules under /tmp, and Docker mounts tmpfs noexec by
        # default. It costs nothing — /work is an exec-capable bind mount
        # already, so noexec here never blocked a determined agent.
        "--tmpfs", f"/tmp:rw,exec,size={cfg['tmp_size']},mode=1777",
        "--tmpfs", f"/home/agent:rw,size={cfg['home_size']},mode=0700,uid=1000,gid=1000",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", str(cfg["pids_limit"]),
        "--memory", str(cfg["memory"]), "--cpus", str(cfg["cpus"]),
        "-e", f"HTTPS_PROXY={proxy_url()}", "-e", f"HTTP_PROXY={proxy_url()}",
        "-e", "NO_PROXY=localhost,127.0.0.1,::1",
        "-e", "no_proxy=localhost,127.0.0.1,::1",
        # Acceptance commands need the same credentials the worker had, or a test
        # that exercises a live API passes for the worker and fails in the gate.
        *[arg for key in sorted(project_env(project)) for arg in ("-e", key)],
        "-v", f"{work}:/src:ro",
        c["agent_tag"],
        "timeout", f"{timeout_min}m",
        # git clone, not cp -a: copying the worktree drags in the worker's .venv,
        # and a virtualenv is not relocatable — pytest then fails to spawn and every
        # task parks on a gate failure that has nothing to do with its code. Cloning
        # also means the gate tests exactly the committed state that would merge.
        # Clone copies refs/heads/* only, so the gate's copy has the task branch
        # and agent/integration but none of the remote-tracking refs the worker saw.
        # Carrying refs/remotes/origin/* across keeps the two environments honest: an
        # acceptance command that resolves something against origin/main used to pass
        # in the worker's tree and fail here, which reads as a code failure and is not.
        "bash", "-lc",
        "git clone -q --no-hardlinks /src /tmp/w && "
        "git -C /tmp/w fetch -q --no-tags /src "
        "'+refs/remotes/origin/*:refs/remotes/origin/*' && "
        f"cd /tmp/w && {command}",
    ]
    child_env = dict(os.environ)
    child_env.update(project_env(project))
    proc = subprocess.run(argv, capture_output=True, text=True, env=child_env,
                          timeout=timeout_min * 60 + 120)
    return proc.returncode, (proc.stdout + proc.stderr)


def merge_task(task: dict, work: Path) -> str:
    """Merge the task branch into agent/integration inside the bare repo."""
    branch = f"agent/{task['id']}"
    gates.git(work, "push", "origin", branch)
    gates.git(work, "checkout", INTEGRATION)
    gates.git(work, "merge", "--no-ff", branch, "-m",
              f"{task['id']}: {task['title']}")
    gates.git(work, "push", "origin", INTEGRATION)
    return gates.git(work, "rev-parse", "--short", "HEAD").strip()


# -------------------------------------------------------------------- prompts
def prompt_for(role: str, **fields: str) -> str:
    common = (APP / "prompts" / "common.md").read_text(encoding="utf-8").strip()
    text = (APP / "prompts" / f"{role}.md").read_text(encoding="utf-8")
    return text.replace("{common}", common).format(common=common, **fields) \
        if fields else text.replace("{common}", common)


def agent_json(role: str, task_id: str, prompt: str, model: str, *,
               work_dir: str, timeout_min: int, max_turns: int,
               validator, extra_mounts: list[str] | None = None) -> tuple[dict | None, AgentResult]:
    """Run a JSON-returning role. One retry, then it counts as a failure."""
    last = None
    for attempt in (1, 2):
        res = run_agent(role, task_id, prompt, model=model, work_dir=work_dir,
                        writable=False, timeout_min=timeout_min, max_turns=max_turns,
                        extra_mounts=extra_mounts)
        last = res
        if res.rate_limited:
            return None, res
        payload = extract_json_object(res.text)
        if payload is None:
            log(f"{role} returned no JSON object (attempt {attempt})", level="WARN")
            continue
        try:
            return validator(payload), res
        except plan.PlanError as exc:
            log(f"{role} JSON rejected (attempt {attempt}): {exc}", level="WARN")
    return None, last


# ------------------------------------------------------------------- governor
class Governor:
    """Greedy by design: work until a limit hits, sleep exactly as long as needed."""

    def __init__(self, cfg: dict):
        self.cfg = cfg["governor"]
        self.limit_backoff = 0
        self.error_backoff = 0

    def wait_if_limited(self, state: dict) -> None:
        until = state.get("limit_until")
        if not until:
            return
        remaining = float(until) - time.time()
        while remaining > 0:
            log(f"quota limit: sleeping {remaining / 60:.0f} min")
            mark_progress("quota limit", force=True)
            time.sleep(min(remaining, 300))
            remaining = float(until) - time.time()
        state["limit_until"] = None
        state_save(state)

    def on_limit(self, state: dict, res: AgentResult) -> None:
        reset = res.reset_epoch()
        if reset and reset > time.time():
            until = reset + 120           # a small cushion past the reset
            source = "stream rate_limit_event"
        else:
            mins = self.cfg["limit_backoff_min"][
                min(self.limit_backoff, len(self.cfg["limit_backoff_min"]) - 1)]
            self.limit_backoff += 1
            until = time.time() + mins * 60
            source = f"backoff {mins} min (no reset time in the transcript)"
        state["limit_until"] = until
        state_save(state)
        hours = (until - time.time()) / 3600
        log(f"rate limited; sleeping until {datetime.fromtimestamp(until).isoformat()} "
            f"[{source}]")
        if hours >= self.cfg["weekly_cap_notify_hours"]:
            ntfy(f"Usage limit reached and the reset is {hours:.0f} h away "
                 f"({datetime.fromtimestamp(until).strftime('%a %H:%M')}). Sleeping until then.",
                 title="NIGHTSHIFT: long quota sleep", priority="high", tags="hourglass")

    def on_error(self, state: dict) -> None:
        streak = state.get("other_error_streak", 0) + 1
        state["other_error_streak"] = streak
        mins = self.cfg["other_error_backoff_min"][
            min(streak - 1, len(self.cfg["other_error_backoff_min"]) - 1)]
        state_save(state)
        log(f"error streak {streak}; backing off {mins} min", level="WARN")
        time.sleep(mins * 60)

    def on_success(self, state: dict) -> None:
        self.limit_backoff = 0
        state["other_error_streak"] = 0


# ------------------------------------------------------------ phone commands
def ntfy_poll_commands(state: dict) -> list[str]:
    """Read the -cmd topic. Only messages carrying CMD_SECRET are obeyed."""
    topic, secret = env("NTFY_TOPIC"), env("CMD_SECRET")
    if not topic or not secret:
        return []
    since = state.get("last_ntfy_cmd_id") or "5m"
    url = (f"{env('NTFY_SERVER', 'https://ntfy.sh').rstrip('/')}/{topic}-cmd/json"
           f"?poll=1&since={urllib.parse.quote(str(since))}")
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError) as exc:
        log(f"ntfy command poll failed: {exc}", level="WARN")
        return []

    commands = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("event") != "message":
            continue
        state["last_ntfy_cmd_id"] = msg.get("id", state.get("last_ntfy_cmd_id"))
        commands.extend(parse_command(msg.get("message", ""), secret))
    state_save(state)
    return commands


def parse_command(message: str, secret: str) -> list[str]:
    """`<secret>: pause` -> ['pause']. Anything unsigned is ignored, not guessed at."""
    text = message.strip()
    if not text.startswith(secret):
        return []
    rest = text[len(secret):].lstrip(": ").strip().lower()
    return [rest] if rest in runs.COMMANDS else []


def handle_command(cmd: str, state: dict) -> None:
    log(f"phone command: {cmd}")
    if cmd == "pause":
        state.update(paused=True, pause_reason="paused from phone")
        ntfy("Paused. Send resume when you want it going again.", title="NIGHTSHIFT: paused")
    elif cmd == "resume":
        state.update(paused=False, pause_reason="", consecutive_failures=0)
        STOP_FILE.unlink(missing_ok=True)
        ntfy("Resumed.", title="NIGHTSHIFT: resumed")
    elif cmd == "stop":
        STOP_FILE.write_text(ts() + "\n")
        killed = kill_agent_containers()
        state.update(paused=True, pause_reason="stopped from phone")
        ntfy(f"Stopped. Killed {killed} running agent container(s). "
             f"Delete /data/STOP and send resume to restart.",
             title="NIGHTSHIFT: stopped", priority="high", tags="octagonal_sign")
    elif cmd == "status":
        ntfy(status_text(state), title="NIGHTSHIFT: status")
    elif cmd == "digest":
        run_auditor(state, forced=True)
    elif cmd == "finish":
        # Not acted on here: the loop archives between tasks, never under an agent.
        state["finish_requested"] = True
        ntfy("This run will be archived and the next queued charter armed as soon as "
             "the task in flight finishes.", title="NIGHTSHIFT: finishing run")
    elif cmd == "plan-now":
        state["planner_due"] = True
        ntfy("The planner will run on the next loop iteration.",
             title="NIGHTSHIFT: planner queued")
    state_save(state)


def status_text(state: dict) -> str:
    try:
        ready = len(plan.load_tasks())
    except plan.PlanError as exc:
        ready = f"unreadable ({exc})"
    today = now().strftime("%Y-%m-%d")
    merges_today = sum(1 for e in read_usage() if e.get("ts", "").startswith(today)
                       and e.get("role") == "merge")
    limit = state.get("limit_until")
    run = runs.active_run() or {}
    queued = len(runs.queue_list())
    return (f"run: {('%s — %s' % (run.get('run_no'), run.get('title'))) if run else 'none armed'}\n"
            f"queued charters: {queued}\n"
            f"task: {state.get('current_task') or 'idle'}\n"
            f"queue: {ready} ready\n"
            f"merges today: {merges_today} (total {state.get('merges_total', 0)})\n"
            f"parked in a row: {state.get('consecutive_failures', 0)}\n"
            f"paused: {state.get('paused')} {state.get('pause_reason', '')}\n"
            f"limit until: {datetime.fromtimestamp(limit).strftime('%a %H:%M') if limit else 'none'}\n"
            f"disk free: {disk_free_gb():.1f} GB\n"
            f"deadline: {run_deadline_text(state)}")


def run_deadline_text(state: dict) -> str:
    cfg = load_config()
    hours = run_hours(state, cfg)
    armed_at = state.get("armed_at")
    if not hours or not armed_at:
        return "none"
    ends = datetime.fromisoformat(armed_at).timestamp() + hours * 3600
    left = (ends - time.time()) / 3600
    return (f"{datetime.fromtimestamp(ends).strftime('%a %H:%M')} "
            f"({left:.1f} h left)" if left > 0 else "passed")


def read_usage(limit: int = 2000) -> list[dict]:
    if not USAGE_LOG.exists():
        return []
    lines = USAGE_LOG.read_text(encoding="utf-8").splitlines()[-limit:]
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def readonly_checkouts() -> list[str]:
    """Fresh read-only checkouts of every project, for the roles that only look.

    The planner was writing tasks against file names it could not verify and said
    so in its own ADR; the auditor made the same complaint. Both now see the code
    they are judging, mounted read-only at /repo/<project>.
    """
    mounts = []
    for project in plan.charter_projects():
        bare = repo_path(project)
        if not bare.exists():
            continue
        checkout = DATA / "work" / "_readonly" / project
        try:
            if checkout.exists():
                gates.git(checkout, "fetch", "origin", INTEGRATION, timeout=120)
                gates.git(checkout, "reset", "--hard", "FETCH_HEAD", timeout=120)
            else:
                checkout.parent.mkdir(parents=True, exist_ok=True)
                gates.git(DATA / "work", "clone", "--branch", INTEGRATION,
                          str(bare), str(checkout), timeout=300)
            mounts.append(f"{checkout}:/repo/{project}:ro")
        except RuntimeError as exc:
            log(f"cannot prepare read-only checkout of {project}: {exc}", level="WARN")
    return mounts


# ------------------------------------------------------------------- planner
def planner_due(state: dict) -> bool:
    cfg = load_config()["planner"]
    if state.get("planner_due"):
        return True
    if state.get("merges_since_planner", 0) >= cfg["merges_between_runs"]:
        return True
    last = state.get("last_planner_run")
    today_at = now().replace(hour=cfg["daily_at_hour"], minute=0, second=0, microsecond=0)
    return now() >= today_at and (not last or last < today_at.isoformat())


def planner_idle_ok(state: dict) -> bool:
    """Whether an empty backlog on its own justifies another planner run.

    An empty backlog is a reason to plan, but not a reason to plan on a hot loop.
    When the charter's goals are all met the planner correctly returns no ops, the
    backlog is still empty on the next iteration, and without a floor between runs
    the loop asks an Opus planner again as fast as it can answer - which is what it
    did for most of 2026-09-23 and 09-24, for $48 and no tasks.
    """
    gap = load_config()["planner"].get("idle_retry_min", 30)
    last = state.get("last_planner_run")
    if not last:
        return True
    return (now() - datetime.fromisoformat(last)).total_seconds() >= gap * 60


def run_planner(state: dict, gov: "Governor | None" = None) -> bool:
    """True only when the planner actually added work, which is what the caller
    needs to know: a run that applied nothing leaves the backlog exactly as it was.
    """
    goals = plan.charter_goals()
    tasks = {t["id"]: t for t in plan.load_tasks()}
    parked = plan.load_tasks(plan.PARKED)
    done = plan.load_tasks(plan.DONE)[-15:]
    followups = [f for e in read_usage()[-80:] for f in e.get("followups", [])]

    context = (
        f"# CHARTER\n{plan.charter_text()}\n\n"
        f"# ROADMAP\n{plan.ROADMAP.read_text(encoding='utf-8')}\n\n"
        f"# BACKLOG ({len(tasks)} ready)\n"
        + "\n".join(f"- {t['id']} [{t['charter_goal']}/{t['roadmap_ref']}] {t['title']}"
                     for t in tasks.values())
        + f"\n\n# PARKED\n"
        + "\n".join(f"- {t['id']} {t['title']} — {t.get('park_reason', 'no reason recorded')}"
                     for t in parked)
        + f"\n\n# RECENTLY DONE\n"
        + "\n".join(f"- {t['id']} {t['title']}" for t in done)
        + f"\n\n# WORKER FOLLOWUPS\n" + "\n".join(f"- {f}" for f in followups[-40:])
    )
    prompt = prompt_for("planner") + "\n\n" + context

    payload, res = agent_json(
        "planner", "planner", prompt, load_config()["models"]["planner"],
        work_dir="/data/plan", timeout_min=20, max_turns=30,
        validator=lambda p: (plan.validate_adr(p), p)[1],
        extra_mounts=readonly_checkouts())
    if payload is None:
        # A refused request is not a planner that had nothing to say. Without this
        # the governor never learns the quota is spent, and the loop retries the
        # planner once a minute for the whole length of the window.
        if gov is not None and res is not None and res.rate_limited:
            gov.on_limit(state, res)
            return False
        log("planner produced nothing usable", level="WARN")
        return False

    accepted = plan.validate_planner_output(payload, goals=goals, existing=tasks)
    applied = apply_planner_ops(accepted, tasks)
    plan.write_adr(payload["adr"], now().strftime("%Y%m%d-%H%M%S"))

    rejected = payload.get("_rejected", [])
    state["last_planner_run"] = ts()
    state["merges_since_planner"] = 0
    state["planner_due"] = False
    state_save(state)
    # A planner run that validated and applied nothing is the charter saying it
    # is finished. Counted only here, where a refusal or unusable JSON - which
    # returned earlier - can never be mistaken for "no work left".
    state["idle_planner_streak"] = 0 if applied else state.get("idle_planner_streak", 0) + 1
    state_save(state)
    log(f"planner applied {applied} op(s), rejected {len(rejected)}")
    if rejected:
        log("planner ops rejected: " + "; ".join(rejected[:5]), level="WARN")
    return applied > 0


def apply_planner_ops(ops: list[dict], tasks: dict[str, dict]) -> int:
    applied = 0
    for op in ops:
        kind = op["op"]
        # `tasks` is written back as each op is applied. The validator already
        # accepts a batch that adds T-0071 and then updates it, so an apply that
        # only ever read the on-disk snapshot raised KeyError on the update and
        # lost the whole batch; two updates to one task also silently dropped the
        # first one's fields.
        if kind == "add_task":
            task = dict(op["task"])
            task["created"] = ts()
            plan.save_task(task, "ready")
            tasks[task["id"]] = task
        elif kind == "update_task":
            merged = {**tasks[op["id"]], **op["fields"]}
            plan.save_task(merged)
            tasks[op["id"]] = merged
        elif kind == "park_task":
            task = dict(tasks[op["id"]])
            task["park_reason"] = op["reason"]
            plan.save_task(task, "parked")
        elif kind == "add_milestone":
            with plan.ROADMAP.open("a", encoding="utf-8") as fh:
                fh.write(f"\n{op['id']} [{op['charter_goal']}] {op['title']} — planned — "
                         f"{op['exit_criteria']}\n")
        elif kind == "reorder":
            for rank, tid in enumerate(op["ids"]):
                if tid in tasks:
                    plan.save_task({**tasks[tid], "rank": rank})
        applied += 1
    return applied


# ------------------------------------------------------------------- auditor
def merge_diff(entry: dict, max_chars: int = 25000) -> str:
    """The actual code a merge introduced, read straight from the bare repo.

    The auditor judges drift from the diff rather than from task metadata: a task
    can claim anything in its title, and only the code says what really landed.
    """
    project, sha = entry.get("project"), entry.get("sha")
    if not project or not sha:
        return ""
    bare = repo_path(project)
    if not bare.exists():
        return ""
    try:
        stat = gates.git(bare, "--git-dir", str(bare), "show", "--stat", "--oneline",
                         "-s", sha, timeout=60)
        patch = gates.git(bare, "--git-dir", str(bare), "diff", f"{sha}^1", sha,
                          timeout=60)
    except RuntimeError as exc:
        return f"(diff unavailable: {exc})"
    body = patch[:max_chars]
    if len(patch) > max_chars:
        body += f"\n... [{len(patch) - max_chars} more characters truncated]"
    return f"{stat}\n{body}"


def run_auditor(state: dict, forced: bool = False, gov: "Governor | None" = None) -> None:
    cfg = load_config()["auditor"]
    usage = read_usage()
    cutoff = (now().timestamp() - 24 * 3600)
    recent = [e for e in usage
              if datetime.fromisoformat(e["ts"]).timestamp() > cutoff]
    merges = [e for e in recent if e.get("role") == "merge"]
    spend = sum(e.get("cost_usd", 0) for e in recent)
    denials = sum(e.get("permission_denials", 0) for e in recent)

    context = (
        f"# CHARTER\n{plan.charter_text()}\n\n"
        f"# ROADMAP\n{plan.ROADMAP.read_text(encoding='utf-8')}\n\n"
        f"# LAST 24 HOURS\n"
        f"- agent runs: {len(recent)}\n- merges: {len(merges)}\n"
        f"- estimated spend: ${spend:.2f}\n- sandbox denials: {denials}\n"
        + "\n".join(f"- merged {e.get('task')} [{e.get('charter_goal', '?')}]: "
                     f"{e.get('title', '')} ({e.get('diff_lines', '?')} diff lines)"
                     for e in merges)
        + "\n\n# WHAT ACTUALLY LANDED (read from the repositories)\n"
        + "\n\n".join(f"## {e.get('task')} — {e.get('title', '')}\n"
                        f"```diff\n{merge_diff(e)}\n```" for e in merges[-8:])
        + f"\n\n# PARKED\n"
        + "\n".join(f"- {t['id']} {t['title']} — {t.get('park_reason', '')}"
                     for t in plan.load_tasks(plan.PARKED))
    )

    def validate(payload: dict) -> dict:
        score = payload.get("drift_score")
        if not isinstance(score, (int, float)) or not 0 <= score <= 10:
            raise plan.PlanError("drift_score must be a number between 0 and 10")
        if not str(payload.get("digest", "")).strip():
            raise plan.PlanError("auditor must produce a digest")
        return payload

    payload, res = agent_json("auditor", "auditor", prompt_for("auditor") + "\n\n" + context,
                              load_config()["models"]["auditor"], work_dir="/data/plan",
                              timeout_min=15, max_turns=20, validator=validate,
                              extra_mounts=readonly_checkouts())
    if payload is None:
        # As in run_planner: a refused request must reach the governor, or the
        # daily audit retries on every loop iteration until the window resets.
        if gov is not None and res is not None and res.rate_limited:
            gov.on_limit(state, res)
            return
        ntfy("The auditor did not return a usable digest today.",
             title="NIGHTSHIFT: digest failed", priority="low")
        return

    stamp = now().strftime("%Y%m%d")
    (DATA / "digests" / f"{stamp}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    score = payload["drift_score"]
    ntfy(f"{payload['digest']}\n\n"
         f"— drift {score}/10 · {len(merges)} merges · ${spend:.2f} · {denials} sandbox denials",
         title=f"NIGHTSHIFT digest {stamp}",
         tags="chart_with_upwards_trend" if score < cfg["pause_at_drift"] else "warning")
    state["last_auditor_run"] = ts()
    if score >= cfg["pause_at_drift"] and not forced:
        state.update(paused=True, pause_reason=f"auditor drift score {score}")
        ntfy(f"Paused: the auditor scored drift {score}/10.\n"
             + "\n".join(payload.get("findings", [])[:5]),
             title="NIGHTSHIFT: drift pause", priority="urgent", tags="rotating_light")
    state_save(state)


# -------------------------------------------------------------- housekeeping
def housekeeping(state: dict) -> None:
    cfg = load_config()["housekeeping"]
    log("daily housekeeping")
    docker("container", "prune", "-f", "--filter", "label=nightshift=1",
           check=False, timeout=300)

    cutoff = time.time() - cfg["worktree_max_age_days"] * 86400
    for path in (DATA / "work").glob("*"):
        if path.is_dir() and path.stat().st_mtime < cutoff:
            shutil.rmtree(path, ignore_errors=True)
            log(f"removed stale worktree {path.name}")

    total = sum(f.stat().st_size for f in LOGS.rglob("*") if f.is_file())
    cap = cfg["log_cap_gb"] * 1024 ** 3
    if total > cap:
        files = sorted((f for f in LOGS.rglob("*") if f.is_file()),
                       key=lambda f: f.stat().st_mtime)
        while total > cap * 0.8 and files:
            victim = files.pop(0)
            total -= victim.stat().st_size
            victim.unlink(missing_ok=True)
        log(f"log rotation done, now {total / 1024 ** 3:.1f} GB")

    stamp = now().strftime("%Y%m%d")
    archive = DATA / "backup" / f"plan-repos-{stamp}.tar.gz"
    if not archive.exists():
        subprocess.run(["tar", "-czf", str(archive), "-C", str(DATA), "plan", "repos"],
                       capture_output=True, timeout=1800)
    keep = time.time() - cfg["backup_keep_days"] * 86400
    for old in (DATA / "backup").glob("plan-repos-*.tar.gz"):
        if old.stat().st_mtime < keep:
            old.unlink(missing_ok=True)

    free = disk_free_gb()
    if free < load_config()["disk"]["alert_free_gb"]:
        ntfy(f"Only {free:.1f} GB free on the filesystem holding /data.",
             title="NIGHTSHIFT: disk filling up", priority="high", tags="warning")
    state["last_housekeeping"] = ts()
    state_save(state)


# ---------------------------------------------------------------- task picking
def next_ready_task(state: dict) -> dict | None:
    tasks = plan.load_tasks()
    if not tasks:
        return None
    goals = plan.charter_goals()
    done_ids = {t["id"] for t in plan.load_tasks(plan.DONE)}

    def sort_key(task: dict) -> tuple:
        goal_rank = goals.index(task["charter_goal"]) if task["charter_goal"] in goals else 99
        return (goal_rank, task.get("rank", 50), task["roadmap_ref"], task["id"])

    for task in sorted(tasks, key=sort_key):
        if task["status"] != "ready":
            continue
        if any(dep not in done_ids for dep in task.get("depends_on", [])):
            continue
        if task.get("attempts", 0) >= 2:
            continue
        return task
    return None


def save_gate_run(task: dict, gate: gates.GateResult) -> Path:
    """Keep the whole gate run next to the agent transcripts.

    The verdict used to survive only as a log line and a task note, both of which
    keep the command that failed and drop what it printed, so a gate failure could
    not be read back afterwards without re-running the command by hand.
    """
    path = LOGS / task["id"] / f"gates-{now().strftime('%Y%m%d-%H%M%S')}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"ts": ts(), "task": task["id"],
                                "attempt": task.get("attempts", 0) + 1,
                                "ok": gate.ok, "failures": gate.failures,
                                "details": gate.details}, indent=2), encoding="utf-8")
    return path


# ----------------------------------------------------------------- one task
def work_one_task(task: dict, state: dict, gov: Governor) -> str:
    """Returns 'merged', 'retry', 'parked', 'limited' or 'error'."""
    tid = task["id"]
    state["current_task"] = tid
    state_save(state)
    work = prepare_worktree(task)
    protected = ":".join(task["protected_paths"])

    res = run_agent("worker", tid, prompt_for("worker").replace("{task_id}", tid),
                    model=load_config()["models"]["worker"],
                    work_dir=str(work), writable=True,
                    timeout_min=task["timeout_min"], max_turns=task["max_turns"],
                    protected=protected, project=task["project"])
    if res.rate_limited:
        gov.on_limit(state, res)
        return "limited"

    worker_json = extract_json_object(res.text) or {}
    gate = gates.run_gates(
        task, work, INTEGRATION, worker_json,
        lambda tid_, work_, cmd_, timeout_min: sandbox_exec(
            tid_, work_, cmd_, timeout_min, project=task["project"]))
    gate_log = save_gate_run(task, gate)
    log(f"{tid} {gate.report()}")
    if not gate.ok:
        log(f"{tid} gate output (full copy in {gate_log.name}):\n"
            f"{gate.failing_output(800)}")

    review = None
    if gate.ok:
        diff = gates.git(work, "diff", f"{INTEGRATION}...HEAD")[:120000]
        context = (f"# CHARTER\n{plan.charter_text()}\n\n"
                   f"# TASK\n{json.dumps(task, indent=2)}\n\n"
                   f"# GATES\n{gate.report()}\n{json.dumps(gate.details, indent=2)[:4000]}\n\n"
                   f"# WORKER SAID\n{json.dumps(worker_json, indent=2)}\n\n"
                   f"# DIFF\n```diff\n{diff}\n```")
        review, rres = agent_json("reviewer", tid, prompt_for("reviewer") + "\n\n" + context,
                                  load_config()["models"]["reviewer"],
                                  work_dir=str(work), timeout_min=20, max_turns=25,
                                  validator=plan.validate_reviewer_output)
        if rres is not None and rres.rate_limited:
            gov.on_limit(state, rres)
            return "limited"

    if gate.ok and review and plan.review_passes(review):
        sha = merge_task(task, work)
        plan.save_task({**task, "merged_sha": sha, "merged_at": ts()}, "done")
        state["merges_total"] = state.get("merges_total", 0) + 1
        state["merges_since_planner"] = state.get("merges_since_planner", 0) + 1
        state["consecutive_failures"] = 0
        with USAGE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": ts(), "role": "merge", "task": tid,
                                 "title": task["title"], "sha": sha,
                                 "project": task["project"],
                                 "charter_goal": task["charter_goal"],
                                 "diff_lines": gate.details.get("diff_lines"),
                                 "cost_usd": 0}) + "\n")
        ntfy(f"{tid} {task['title']}\n{gate.details.get('diff_lines', '?')} diff lines, "
             f"merged as {sha}\n{worker_json.get('summary', '')[:300]}",
             title="NIGHTSHIFT: merged", tags="white_check_mark")
        state_save(state)
        return "merged"

    # not merged: record why, so the next attempt starts better informed
    reason = gate.report() if not gate.ok else (
        f"reviewer said {review['verdict']}: {review['notes']}" if review
        else "reviewer produced no usable JSON")
    task = dict(task)
    task["attempts"] = task.get("attempts", 0) + 1
    task.setdefault("notes", []).append(
        f"attempt {task['attempts']}: {clip(reason, 4000)}")
    output = gate.failing_output()
    if output:
        task["notes"].append(
            f"attempt {task['attempts']} gate output:\n{clip(output, 4000)}")

    if task["attempts"] >= 2:
        # Only a terminal outcome counts against the streak. A retry is the loop
        # working as designed - the second attempt starts from the reviewer's notes
        # and usually merges - so counting it as well let one unmergeable task eat
        # two thirds of the budget and pause a run that was making progress.
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        task["park_reason"] = clip(reason, 1500)
        plan.save_task(task, "parked")
        state["planner_due"] = True
        ntfy(f"{tid} {task['title']} parked after 2 attempts.\n{clip(reason, 400)}",
             title="NIGHTSHIFT: parked", priority="high", tags="warning")
        state_save(state)
        return "parked"

    plan.save_task(task, "ready")
    state_save(state)
    return "retry"


# ----------------------------------------------------------- command listener
def start_command_listener() -> None:
    """Poll the -cmd topic on its own thread.

    In the main loop a single task can occupy 45 minutes, and a kill switch that
    only answers between tasks is not a kill switch. On its own thread, `stop`
    kills the running agent container immediately; the main loop then finds the
    STOP file and idles.
    """
    def loop() -> None:
        tick = 0
        while True:
            try:
                # The web UI writes a file per command rather than touching
                # state.json. Polled often: a stop button that answers in half a
                # minute is not a button. State is re-read per command, because an
                # ntfy poll can take fifteen seconds and the loop arms, merges and
                # pauses inside that window.
                for entry in runs.control_pop():
                    log(f"web command: {entry['cmd']}")
                    handle_command(entry["cmd"], state_load())
                if tick % 10 == 0:
                    state = state_load()
                    for cmd in ntfy_poll_commands(state):
                        handle_command(cmd, state_load())
            except Exception as exc:  # noqa: BLE001 - never let this thread die
                log(f"command listener error: {type(exc).__name__}: {exc}", level="WARN")
            tick += 1
            time.sleep(3)

    threading.Thread(target=loop, daemon=True, name="commands").start()


# ------------------------------------------------------------------ watchdog
def start_watchdog() -> None:
    cfg = load_config()["loop"]

    def loop() -> None:
        while True:
            time.sleep(60)
            stalled = (time.time() - _PROGRESS["at"]) / 60
            if stalled > cfg["heartbeat_stale_min"]:
                log(f"watchdog: no progress for {stalled:.0f} min; restarting",
                    level="ERROR")
                ntfy(f"No loop progress for {stalled:.0f} min at step "
                     f"'{_PROGRESS.get('step')}'. Killing agents and restarting.",
                     title="NIGHTSHIFT: watchdog restart", priority="high", tags="warning")
                try:
                    kill_agent_containers()
                except Exception:  # noqa: BLE001 - we are on our way out anyway
                    pass
                os._exit(1)      # Docker's restart policy brings us back

    threading.Thread(target=loop, daemon=True, name="watchdog").start()


# ------------------------------------------------------------------ main loop
def cmd_run() -> int:
    cfg = load_config()
    log(f"orchestrator starting (tz={env('TZ', 'unset')})")
    start_watchdog()
    start_command_listener()

    try:
        ensure_jail()
    except (DockerError, subprocess.SubprocessError) as exc:
        log(f"jail setup failed: {exc}", level="ERROR")
        ntfy(f"Could not set up the sandbox: {exc}", title="NIGHTSHIFT: startup failed",
             priority="urgent")

    state = state_load()
    gov = Governor(cfg)
    idle_logged = 0.0

    while True:
        try:
            mark_progress("heartbeat", force=True)
            state = state_load()

            free = disk_free_gb()
            if free < cfg["disk"]["pause_free_gb"] and not state.get("paused"):
                state.update(paused=True, pause_reason=f"only {free:.1f} GB free")
                state_save(state)
                ntfy(f"Paused: only {free:.1f} GB free on /data.",
                     title="NIGHTSHIFT: disk pressure", priority="urgent", tags="warning")

            armed = plan.CHARTER.exists() and bool(state.get("charter_sha256"))

            if STOP_FILE.exists() or state.get("paused"):
                # "Pause, then wrap this run up" is one intention, and a paused
                # loop is the safest moment to archive: nothing is in flight.
                # The STOP file is not pause, though - it is the kill switch, and
                # nothing moves, archiving included, until it is taken away.
                if armed and state.get("finish_requested") and not STOP_FILE.exists():
                    finish_run(state, cfg, "finished on request")
                time.sleep(cfg["loop"]["idle_sleep_sec"])
                continue

            if armed and deadline_reached(state, cfg):
                finish_run(state, cfg, f"{run_hours(state, cfg)}h run deadline reached")
                continue
            if armed and state.get("finish_requested"):
                finish_run(state, cfg, "finished on request")
                continue

            if not armed:
                # One charter ends, the next begins: this is what makes the stack a
                # service rather than a single run. Nothing is armed automatically
                # that Tim did not queue himself.
                mark_progress("activating next charter")
                run = runs.activate_next(state, log=log, notify=ntfy)
                if run is not None:
                    state_save(state)
                    hc_ping("", f"armed run {run['run_no']}: {run['title']}")
                    continue
                state_save(state)
                if time.time() - idle_logged > 1800:
                    if plan.CHARTER.exists():
                        # A charter written to /data/plan by hand, or one left
                        # behind by an interrupted arming. The queue cannot move
                        # past it, so say so rather than reporting an empty idle.
                        log("a charter is on disk but not armed: run "
                            "'nightshift.py arm', or remove /data/plan/CHARTER.md "
                            "to let the queue through", level="WARN")
                    else:
                        log(f"idle: nothing armed, "
                            f"{len(runs.queue_list())} charter(s) queued")
                    idle_logged = time.time()
                time.sleep(cfg["loop"]["idle_sleep_sec"])
                continue

            mark_progress("charter check")
            if plan.charter_hash() != state["charter_sha256"]:
                state.update(paused=True, pause_reason="charter changed")
                state_save(state)
                ntfy("The charter's hash no longer matches the one recorded at arming. "
                     "Halted until you resume.",
                     title="NIGHTSHIFT: charter changed", priority="urgent",
                     tags="rotating_light")
                continue

            gov.wait_if_limited(state)

            mark_progress("schedules")
            hour = now().hour
            if ((state.get("last_housekeeping") or "")[:10] != now().strftime("%Y-%m-%d")
                    and hour >= cfg["housekeeping"]["run_at_hour"]):
                housekeeping(state)
            if ((state.get("last_auditor_run") or "")[:10] != now().strftime("%Y-%m-%d")
                    and hour >= cfg["auditor"]["daily_at_hour"]
                    # The auditor is an Opus call reading merge diffs. A run that
                    # has merged nothing gives it nothing to read.
                    and runs.run_stats()["merges"]):
                run_auditor(state, gov=gov)

            mark_progress("planner")
            task = next_ready_task(state)
            if planner_due(state) or (task is None and planner_idle_ok(state)):
                if run_planner(state, gov):
                    continue
                if state.get("limit_until"):
                    continue          # quota is spent; wait_if_limited sleeps it off
            if task is None:
                streak = state.get("idle_planner_streak", 0)
                limit = cfg.get("runs", {}).get("finish_after_idle_planner_runs", 3)
                if limit and streak >= limit:
                    finish_run(state, cfg,
                               f"charter complete: {streak} planner runs added nothing")
                    continue
                log(f"no ready task and the planner added none; idling "
                    f"(idle planner runs: {streak})")
                time.sleep(cfg["loop"]["idle_sleep_sec"])
                continue

            mark_progress(f"task {task['id']}")
            outcome = work_one_task(task, state, gov)
            state["current_task"] = None
            state_save(state)
            log(f"{task['id']} -> {outcome}")

            if outcome in ("merged", "parked"):
                gov.on_success(state)
            if outcome == "merged":
                state["idle_planner_streak"] = 0
                state_save(state)
            if state.get("consecutive_failures", 0) >= cfg["loop"]["max_consecutive_failures"]:
                state.update(paused=True,
                             pause_reason=f"{state['consecutive_failures']} tasks parked in a row")
                state_save(state)
                ntfy(f"Paused after {state['consecutive_failures']} tasks parked in a row.",
                     title="NIGHTSHIFT: repeated failures", priority="urgent",
                     tags="rotating_light")

        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 - the loop must outlive any single error
            log(f"loop error: {type(exc).__name__}: {exc}", level="ERROR")
            state = state_load()
            gov.on_error(state)
            if state.get("other_error_streak", 0) >= cfg["governor"]["max_other_errors"]:
                state.update(paused=True, pause_reason="too many loop errors")
                state_save(state)
                ntfy(f"Paused after {state['other_error_streak']} consecutive loop errors.\n"
                     f"Last: {type(exc).__name__}: {exc}",
                     title="NIGHTSHIFT: loop errors", priority="urgent", tags="rotating_light")


def run_hours(state: dict, cfg: dict) -> int:
    """The deadline in force: the charter's own, else the config default."""
    hours = (runs.active_run() or {}).get("run_until_hours")
    if hours is None:
        hours = cfg["loop"].get("run_until_hours", 0)
    return int(hours or 0)


def deadline_reached(state: dict, cfg: dict) -> bool:
    hours = run_hours(state, cfg)
    armed_at = state.get("armed_at")
    if not hours or not armed_at:
        return False
    return time.time() >= datetime.fromisoformat(armed_at).timestamp() + hours * 3600


def finish_run(state: dict, cfg: dict, reason: str) -> None:
    """End the active charter: last digest, archive, make way for the next one.

    Called only from the top of the loop, so no agent is running and no worktree
    is half-merged. Archiving is what lets the next charter start unattended; if
    it fails the run is left exactly as it was and the loop pauses instead.
    """
    log(f"finishing run: {reason}")
    # A run that merged nothing has nothing to audit, and the auditor is an Opus
    # call: a charter cancelled an hour after arming must not cost a digest that
    # can only say "no merges".
    if runs.run_stats()["merges"]:
        try:
            run_auditor(state, forced=True)
        except Exception as exc:  # noqa: BLE001 - the archive matters more than the report
            log(f"final audit failed: {exc}", level="WARN")
    else:
        log("no merges in this run; skipping the final digest")

    if cfg.get("runs", {}).get("archive_on_finish", True):
        archived = runs.finish_active(state, reason=reason, log=log, notify=ntfy)
        state_save(state)
        if archived is not None:
            queued = len(runs.queue_list())
            log(f"archived to {archived}; {queued} charter(s) queued")
            return

    state.update(paused=True, pause_reason=reason)
    state_save(state)
    ntfy(f"The run is over ({reason}). {state.get('merges_total', 0)} task(s) merged.\n\n"
         f"Nothing further will run until you resume. Review with:\n"
         f"git --git-dir=~/nightshift/data/repos/<project>.git log --oneline agent/integration",
         title="NIGHTSHIFT: run finished", priority="high", tags="checkered_flag")


def cmd_arm() -> int:
    """Record the charter hash. Nothing runs until this has been done."""
    if not plan.CHARTER.exists():
        print("no /data/plan/CHARTER.md", file=sys.stderr)
        return 1
    goals = plan.charter_goals()
    projects = plan.charter_projects()
    if not goals:
        print("the charter declares no goals (expected lines like '- G1: ...')",
              file=sys.stderr)
        return 1
    missing = [name for name in projects if not repo_path(name).exists()]
    if missing:
        print(f"no bare repo for: {missing} (expected /data/repos/<name>.git)",
              file=sys.stderr)
        return 1
    state = state_load()
    state["charter_sha256"] = plan.charter_hash()
    state["armed_at"] = ts()
    state.update(paused=False, pause_reason="", consecutive_failures=0,
                 idle_planner_streak=0, finish_requested=False)
    state_save(state)
    if runs.active_run() is None:
        title = next((line.lstrip("# ").strip() for line in plan.charter_text().splitlines()
                      if line.startswith("# ")), "charter armed by hand")
        runs.write_atomic(runs.ACTIVE_FILE, json.dumps({
            "run_no": runs.next_run_no(), "id": f"manual-{now():%Y%m%d-%H%M%S}",
            "title": title, "slug": runs.slugify(title), "goals": goals,
            "projects": {name: {"source": "", "ref": "HEAD"} for name in projects},
            "test_cmds": {n: p.get("test_cmd", "") for n, p in projects.items()},
            "run_until_hours": None, "armed_at": state["armed_at"],
            "charter_sha256": state["charter_sha256"],
        }, indent=2) + "\n")
    hours = load_config()["loop"].get("run_until_hours", 0)
    if hours:
        ends = datetime.fromtimestamp(time.time() + hours * 3600)
        print(f"run deadline: {hours}h from now ({ends.strftime('%a %d %b %H:%M')})")
    print(f"armed: goals={goals} projects={list(projects)}")
    print(f"charter sha256={state['charter_sha256']}")
    ntfy(f"Armed with goals {', '.join(goals)} across {len(projects)} project(s).",
         title="NIGHTSHIFT: armed", tags="rocket")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "run"
    if cmd == "run":
        return cmd_run()
    if cmd == "selftest":
        return cmd_selftest()
    if cmd == "arm":
        return cmd_arm()
    if cmd == "setup":
        return cmd_setup(argv)
    if cmd == "web":
        import web
        return web.serve()
    if cmd == "notify":
        return 0 if ntfy(" ".join(argv[2:]) or "test", title="NIGHTSHIFT: manual") else 1
    print("usage: nightshift.py [run|web|selftest|setup|arm|notify <msg>]",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(130)
