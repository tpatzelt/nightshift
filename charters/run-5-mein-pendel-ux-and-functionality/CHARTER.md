# Mein Pendel: UX and functionality

Charter  (immutable — agents must not edit)

Mein Pendel is live at a public URL and works end to end, but it still feels like a
prototype: visitors type raw stop IDs and free-text line names, the "today" page shows
bare IDs, a saved commute can't be edited, and the stylesheet is 28 lines. This run
makes it an app a stranger from Reddit can set up in under a minute on a phone.

## Goals
- G1: Guided commute setup. Search origin and destination by name, then pick the lines
  from checkboxes of the lines that actually depart from the chosen origin (read from
  its departures), so a visitor never types a stop ID or a line name. Stop names are
  stored with the commute. Sensible defaults: Mon–Fri, a 30-minute window starting at
  the next full half hour, delay threshold 5 min. The whole flow is at most three
  screens and works without JavaScript.
- G2: Manage commutes. A "my commutes" page lists every saved commute by name with its
  lines, days and window, and each one can be edited, paused/resumed and deleted
  individually. Departure windows may cross midnight (e.g. 23:30–00:30), including
  across DST transitions. Paused commutes are never checked by the scheduler.
- G3: A useful "today" page. One card per commute, showing stop names (never IDs), a
  clear status (OK / disrupted / paused / checking failed), the reason in the UI
  language, the next departures on the ridden lines with planned vs real-time time and
  platform, and the suggested alternative when there is one. When a remark's summary is
  generic ("Information.", "Störung."), the reason uses a shortened, cleaned version of
  the remark text instead. The alternative must still be found when HAFAS reports the
  journey's arrival at a child stop of the saved destination.
- G4: Visual design. A coherent, small design system in plain CSS (custom properties
  for color, spacing and type), light and dark mode following `prefers-color-scheme`,
  status never shown by color alone, WCAG AA contrast, touch targets at least 44px,
  and a web app manifest plus icons so the site can be added to a phone's home screen.
  Still server-rendered: small vanilla JS for progressive enhancement is allowed, but
  every page works with JS disabled.
- G5: Better notifications. A notification names the commute, line, planned time,
  reason and alternative, and links to the "today" page; the "resolved" message says
  what cleared. The notifications page shows which channels are linked, lets the
  visitor unlink each one, and offers a "send test message" action. All of this is
  exercised only against the fake channels.

## Non-goals
- No user accounts with passwords, no payments, no ads, no analytics or trackers.
- No native app, no Web Push, no service worker, no SMS, no email.
- No frontend framework, bundler, npm or any JS build step; no CSS framework.
- No scraping of bvg.de, s-bahn.berlin or any site; only the HAFAS REST API.
- No edits outside this repo (the homelab repo and deploy host are off limits), and no
  changes to how the image is built or published beyond what a goal requires.
- No reformatting or restructuring not required by a specific task.

## Constraints
- Python >= 3.12, uv: `uv sync`, `uv run pytest -q`. Dependencies are allowed but must
  be justified in the commit message; prefer stdlib + fastapi + httpx + jinja2 + sqlite.
- SQLite at a path from `PENDEL_DATA_DIR`. Schema changes are new numbered plain SQL
  migration files; existing migrations are never edited, and every migration must
  upgrade the live database (existing users, commutes and channels) without data loss —
  tested against a database created by the current schema.
- `uv run pytest -q` must stay green and fully offline: HTTP is replayed from fixtures
  under `tests/fixtures/**`; a test that touches the network is a failing test. Prefer
  the real recorded fixtures in `tests/fixtures/hafas/recorded/`; new fixtures may be
  recorded from v6.bvg.transport.rest (small, never looped, public instance is
  rate-limited to ~100 req/min). Real stop IDs are 9 digits, e.g. Alexanderplatz
  900100003, Ostkreuz 900120003, Hauptbahnhof 900003201. If the API errors, record the
  exact error and try again later; it has had outages, it is not a sandbox block.
- Never contact Telegram, ntfy or any other messaging service, even though the sandbox
  has open egress: no bot token is provided, none may be created, and no request may
  be sent to api.telegram.org or any ntfy server. Both channels are faked in tests.
- No secrets, tokens, real domains, LAN IPs or personal data in the repository.
- Times are Europe/Berlin throughout; DST transitions are tested.
- German and English for every new string. Every page keeps passing the 360px layout
  test (viewport meta, no fixed widths).
- The Impressum and Datenschutz placeholders stay as they are.

## Definition of done per goal
- G1: TestClient tests walk the full setup (search origin, search destination, pick
  lines, save) using recorded fixtures, with no stop ID or line name typed; the line
  choices come from the origin's departures fixture; the saved commute stores stop
  names; the flow works with JS disabled (no required script).
- G2: Tests cover list, edit, pause/resume and delete of a single commute (deleting one
  leaves the others); the engine and scheduler handle a window crossing midnight,
  including on a DST transition night; the scheduler skips paused commutes; a migration
  test upgrades a database created by the previous schema.
- G3: A test renders "today" for an OK, a disrupted, a paused and a failed-check commute
  and asserts stop names appear and raw IDs don't; next departures show planned and
  real-time times; generic remark summaries fall back to cleaned remark text; an
  alternative is found when the arrival is at a child stop of the destination.
- G4: The stylesheet defines its colors as custom properties with a dark-mode block; a
  test checks every page links the manifest and that status markup carries a text or
  icon label, not only a class; a contrast test checks the status colors against their
  backgrounds at 4.5:1 in both modes.
- G5: Tests with the fake channels assert the notification text contains commute name,
  line, planned time and reason, and a link to /today; unlink removes only that
  channel; "send test message" sends exactly one message through the fake.

## Priority order
G1 > G3 > G2 > G5 > G4

## Allowed idle work (when the backlog is empty)
Tests, recorded fixtures of further real disruption kinds, documentation, accessibility
and small refactors strictly within G1–G5. Nothing new.

## Projects
- repo: mein-pendel   goals: [G1, G2, G3, G4, G5]   test_cmd: "uv run pytest -q"
