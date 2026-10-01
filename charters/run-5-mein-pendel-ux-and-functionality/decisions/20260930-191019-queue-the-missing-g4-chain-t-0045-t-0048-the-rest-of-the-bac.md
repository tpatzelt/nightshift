# Queue the missing G4 chain (T-0045..T-0048); the rest of the backlog stands

_Recorded 20260930-191019 by the NIGHTSHIFT planner._

## Context
M6 is met: T-0031 (re-issue of parked T-0016) and T-0017/T-0018 are done. T-0016 stays parked as history. The ready backlog covers G3 (T-0014, T-0015), G2 (T-0019, T-0020, T-0032..T-0034) and G5 (T-0035..T-0040). All of them still match the code: /today fetches no journeys, _default_window still clamps to 23:59, there is no commutes.html, and there are no unlink/test routes. The previous ADR says G4 tasks T-0041..T-0044 were queued, but none is in the backlog, so G4 has no path to done. Code facts: style.css is 28 lines with raw hex colors and no custom properties or dark mode. static/ has only css/. base.html links no manifest. today.html already renders an aria-hidden icon plus a text label inside .status-<s>, but the stylesheet has no status rules.

## Decision
Add G4 tasks with fresh ids T-0045..T-0048, because T-0041..T-0044 may have been issued and must not be reused. T-0045 adds CSS tokens, the dark block and 44px targets. T-0046 adds status colors and a pure-Python WCAG contrast test. T-0047 adds the manifest, stdlib-generated PNG icons and base.html links. T-0048 is the G4 done test, which enumerates every HTML GET route after the G2/G5 pages exist. They go at the end of the backlog, following the charter priority G1 > G3 > G2 > G5 > G4. T-0045 and T-0047 touch only style.css, base.html, static files and a new tests/test_design.py, so they have no dependencies and can run in parallel with the app.py chain. Assumptions: (1) the manifest is served as /static/manifest.json so StaticFiles sends a JSON content type without app changes; (2) start_url is /today; (3) today.html is left to T-0014, so status styling lives in CSS only; (4) no service worker, per the non-goals. No other backlog changes.

## Consequences
Every goal now has a task chain ending in a definition-of-done test: G3 at T-0015, G2 at T-0034, G5 at T-0040, G4 at T-0048. No new dependency, migration or network access. T-0048 depends on T-0033 and T-0039, so it runs last and covers the pages they add. If a G4 check fails on a page owned by another task, T-0048 reports it rather than editing templates.
