# One remaining message-path gap: the exact text of the active-chat and already-set-up /start replies

_Recorded 20260924-085800 by the NIGHTSHIFT planner._

## Context
On 2026-09-24 HEAD is cc1a1b6 and the backlog is empty. The mount is read-only, so I copied it to a scratch directory and ran the gates there. `uv run pytest -q` gave 388 passed, 1 skipped. `uv run python -m evals.offline_eval` exited 0 and scored 1.000 on all five metrics across 58 records. The arming baseline was posting_shape 0.815 and aggregator_drop 0.765, so G1 and G2 meet their definition of done. The previous pass said a new task is justified only if a message path turns up without an exact-text test. I compared the reply strings in src/intake.py, src/bot_service.py, src/notifier.py and src/telegram_api.py against the tests. The bot_service send paths, the notifier text and most intake replies already have exact assertions. Two intake replies do not: _handle_active_chat and the already-active branch of _handle_start. Both reach users through BotService._dispatch and are checked only by substrings in tests/test_intake.py:465 and :481. I confirmed the exact strings by driving both paths on the scratch copy, and equality assertions against them passed.

## Decision
Add T-0067 under M3/G3. It is a tests-only task in tests/test_intake.py that turns the two fragment checks into exact-equality assertions, with no src/ change. I am not reviving any parked task: each one was superseded by a re-issue that has since merged. I added nothing for G1 or G2 because their definitions of done are met. Assumption: tightening an existing fragment test to exact text counts as allowed idle work ('tests strictly within G1–G3'), because G3 requires every user-visible message path to have a test that asserts its content.

## Consequences
Once T-0067 merges, every user-visible reply string I found in the G3 files and in intake.py (which reaches the user through bot_service) has an exact-text assertion. The next pass should emit no ops unless new input arrives: a worker followup, a commit that regresses a gate, or a newly found message path without an exact-text test.
