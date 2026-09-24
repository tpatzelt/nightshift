# Roadmap

M1 [G1] Offline result-quality harness — planned — `uv run python -m evals.offline_eval` replays the recorded runs, prints a per-metric table, writes a JSON report, and is covered by tests
M2 [G2] Deterministic triage and signals improved — planned — the M1 metric table beats the arming baseline on posting-shape and aggregator-drop rates with no metric regressing
M3 [G3] Output that explains itself — planned — every user-visible message path is asserted by a test, repeat notifications are provably impossible, and scan failures produce actionable text
