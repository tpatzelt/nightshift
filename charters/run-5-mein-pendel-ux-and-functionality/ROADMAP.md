# Roadmap

One milestone per goal to start with; the planner adds more as it learns what the code actually needs.

M1 [G1] First milestone for G1 — planned — the charter's definition of done for G1 is met
M2 [G2] First milestone for G2 — planned — the charter's definition of done for G2 is met
M3 [G3] First milestone for G3 — planned — the charter's definition of done for G3 is met
M4 [G4] First milestone for G4 — planned — the charter's definition of done for G4 is met
M5 [G5] First milestone for G5 — planned — the charter's definition of done for G5 is met

M6 [G2] Recover the parked midnight-window work — planned — T-0031 (re-issue of parked T-0016) is done: Commute accepts windows crossing midnight, DST-tested, with tests/test_web_commutes.py updated; T-0017..T-0019 unblocked.

M7 [G1] Idle work: README documents the finished visitor flows — planned — README.md has a 'Using Mein Pendel' section that names the guided setup (/stops then /commutes/new), /commutes (edit, pause/resume, delete), /today and /notifications (unlink, send test message). Its goal labels match the current charter. tests/test_readme.py asserts this, and uv run pytest -q is green.

M8 [G4] Idle work: accessibility guard that every visible form control has a label — planned — tests/test_web_a11y.py asserts that every visible input, select and textarea has an accessible label (a <label for> that matches its id, or a wrapping <label>). It covers /stops, /commutes/new with origin and destination, the edit page of a saved commute, and /notifications, in both DE and EN. uv run pytest -q is green, and src/** is unchanged.

M9 [G3] Idle work: a recorded fixture of a real platform change — planned — tests/fixtures/hafas/recorded/departures_platform_change.json is a real verbatim-trimmed v6.bvg.transport.rest response. At least one departure in it has platform and plannedPlatform both set and different. It is documented in tests/fixtures/hafas/recorded/README.md. tests/test_engine_recorded.py asserts that next_departures carries both platforms for that departure, and tests/test_web_today.py asserts that /today shows 'Gleis X statt Y' / 'Platform X instead of Y' for it. uv run pytest -q is green and offline. src/** is unchanged.
