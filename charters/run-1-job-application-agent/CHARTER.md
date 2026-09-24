# Charter  (immutable — agents must not edit)

## Goals
- G1: An offline, network-free result-quality harness exists. It replays the recorded
  search results in `evals/runs/**` through the agent's deterministic logic and reports
  per-metric scores (posting-shape rate, aggregator-drop rate, location match, staleness
  detection, dedup rate), so any change's effect on result quality is measurable without
  Brave or OpenRouter keys.
- G2: Result quality improves as measured by G1. The deterministic logic that decides which
  URLs become results — `src/url_heuristics.py`, `src/page_signals.py`, and the triage and
  dedup paths in `src/crawler_engine.py` / `src/orchestrator.py` — produces better scores on
  the G1 harness than the baseline recorded at arming.
- G3: The output is more useful to read. `src/notifier.py`, `src/telegram_api.py` and
  `src/bot_service.py` produce job messages that state why a job matched, never notify twice
  about the same posting, and surface failures as actionable text instead of silence.

## Non-goals
- No live Telegram call of any kind. The deployed bot has real users; agents must never send
  them a message. `TELEGRAM_BOT_TOKEN` is deliberately absent from the sandbox.
- No live API call inside the default test suite or inside the G1 harness. `uv run pytest -q`
  and `python -m evals.offline_eval` must stay offline, deterministic and repeatable — they
  are what the merge gates run, and a flaky gate is worse than no gate.
- No new runtime or test dependencies.
- No changes to deployment: `Dockerfile`, `docker-compose.yml`, `.github/**`, `pyproject.toml`,
  `uv.lock`.
- No reformatting, renaming or restructuring that is not required by a specific task.
- No changes to the LLM prompts' intent (wording may be improved; behaviour under test may not
  silently change).

## Constraints
- Python >= 3.11, standard tooling: `uv sync`, `uv run pytest -q`.
- `uv run pytest -q` must stay green: 182 passed, 1 skipped is the baseline at arming.
- `uv run python run_mock_test.py` must keep passing (offline end-to-end loop).
- No secrets, no API keys, no personal data in the repository.
- The sandbox has open outbound internet access and holds real `BRAVE_API_KEY` and
  `OPENROUTER_API_KEY` credentials in the environment. Use them to develop and validate
  against the real APIs: run real searches, inspect what actually comes back, and check that
  a change behaves on live data as the offline harness predicts.
- Live calls cost Tim real money and quota. Respect the repo's effort budget
  (`[tool.job_crawler.budget]`), keep exploratory runs small, and never loop a live search in
  a test. Prefer replaying a recorded fixture once you have seen the live behaviour.
- When a live call teaches you something, capture it as a fixture under `evals/fixtures/**`
  so the offline harness keeps the lesson and the next agent need not pay for it again.
- Never write a key into a file, a commit, a log or a fixture. The merge gates reject any
  diff containing one.

## Definition of done per goal
- G1: `uv run python -m evals.offline_eval` exits 0, prints a per-metric table, writes a JSON
  report under `evals/runs/offline/`, and is covered by tests that fail if a metric is
  miscomputed. README documents what each metric means and how to run it.
- G2: The metric table from G1 shows an improvement over the arming baseline on at least
  posting-shape rate and aggregator-drop rate, with no metric regressing, and every change is
  covered by an offline test that fails without it. Live-API validation may inform a change
  and must be described in the commit message, but the offline harness remains the measure —
  a live run is evidence, never proof.
- G3: Every user-visible message path has a test asserting its content; a job already notified
  is provably not notified again; an error during a scan produces a message naming what failed.

## Priority order
G1 > G2 > G3

## Allowed idle work (when the backlog is empty)
Tests, documentation and small refactors strictly within G1–G3. Nothing new.

## Projects
- repo: job-application-agent   goals: [G1, G2, G3]   test_cmd: "uv run pytest -q"
