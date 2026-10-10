"""Screenshot a page so an agent can look at what its CSS and templates render.

Playwright and a headless Chromium live in /opt/playwright, outside every project:
nothing here becomes a project dependency, and no test may rely on it.

    ns-screenshot URL_OR_FILE [OUT.png] [--width 360] [--height 800] [--dark] [--full-page]

A local path is opened as file://. Servers started by the agent are reached on
localhost directly; Chromium ignores the proxy variables. Screenshots default to
/tmp/shots and must never be committed.
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    ap = argparse.ArgumentParser(prog="ns-screenshot")
    ap.add_argument("target", help="http(s) URL, file:// URL or a local HTML path")
    ap.add_argument("out", nargs="?", help="PNG path (default /tmp/shots/<name>.png)")
    ap.add_argument("--width", type=int, default=360)
    ap.add_argument("--height", type=int, default=800)
    ap.add_argument("--dark", action="store_true", help="prefers-color-scheme: dark")
    ap.add_argument("--full-page", action="store_true")
    ap.add_argument("--wait-ms", type=int, default=300,
                    help="settle time after load, for scripts and fonts")
    args = ap.parse_args()

    target = args.target
    if "://" not in target:
        target = Path(target).resolve().as_uri()
    if args.out:
        out = Path(args.out)
    else:
        stem = "".join(c if c.isalnum() else "-" for c in target.split("://", 1)[-1])[:80]
        scheme = "dark" if args.dark else "light"
        out = Path("/tmp/shots") / f"{stem}-{args.width}-{scheme}.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--disable-dev-shm-usage"])
        page = browser.new_page(
            viewport={"width": args.width, "height": args.height},
            color_scheme="dark" if args.dark else "light",
        )
        page.goto(target, wait_until="load", timeout=30_000)
        page.wait_for_timeout(args.wait_ms)
        page.screenshot(path=str(out), full_page=args.full_page)
        browser.close()
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
