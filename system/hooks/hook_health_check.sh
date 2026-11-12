#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "hook_health_check.sh" "SessionStart" "" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: hook_runner.sh quietly restores a broken hook from a known-good copy. Quiet is dangerous twice over:
#      (1) the restore can silently revert a TRACKED file in a git clone, and a later commit then carries
#      the reversion; (2) the runner is itself one file -- if it is deleted or gets a syntax error nobody
#      is told, because the registered commands fall back to running the real hooks directly.
# GUARDS: nothing. SessionStart is structurally non-blocking; this only INFORMS (stdout + exit 0).
# DOES: (1) `bash -n` on hook_runner.sh -> LOUD notice + alert file if missing or broken.
#      (2) If ~/.local/state/lifehack/hooks-alert.json exists (written by hook_runner.sh on a restore or a
#      fail-closed, or by a registered command's runner-unavailable fallback) print it at the top of the
#      session UNTIL it is acknowledged: `bash system/tools/hook_alert_ack.sh`.
# REDIRECT: n/a -- nothing is refused. To clear the notice, find out what broke the hook, then acknowledge.
# SIGNPOST: system/sops/hook-sop.md section 6; system/hooks/hook_runner.sh; system/tools/hook_register.py.
# FAIL_POSTURE: open, deliberately. Every path exits 0: a session that cannot be told must still start.
# UPDATED: 2026-11-12
# ─────────────────────────────────────────────────────────────────────────────
set +e
cat >/dev/null 2>&1   # allow-silence: draining an unused stdin; a failure here changes nothing
dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P)"
st="${LIFEHACK_STATE_DIR:-$HOME/.local/state/lifehack}"
runner="$dir/hook_runner.sh"
if [ ! -r "$runner" ] || ! bash -n "$runner" 2>/dev/null; then
  why="hook_runner.sh ($runner) is missing, unreadable or fails bash -n"
  { mkdir -p "$st" && printf '{"alert":"hook-runner-broken","what":"%s","at":"%s"}\n' "$why" "$(date -u +%Y%m%dT%H%M%SZ)" > "$st/hooks-alert.json"; } || echo "hook_health_check: could not write $st/hooks-alert.json" >&2
  printf '=== HOOK ALERT: %s. Every PreToolUse hook is running directly with NO last-good protection until it is repaired (git checkout -- system/hooks/hook_runner.sh). ===\n' "$why"
fi
if [ -s "$st/hooks-alert.json" ]; then
  printf '=== HOOK ALERT (unacknowledged) -- a hook was restored or could not run. A tracked file may now differ from your last commit; check `git status` in the hooks folder before committing. ===\n'
  cat "$st/hooks-alert.json" 2>/dev/null
  printf '=== Acknowledge once you know what broke it: bash %s/../tools/hook_alert_ack.sh ===\n' "$dir"
fi
exit 0
