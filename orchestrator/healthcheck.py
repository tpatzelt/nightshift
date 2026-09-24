#!/usr/bin/env python3
"""Container healthcheck: fail if the main loop has stopped advancing.

The loop rewrites /data/state/heartbeat every iteration. If that file is missing
or older than loop.heartbeat_stale_min, Docker marks the container unhealthy and
(together with restart: unless-stopped and the watchdog thread) it gets recycled.
"""
import sys
import time
from pathlib import Path

import yaml

HEARTBEAT = Path("/data/state/heartbeat")
CONFIG = Path("/app/config.yaml")


def main() -> int:
    try:
        stale_min = yaml.safe_load(CONFIG.read_text())["loop"]["heartbeat_stale_min"]
    except Exception:  # noqa: BLE001 - a broken config must not mask the real signal
        stale_min = 30
    if not HEARTBEAT.exists():
        print("no heartbeat file yet", file=sys.stderr)
        return 1
    age_min = (time.time() - HEARTBEAT.stat().st_mtime) / 60
    if age_min > stale_min:
        print(f"heartbeat is {age_min:.1f} min old (limit {stale_min})", file=sys.stderr)
        return 1
    print(f"heartbeat {age_min:.1f} min old")
    return 0


if __name__ == "__main__":
    sys.exit(main())
