# Editorial portfolio, in the vein of mathismiener.com

Charter  (immutable — agents must not edit)

## Reference

https://mathismiener.com/ — a brand designer's portfolio. What to take from it:

- **Light and neutral.** Near-white ground, near-black text, one restrained accent.
  The page is a document, not a light show.
- **Typography carries the design.** Inter / Inter Tight, a wide weight range, a
  large display headline against small quiet body copy and captions. Hierarchy comes
  from size and weight, not colour.
- **Whitespace is the layout.** Generous vertical rhythm, content in a narrow
  measure, sections separated by space rather than rules or boxes.
- **It scrolls, and it says things.** A hero statement of who he is, then skills,
  then experience in numbers, then real project entries, then testimonials, then
  contact. Several sections, each earning its place.
- **Restraint in motion.** Smooth scrolling and a little interactivity, no
  continuous ambient animation.

What NOT to take: the agency/testimonial framing and the project-tile grid are his
content model, not Tim's. Tim is a machine learning engineer, not a brand designer.

## Goals

- G1: Replace the current single-screen dark hero with a light, typographic,
  multi-section page in the reference's spirit — a page that reads as an engineer's
  professional site rather than a landing animation.
- G2: Give the page real content sections beyond the name and the links — at minimum
  an "about" statement, a selected-work or projects section, and a contact section —
  structured so adding an entry later is editing data, not hand-writing markup.
- G3: Keep the page fast, accessible and dependency-free: no JS framework, no web
  fonts beyond the one family, correct heading order, visible focus, working
  reduced-motion, and legible at 400px wide.

## Non-goals

- Deployment, CI, the Pages configuration, and `.github/**`. Do not touch them.
- The CV PDF, and the contents of `_config.yml` beyond adding data that new sections
  need. Do not change Tim's name, email, or social handles.
- Inventing biography. If a section needs facts that are not already in the repo
  (project descriptions, employers, dates, testimonials), use clearly-marked
  placeholder copy and list what is needed in the task notes. Do not fabricate
  Tim's history, employers, publications, or client quotes.
- A CMS, a build step beyond Jekyll, or a package.json.

## Constraints

- `bash scripts/check-site.sh` must stay green.
- The site is built by GitHub Pages' legacy Jekyll builder. Use only plain Liquid and
  Jekyll features that need no plugin, and no Sass beyond what already exists.
- No secrets, no API keys and no personal data beyond what `_config.yml` already
  carries.
- Keep it to plain HTML, CSS and vanilla JS. No frameworks, no CDN scripts, no npm.
- One `<h1>` per page, and headings in order.

## Definition of done per goal

- G1: The page loads light-themed and typographic, the ambient canvas background and
  the blurred parallax blobs from run 2 are gone, and `check-site.sh` is green.
- G2: The page has at least three content sections beyond the hero, and the
  repeated ones (projects, and anything list-shaped) render from a data structure —
  `_data/*.yml` or a `_config.yml` key — rather than from copy-pasted markup.
- G3: Heading order is correct with exactly one `<h1>`; every interactive element has
  a visible focus style; `prefers-reduced-motion: reduce` disables every transition
  and scroll effect the page adds; the page has no horizontal scrollbar at 400px.

## Priority order

G1, then G2, then G3.

## Projects

- repo: tpatzelt.github.io   goals: [G1, G2, G3]   test_cmd: "bash scripts/check-site.sh"
