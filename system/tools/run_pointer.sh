#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: /next and /back must work from a window whose cwd is not the run folder (SB-10, first live
#      run 2026-11-24). The runner's `start` records WHERE the run folder is, per session, so the
#      mover (system/hooks/run_step_hook.sh) can find the run when the window's cwd has no marker.
# GUARDS: none — a tiny state writer over the shared switch library system/hooks/lib/flag.sh.
#      Session-scoped + machine-local (CLAUDE_CODE_SESSION_ID; cwd-hash fallback), TTL 24h.
# REDIRECT: flag ~/.claude/run/runptr/runptr-sess-<id>.flag. Writer: the runner's `start`.
#      Reader: run_step_hook.sh. Off: `clear`, or the TTL.
# SIGNPOST: key derivation, TTL and sweep live in system/hooks/lib/flag.sh. Never a second mover.
# UPDATED: 2026-11-25 (new, SB-10)
# ─────────────────────────────────────────────────────────────────────────────
#   run_pointer.sh set <abs_workdir>   # record the run folder for this session
#   run_pointer.sh get                 # print the recorded run folder, or nothing
#   run_pointer.sh clear               # forget it (this session)
set +e
_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
_LIB="$_SELF_DIR/../hooks/lib/flag.sh"
[ -f "$_LIB" ] || { echo "run_pointer.sh: FATAL — shared library missing at $_LIB" >&2; exit 1; }
. "$_LIB" || { echo "run_pointer.sh: FATAL — shared library failed to load" >&2; exit 1; }
for _fn in flag_init flag_write flag_get flag_ttl_expired flag_clear_sweep; do
  command -v "$_fn" >/dev/null 2>&1 || { echo "run_pointer.sh: FATAL — library missing $_fn()" >&2; exit 1; }
done
TTL_HOURS="${RUNPTR_TTL_HOURS:-24}"
flag_init runptr runptr
case "$1" in
  set)
    [ -n "$2" ] && [ -d "$2" ] || { echo "set: an existing <abs_workdir> is required" >&2; exit 1; }
    flag_write "workdir=$2" "armed_at=$NOW" "cwd=$PWD" "session=$CLAUDE_CODE_SESSION_ID"
    echo "RUN POINTER SET: $2 (session ${CLAUDE_CODE_SESSION_ID:-none})";;
  get)
    if [ -f "$FLAG" ] && ! flag_ttl_expired $(( TTL_HOURS * 3600 )); then flag_get workdir; fi;;
  clear)
    echo "RUN POINTER CLEARED ($(flag_clear_sweep runptr))";;
  *) echo "usage: run_pointer.sh set <abs_workdir> | get | clear" >&2; exit 2;;
esac
exit 0
