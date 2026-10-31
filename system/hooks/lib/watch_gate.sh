# watch_gate.sh -- sourced near the top of every SWITCHED guard (Round D B.5). Usage:  watch_gate <this-script-name> [--shadow-only]
# NOT watch mode (default off in code; a ROUNDB_* variable in the environment also means "not watch" unless LIFEHACK_WATCH=1; roundB.conf `mode=watch` or env LIFEHACK_WATCH=1 turns it on, LIFEHACK_WATCH=0 forces it off): returns at once, the guard runs as normal.
# WATCH mode: re-executes the guard through lib/watch_run.py, which runs it as a shadow (switches as configured, no state written) and for real
#   (every switch forced off), logs any difference to ~/.claude/run/watch/watch-log.jsonl and hands the harness the all-off result. Blocks and asks nothing new.
watch_gate() {
  [ -n "${LHB_WATCH_CHILD:-}" ] && return 0
  local w="${LIFEHACK_WATCH:-}" d
  d="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  if [ -z "$w" ]; then
    # a ROUNDB_* variable in the environment means a test or replay run that chose its switches on purpose: the conf line does not turn watch on there
    env | grep -q '^ROUNDB_' && return 0
    [ "$(sed -n 's/^mode=//p' "$d/roundB.conf" 2>/dev/null | tail -1 | tr -d '[:space:]')" = "watch" ] && w=1
  fi
  [ "$w" = "1" ] || return 0
  # nothing switched on (conf or env) = nothing to watch: skip the extra process
  grep -qE '^[a-z0-9_]+=on[[:space:]]*$' "$d/roundB.conf" 2>/dev/null || env | grep -q '^ROUNDB_[A-Z0-9_]*=on' || return 0
  [ -f "$d/lib/watch_run.py" ] || return 0
  # FAIL-OPEN FOR THE WATCHER ONLY: the watcher hands its result back through files; if it crashes, never starts, or leaves no `done` file, the REAL
  # hook below this call runs normally (enforce behaviour) with its stdin restored. A fine-china guard must never be skipped by a watcher fault.
  local t; t="$(mktemp -d 2>/dev/null)" || return 0
  cat > "$t/in" 2>/dev/null || { exec 0< /dev/null; return 0; }
  LHB_WATCH_OUT="$t" python3 "$d/lib/watch_run.py" "$@" < "$t/in" >/dev/null 2>"$t/crash"
  if [ -f "$t/done" ] && [ -f "$t/rc" ]; then
    cat "$t/out" 2>/dev/null; cat "$t/err" >&2 2>/dev/null
    local rc; rc="$(cat "$t/rc" 2>/dev/null)"; rm -rf "$t"
    trap - EXIT; exit "${rc:-0}"
  fi
  cat "$t/crash" >&2 2>/dev/null; echo "watch_gate: watcher failed; running the real hook normally" >&2
  exec 0< "$t/in"; rm -rf "$t"   # stdin reopened from the saved payload (the open handle survives the delete)
  return 0
}
