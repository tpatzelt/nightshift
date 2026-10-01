# Re-issue parked T-0048 (G4 done test) as two narrow test-only tasks T-0051 and T-0052, queued after the G5 chain

_Recorded 20261001-004522 by the NIGHTSHIFT planner._

## Context
G1, G3 and G2 have their definition-of-done tasks done (T-0006, T-0049, T-0034). G5 has a ready six-task chain (T-0035..T-0040) whose dependencies are all done or earlier in that chain. G4's design tokens, dark mode, status contrast and manifest landed (T-0045..T-0047). But the G4 done test T-0048 was parked after two attempts ended with no status. Its scope was wide: enumerating app.routes, seeding four HAFAS-backed today cards in DE/EN, and checking three pages. Reading the code shows what is actually missing: tests/test_design.py:_MANIFEST_PAGES omits /commutes, /commutes/new and /commutes/{id}/edit, and no design test asserts that status markup has a visible label. The only status-classed markup is in today.html (class="status-*" with an aria-hidden icon plus status_label). commutes.html shows paused as plain text.

## Decision
Split T-0048 into T-0051 (manifest link and viewport meta on an explicit list of every HTML page, including the three G1/G2 pages) and T-0052 (render today.html directly through pendel.app._status_item and the app's Jinja env, for all five statuses in DE and EN, asserting the visible label; plus a static guard that any template using status-* classes renders status_label). Both edit only tests/test_design.py, protect src/**, have a 150-line diff budget and a 30 min / 40 turn budget, and depend on the G5 chain so they run last, following charter priority G1 > G3 > G2 > G5 > G4. T-0048 stays parked as history. Assumption: rendering the template with the app's own _status_item and the i18n strings is enough to meet 'a test checks that status markup carries a text or icon label', because tests/test_web_today.py already exercises the /today route end to end for all four statuses. Assumption: an explicit page list instead of route enumeration still meets 'every page'.

## Consequences
Once G5 lands, G4 has a small, concrete path to its definition of done. No production code, migration, dependency, fixture or network change. If either test finds a real defect (a page without the manifest, a status without a label), the worker reports blocked, and a template fix task follows next round.
