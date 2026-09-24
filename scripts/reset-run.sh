#!/usr/bin/env bash
# Clear the runtime state of a finished NIGHTSHIFT run so a new charter can be armed.
#
# The plan, the transcripts and the agent worktrees of one run are disposable once the
# run is archived under charters/ and its branches are out of the sandbox. The bare
# repos are kept by default: they are the expensive part to rebuild and `arm` requires
# one per charter project. Pass --repos to drop them too.
#
# Usage: scripts/reset-run.sh [--repos] [--dry-run]
set -euo pipefail

cd "$(dirname "$0")/.."
DATA=data
repos=0; dry=0
for a in "$@"; do
  case "$a" in
    --repos) repos=1 ;;
    --dry-run) dry=1 ;;
    *) echo "usage: $0 [--repos] [--dry-run]" >&2; exit 2 ;;
  esac
done

# 1. The loop must not be mid-task, or a worktree is pulled out from under an agent.
if [ -f "$DATA/state/state.json" ]; then
  current=$(python3 -c "import json;print(json.load(open('$DATA/state/state.json')).get('current_task') or '')")
  if [ -n "$current" ]; then
    echo "refusing: task $current is in flight. touch $DATA/STOP, wait for it to finish, then retry." >&2
    exit 1
  fi
fi
if [ ! -f "$DATA/STOP" ] && docker compose ps --status running --services 2>/dev/null | grep -q orchestrator; then
  echo "refusing: orchestrator is running without the kill switch. touch $DATA/STOP first." >&2
  exit 1
fi

# 2. The charter being cleared must already be archived, or the run's reasoning is lost.
if [ -f "$DATA/plan/CHARTER.md" ]; then
  sum=$(sha256sum <"$DATA/plan/CHARTER.md" | cut -d' ' -f1)
  if ! find charters -name CHARTER.md -exec sha256sum {} + 2>/dev/null | grep -q "$sum"; then
    echo "refusing: $DATA/plan/CHARTER.md is not archived under charters/." >&2
    echo "copy the charter, roadmap, plan/{done,parked,decisions} and digests there first." >&2
    exit 1
  fi
fi

targets=(
  "$DATA/work" "$DATA/logs" "$DATA/digests" "$DATA/backup" "$DATA/state"
  "$DATA/plan/backlog" "$DATA/plan/done" "$DATA/plan/parked" "$DATA/plan/decisions"
  "$DATA/plan/CHARTER.md" "$DATA/plan/ROADMAP.md" "$DATA/STOP"
)
[ "$repos" = 1 ] && targets+=("$DATA/repos")

for t in "${targets[@]}"; do
  [ -e "$t" ] || continue
  if [ "$dry" = 1 ]; then
    echo "would remove $t ($(du -sh "$t" | cut -f1))"
  else
    rm -rf "$t"
  fi
done
[ "$dry" = 1 ] && exit 0

mkdir -p "$DATA"/{work,logs,digests,backup,state,repos} \
         "$DATA"/plan/{backlog,done,parked,decisions}

cat <<'EOF'
runtime cleared. To arm the next run:

  1. write data/plan/CHARTER.md (goals G1.., non-goals, constraints, definition of
     done, priority order, and a "## Projects" line per repo) and data/plan/ROADMAP.md
  2. per project, seed the bare repo the agents work in:
       git clone --bare ~/coding/<repo> data/repos/<repo>.git
       git -C data/repos/<repo>.git symbolic-ref HEAD refs/heads/main
  3. docker compose up -d
     docker compose exec orchestrator python3 /app/nightshift.py selftest
     docker compose exec orchestrator python3 /app/nightshift.py arm
EOF
