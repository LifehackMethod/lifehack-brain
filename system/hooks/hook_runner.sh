#!/bin/bash
# hook_runner.sh <hook-file> [args...] -- the tiny wrapper every PreToolUse hook is launched through.
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: a live hook that cannot even PARSE (a half-applied patch left conflict markers in
#      ingest_gate_enforce.sh, 2026-11-12) exits 2 on every call; for PreToolUse exit 2 means
#      "block", so every tool in every window was blocked -- including the tools needed to fix it.
# DOES: (1) bash -n + conflict-marker check on the target. (2) Good -> snapshot it as a last-good copy
#      if its content changed, then `exec bash <hook>` with stdin untouched. (3) Broken -> quarantine
#      the broken file, restore the newest last-good copy that itself passes the check, log LOUDLY,
#      run the restored hook. (4) Broken/missing and NO good copy -> exit 2: FAIL CLOSED.
# FAIL_POSTURE: closed. This wrapper only ever turns "hook cannot parse" into "last parseable version of
#      that same hook runs". It never skips, downgrades or replaces a gate with anything else.
#      A missing hook file is also closed (a missing file otherwise exits 127 = non-blocking = OPEN).
# SIGNPOST: copies come from system/tools/hook_swap.sh and from this wrapper's own snapshots. Rules:
#      system/sops/hook-sop.md section 6. Keep this file TINY; it has its own test.
# ─────────────────────────────────────────────────────────────────────────────
name="${1:-}"; [ $# -gt 0 ] && shift
case "$name" in ""|*/*|.*) echo "BLOCKED: hook_runner.sh needs a bare hook file name, got '$name' -- failing CLOSED." >&2; exit 2;; esac
src="${BASH_SOURCE[0]}"; dir="${src%/*}"; [ "$dir" = "$src" ] && dir=.
t="$dir/$name"
st="${LIFEHACK_STATE_DIR:-$HOME/.local/state/lifehack}"; lg="${LIFEHACK_HOOKS_LASTGOOD:-$st/hooks-last-good}"
ts="$(date -u +%Y%m%dT%H%M%SZ)"
good() { [ -f "$1" ] && bash -n "$1" 2>/dev/null && ! grep -qE '^(<<<<<<<|=======$|>>>>>>>)' "$1"; }
if good "$t"; then
  new="$(ls -1r "$lg/$name".2* 2>/dev/null | head -1)"
  if [ -z "$new" ] || ! cmp -s "$t" "$new"; then
    { mkdir -p "$lg" && cp "$t" "$lg/.$name.$$" && mv -f "$lg/.$name.$$" "$lg/$name.$ts"; } 2>/dev/null || true
  fi
  exec bash "$t" "$@"
fi
alert() { { mkdir -p "$st"; echo "$ts $1" >> "$st/hooks-alerts.log"; printf '{"alert":"hook-runner","hook":"%s","at":"%s","what":"%s"}\n' "$name" "$ts" "$1" > "$st/hooks-alert.json"; } 2>/dev/null; echo "HOOK-RUNNER ALERT: $1" >&2; }
for c in $(ls -1r "$lg/$name".2* 2>/dev/null); do
  good "$c" || continue
  { [ -f "$t" ] && mkdir -p "$lg" && cp "$t" "$lg/$name.broken.$ts"; } 2>/dev/null
  if cp "$c" "$dir/.$name.restore.$$" 2>/dev/null && mv -f "$dir/.$name.restore.$$" "$t" 2>/dev/null; then
    alert "$name could not parse; RESTORED from last-good ${c##*/} (broken copy kept as $name.broken.$ts). Find out what broke it."
    exec bash "$t" "$@"
  fi
  rm -f "$dir/.$name.restore.$$" 2>/dev/null
  break
done
alert "$name cannot run (syntax error / conflict markers / missing) and NO usable last-good copy exists -- FAILING CLOSED. Restore it from a terminal: git checkout -- system/hooks/$name"
exit 2
