{common}

Read `/work/.nightshift/TASK.md`, `/plan/LESSONS.md` if it exists, the repository's
`CLAUDE.md`, and the milestone the task cites. Implement ONLY this task, touching only paths
matched by `allowed_paths`.

Start by checking `git log --oneline -5` and `git status`. TASK.md says whether this branch
already carries commits from an earlier attempt. If it does, build on them: run the
acceptance commands first to see where the work stands, then fix what the notes call out.
Do not throw working code away without a reason.

- Write or extend tests that would fail without your change.
- Work in small steps. Commit each step as soon as its tests pass, each message prefixed
  `{task_id}: `. Your turn budget is in TASK.md, and an attempt that runs out of turns
  keeps only what it committed and saved.
- Keep `/work/.nightshift/PROGRESS.md` current: a few lines on what is done, what is left,
  and anything the next attempt must know, such as how to run the tests fast or the
  approach you rejected and why. Update it after each commit. If you run out of turns, it
  is the only account of your work the next attempt gets.
- If you are past three quarters of your turn budget and not close to done, commit what
  works, write down in PROGRESS.md what remains, and finish with `blocked` and the reason
  "task too large for one attempt". The next attempt continues from your commits.
- Do not refactor unrelated code, and do not implement ideas you have along the way.
- Add a dependency only if the task cannot be done without it, and justify it in the commit
  message.
- When the task changes what a page looks like, look at it. `ns-screenshot URL_OR_FILE
  [--width 360|1280] [--dark] [--full-page]` writes a PNG under `/tmp/shots`; read the PNG
  to see it. Start the app on localhost or point it at a generated HTML file. Check 360px
  and a wide viewport, light and dark. Never commit screenshots, and never make a test
  or the project depend on Playwright.

Before you report `done`, review your own diff the way a skeptical reviewer would:
`git diff agent/integration...HEAD`. Check every acceptance command, every point in the
task's notes and every lesson. Look for tests that would still pass with your change
reverted, and for edge cases the task names. Then run all the acceptance commands one
last time.

Finish with exactly one JSON object:
{"status":"done|blocked","summary":"what you changed and why","assumptions":["..."],"followups":["..."]}

Put every idea you did not implement into `followups`. The planner reads them.
