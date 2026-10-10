# Wie Berlin radelt: frontend styling and UX

Charter  (immutable — agents must not edit)

Wie Berlin radelt is live and collecting. Its numbers are right, but the site reads
like a test page. Every paragraph is printed twice, in German and then English. The
charts are bare polylines with no axes, gridlines or labels, so nobody can read a
value off them. The stylesheet is 77 lines, there is no site header or navigation
beyond a footer, and the map page is a dropdown above a box. Around 2026-11-01 the
site goes to r/berlin. This run makes it look and read like a considered data
article in the spirit of Todd Schneider's write-ups, on a phone first. No new
analysis or metric is added.

## Goals
- G1: One language at a time. Each page renders in German or English, never both
  side by side. German is the default. An English version is generated next to it
  (for example `en/index.html`, or `index.en.html`, an ADR picks which). A visible
  switch in the header links each page to its counterpart. `<html lang>` and
  `hreflang` alternate links match. Every string that exists today keeps both
  translations. No translation goes missing and nothing falls back silently to the
  other language.
- G2: Readable charts. Every SVG chart gets labelled x and y axes with tick values,
  light gridlines, units in the axis title, and direct line labels or a legend that
  sits next to the lines it names. The headline value of each chart is called out in
  the chart itself (for example the 8:00 dip). Weekday lines can be told apart without
  color: by dash pattern or by direct labels. Charts stay plain server-rendered SVG with
  no JS charting library, scale to the container width, and keep their table
  fallbacks. Text inside SVG stays legible at 360px (at least 11px rendered).
- G3: A design system and an editorial layout. Plain CSS with custom properties for
  color, spacing, type scale and radii, plus a dark-mode block that redefines every
  color token. A readable measure (about 60–75 characters) for prose, with charts and
  the map allowed to break out wider on large screens. A real type hierarchy, a site
  header with the title and navigation, a lead paragraph and key-number callouts at the
  top of the article, section anchors, and a footer that stays quiet. The "not enough
  data yet" state is a designed component that shows progress toward 14 days, not a
  bordered box. Use the system font stack, or one self-hosted variable font committed
  with its license. No Google Fonts or other font CDN.
- G4: The map page as a tool. Choosing a station or Ortsteil is possible by tapping
  the map as well as from the select, and the select is searchable by typing. The
  weekday curve sits beside the map on wide screens and below it on phones, has the
  same axes as G2, and marks the hour the visitor is looking at. Station markers are
  colored by typical availability at a selected hour with a legend, and the color is
  never the only cue. The selection is reflected in the URL hash, so a link to "my
  station" works. Keyboard users can do everything without the map.
- G5: Polish and accessibility. WCAG AA contrast for text, chart ink and series colors
  against both backgrounds. Visible focus states, a skip link, 44px touch targets for
  controls and nav, and `prefers-reduced-motion` respected. Open Graph and Twitter-card
  meta with a static preview image committed to the repo, so the Reddit link shows a
  card. A favicon. The methodology page gets the same typographic care as the article.

## Non-goals
- No new metrics, analyses, data sources or collector changes. `analysis/`,
  `collector.py`, `gbfs.py`, `weather.py`, `storage.py` and `cells.py` change only when
  a chart needs a value reshaped for display, and never in what they compute.
- No frontend framework, bundler, npm, or JS build step. No CSS framework, and no JS
  charting library (Vega or D3 included). Leaflet stays the only third-party script,
  pinned with SRI.
- No analytics, trackers, cookies, or third-party requests other than the map tiles
  and Leaflet already in use.
- No edits to the homelab repo, the Dockerfile, `deploy/` or CI beyond what a goal
  strictly requires.
- The Impressum and Datenschutz placeholders stay as they are.
- No reformatting or restructuring that a specific task does not require.

## Constraints
- Python >= 3.12, uv: `uv sync`, `uv run pytest -q`. New dependencies need a
  justification in the commit message, and none should be needed.
- `uv run pytest -q` must stay green and fully offline. Pages are rendered from the
  synthetic dataset, both with enough data and below the 14-day guard. Every page must
  look finished in both states.
- Every page keeps passing the 360px layout test (viewport meta, no fixed widths). The
  existing chart-fallback, theme-token and methodology tests keep passing. They may be
  extended, never weakened.
- Workers can see what they build: `ns-screenshot` (Playwright + headless Chromium,
  preinstalled outside the project) screenshots a generated page or a local server.
  Every visual task checks its pages at 360px and 1280px, in light and dark mode.
  Playwright must not become a project dependency, and no test may require it. Never
  commit screenshots, except the G5 preview image.
- The sandbox has open egress. No live calls to the GBFS feeds, Bright Sky or the tile
  server are needed in this run, and none may be made.
- Generated site output goes to `BIKES_SITE_DIR` and is never committed.
- No secrets, tokens, real domains, LAN IPs or personal data in the repository.

## Definition of done per goal
- G1: A test builds the site and asserts that each German page contains no English
  body copy and each English page contains no German body copy (for example, no
  `lang="en"` spans in a `lang="de"` page). Both versions exist for every page, each
  links to the other, and `hreflang` alternates are present. A test fails if a
  translation key exists in one language only.
- G2: A test asserts that every chart SVG contains axis tick labels on both axes, an
  axis title with a unit, and a headline annotation. Weekday series differ by
  `stroke-dasharray` or carry direct labels. Table fallbacks are still present.
- G3: A test checks that the stylesheet declares color, spacing and type tokens in
  `:root`, that a dark block redefines every color token, and that no raw color
  literal appears outside those blocks. Every page has a header with the navigation.
  The not-enough-data component renders a progress indication with the day count.
- G4: The map page works without JS (the select and a server-rendered curve or table
  for a default selection). With JS, the selection round-trips through the URL hash.
  A test asserts the legend exists and that markers carry an accessible name.
- G5: A contrast test checks text, muted text, links, chart ink and every series color
  at 3:1 for graphics and 4.5:1 for text, in both modes. Every page has a skip link,
  OG meta and a favicon link, and the preview image exists at its declared size.

## Priority order
G1 > G2 > G3 > G5 > G4

## Allowed idle work (when the backlog is empty)
Tests, accessibility, chart clarity, copy editing of existing text in both languages,
and small refactors of the site templates and CSS strictly within G1–G5. Nothing new.

## Projects
- repo: berlin-bike-data   goals: [G1, G2, G3, G4, G5]   test_cmd: "uv run pytest -q"
