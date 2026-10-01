# Retry parked T-0032 (G4 deploy files) as T-0035 with the reviewer's two fixes and rank it ahead of the G5 tasks

_Recorded 20260929-230036 by the NIGHTSHIFT planner._

## Context
T-0032 was parked after attempt 2. The reviewer accepted almost all of it but found two operational bugs. (1) The env example shipped `PENDEL_CHECK_LEAD_MIN=` empty, and src/pendel/scheduler.py:_lead_minutes_from_env falls back to the default only when the variable is None, so int('') crashes the scheduler into a restart loop. (2) DEPLOY.md put .pendel.env under /opt/dockerdata/pendel, but compose's `env_file: .pendel.env` resolves to deploy/.pendel.env, and /opt/dockerdata/pendel is the data volume mounted into both containers. No retry was in the backlog. The repo still has no Dockerfile, compose file, env example, workflow or DEPLOY.md. The backlog held only G5 tasks (T-0033, T-0034). The charter's priority is G1 > G3 > G2 > G4 > G5. G1 is still blocked on live-recording access (ADR 20260929-125118).

## Decision
Add T-0035 (G4/M4). It rebuilds the accepted T-0032 design and adds both fixes. Numeric and optional-channel vars ship commented out, never empty. The env file lives at deploy/.pendel.env (already gitignored by `.*.env`), outside the data volume. New stdlib tests guard both fixes, and the env-var coverage test includes PENDEL_RATE_LIMIT_PER_MIN, so it stays green whatever order T-0033 lands in. T-0035 touches no src/ file and so conflicts with neither T-0033 nor T-0034. The ordering is T-0035, then T-0033, then T-0034, which follows G4 > G5. The task fixes the env example rather than changing scheduler.py; that is the conservative choice, since it stays within G4's files and the reviewer offered it as a valid fix. T-0032 stays parked because IDs are never reused.

## Consequences
Once T-0035 lands, G4's files exist and are statically tested. `docker build .`, the container healthcheck and `docker compose config` stay unverified until a human runs them, because the NIGHTSHIFT guard blocks Docker. After that, G5's definition of done can be reached through T-0033 and T-0034. Still open and needing a human: live HAFAS recording access for G1 (T-0016/T-0017/T-0018/T-0020–T-0022), Docker verification for G4, and the deferred Telegram update poller.
