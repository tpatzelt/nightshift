# Mein Pendel: frontend styling and UX

Charter  (immutable — agents must not edit)

Mein Pendel works and run 5 made it usable, but it still looks unstyled. There is no
header or app navigation, so the footer is the only way around. Every link, including
links inside a sentence, is forced into a 44px inline-flex box. The "today" page is a
bulleted list of paragraphs. The setup flow, the commutes list and the notifications
page are bare forms. The person this run serves opens the app on a phone on the
platform at 7:40 and needs to know in one glance whether the train is running. This
run makes Mein Pendel look and feel like a small, trustworthy transit app. No new
features are added.

## Goals
- G1: App shell and navigation. Every page gets a compact header with the app name and
  primary navigation (Heute/Today, Meine Pendel/My commutes, Benachrichtigungen/
  Notifications). The current page is marked with `aria-current`, and the language
  switch is reachable from the header. On phones the navigation stays usable with one
  thumb, either as a bottom tab bar or as a header row that fits at 360px (an ADR picks
  which). Touch-target sizing applies to nav items, buttons and form controls only, and
  inline text links return to normal inline flow.
- G2: The "today" page as a status board. Each commute is a card: the commute name and
  "origin → destination" as the title, a large status badge (icon + word + color, never
  color alone), and the reason and alternative in a clearly separated callout when
  disrupted. Departures go in an aligned table-like list: line badge, planned time,
  real-time time, delay, and platform, with changes such as a platform change or a
  cancellation visually emphasized. A disrupted commute sorts above an OK one. The page
  shows when it was last checked ("Stand 07:41") and offers a refresh that works
  without JS. The empty state gets a friendly illustration-free design with one clear
  call to action.
- G3: Forms and the setup flow. The three setup screens show a step indicator
  ("Schritt 2 von 3"). Stop search results are tappable rows, not radio soup. Line
  choices are chip-style checkboxes grouped by product (S, U, Tram, Bus) with the
  product's conventional color as a secondary cue next to a text label. Day selection is
  a row of toggles. Validation errors sit next to their field with `aria-describedby`.
  Primary and secondary buttons are visually distinct, and destructive actions (delete
  a commute, unlink a channel) are styled as such and confirmed on a no-JS page.
- G4: "My commutes" and "Notifications". Commutes are listed as cards with their lines,
  days and window in a scannable summary, and edit, pause/resume and delete are
  reachable without crowding. A paused commute looks paused. On the notifications page
  each channel shows its linked or unlinked state at a glance, linking instructions are
  numbered steps, and "send test message" reports its result inline.
- G5: Design-system pass and polish. Extend the existing tokens with a type scale,
  radii, elevation (shadow or border), and a single accent color with a matching dark
  value, and put every color through these tokens. Visible `:focus-visible` styles, a
  skip link, `prefers-reduced-motion` respected, and smooth, short transitions only
  where they help. The app icon and `theme-color` match the new accent in both modes
  (`theme-color` gets a media query per scheme). The About, Impressum and Datenschutz
  pages share the same layout as everything else.

## Non-goals
- No new features. No new notification channels, data, API calls, scheduler or engine
  changes. Python changes are limited to what a template needs, for example passing
  the stop names, the last-checked time, or the sort order to "today".
- No user accounts with passwords, no payments, no ads, no analytics or trackers.
- No native app, no Web Push, no service worker.
- No frontend framework, bundler, npm or JS build step. No CSS framework, no icon font,
  and no web fonts from a CDN. Icons are inline SVG or Unicode.
- No database schema changes.
- No edits outside this repo. The homelab repo and the deploy host are off limits, and
  the Dockerfile, `deploy/` and CI change only if a goal strictly requires it.
- The Impressum and Datenschutz placeholders stay as they are.
- No reformatting or restructuring that a specific task does not require.

## Constraints
- Python >= 3.12, uv: `uv sync`, `uv run pytest -q`. New dependencies need a
  justification in the commit message, and none should be needed.
- `uv run pytest -q` must stay green and fully offline. HTTP is replayed from the
  fixtures under `tests/fixtures/**`, and no new live HAFAS calls are needed.
- Server-rendered. Small vanilla JS for progressive enhancement is allowed, but every
  page and every action works with JS disabled.
- German and English for every new string. Every page keeps passing the 360px layout
  test (viewport meta, no fixed widths).
- `tests/test_design.py` and `tests/test_web_a11y.py` keep passing. They may be
  extended, never weakened. Status is never shown by color alone. WCAG AA contrast
  holds in both modes, and touch targets are at least 44px for controls.
- Workers can see what they build: `ns-screenshot` (Playwright + headless Chromium,
  preinstalled outside the project) screenshots a generated page or a local server.
  Every visual task checks its pages at 360px and 1280px, in light and dark mode.
  Playwright must not become a project dependency, and no test may require it. Never
  commit screenshots.
- Never contact Telegram, ntfy or any other messaging service, even though the sandbox
  has open egress. No bot token is provided, none may be created, and no request may be
  sent to api.telegram.org or any ntfy server. Both channels are faked in tests.
- No secrets, tokens, real domains, LAN IPs or personal data in the repository.

## Definition of done per goal
- G1: A test renders every page in DE and EN and asserts the header nav is present,
  that exactly one item carries `aria-current="page"` on the three main pages, and that
  the language switch is in the header. A CSS test asserts the 44px minimum applies to
  nav, button and form-control selectors and not to bare `a`.
- G2: A test renders "today" with an OK, a disrupted, a paused and a failed commute and
  asserts that disrupted sorts first, that each card has a heading with both stop
  names, that the status badge carries text, that a last-checked time is shown, and
  that the refresh is a plain link or form. Platform-change and cancelled departures
  carry a distinguishing class and text.
- G3: TestClient tests walk the setup flow and assert the step indicator on each
  screen, the lines grouped by product with text labels, and field errors linked via
  `aria-describedby`. Delete and unlink go through a confirmation page without JS.
- G4: Tests assert that each commute card shows lines, days and window, that a paused
  card carries a paused label, and that the notifications page shows linked or
  unlinked text per channel and an inline result after a test message (fake channel).
- G5: The existing token, contrast and dark-mode tests cover the new tokens and the
  accent. A test asserts that every page has a skip link and that `theme-color` has a
  media-qualified value per scheme. A test asserts that no raw color literal appears
  outside `:root` and the dark block.

## Priority order
G2 > G1 > G3 > G5 > G4

## Allowed idle work (when the backlog is empty)
Tests, accessibility, copy editing of existing strings in both languages, and small
refactors of templates and CSS strictly within G1–G5. Nothing new.

## Projects
- repo: mein-pendel   goals: [G1, G2, G3, G4, G5]   test_cmd: "uv run pytest -q"
