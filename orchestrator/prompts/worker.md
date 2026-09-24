{common}

Read `/work/.nightshift/TASK.md`, the repository's `CLAUDE.md`, and the milestone the task
cites. Implement ONLY this task, touching only paths matched by `allowed_paths`.

- Write or extend tests that would fail without your change.
- Run every command under `acceptance` before you finish, and make them pass.
- Commit in small steps, each message prefixed `{task_id}: `.
- Do not refactor unrelated code, and do not implement ideas you have along the way.
- Add a dependency only if the task cannot be done without it, and justify it in the commit
  message.

Finish with exactly one JSON object:
{"status":"done|blocked","summary":"what you changed and why","assumptions":["..."],"followups":["..."]}

Put every idea you did not implement into `followups`. The planner reads them.
