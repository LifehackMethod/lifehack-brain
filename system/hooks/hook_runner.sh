#!/bin/bash
# hook_runner.sh <hook-file> [args...] -- the tiny wrapper every PreToolUse hook is launched through.
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: a live hook that cannot even PARSE (a half-applied patch left conflict markers in
#      ingest_gate_enforce.sh, 2026-11-12) exits 2 on every call; for PreToolUse exit 2 means
#      "block", so every tool in every window was blocked -- including the tools needed to fix it.
# DOES: (1) bash -n + conflict-marker check on the target. (2) Good -> snapshot it as a last-good copy
#      if its content changed (store is PER HOOKS FOLDER, newest 10 kept), then `exec bash <hook>` with
#      stdin untouched. (3) Broken -> quarantine the broken file, restore a known-good copy (git HEAD of
#      THIS folder first, else the newest last-good copy saved from THIS SAME folder, never one dated in
#      the future), log LOUDLY (hooks-alert.json is shown at the next session start until acknowledged),
#      run the restored hook. (4) Broken/missing and NO good copy -> exit 2: FAIL CLOSED.
# FAIL_POSTURE: closed. This wrapper only ever turns "hook cannot parse" into "last parseable version of
#      that same hook, from that same folder, runs". It never skips, downgrades or replaces a gate with
#      anything else. A missing hook file is also closed (a missing file otherwise exits 127 = OPEN).
#      If THIS file is missing or broken, every registered command falls back to running the real hook
#      directly (see system/tools/hook_register.py) -- the runner is never a single point of failure.
# SIGNPOST: copies come from system/tools/hook_swap.sh and from this wrapper's own snapshots. Rules:
#      system/sops/hook-sop.md section 6. Keep this file SMALL; it has its own test.
# ─────────────────────────────────────────────────────────────────────────────
name="${1:-}"; [ $# -gt 0 ] && shift
case "$name" in ""|*/*|.*) echo "BLOCKED: hook_runner.sh needs a bare hook file name, got '$name' -- failing CLOSED." >&2; exit 2;; esac
src="${BASH_SOURCE[0]}"; dir="${src%/*}"; [ "$dir" = "$src" ] && dir=.
dir="$(cd "$dir" 2>/dev/null && pwd -P)" || { echo "BLOCKED: hook_runner.sh cannot resolve its own folder -- failing CLOSED." >&2; exit 2; }
t="$dir/$name"
st="${LIFEHACK_STATE_DIR:-$HOME/.local/state/lifehack}"; base="${LIFEHACK_HOOKS_LASTGOOD:-$st/hooks-last-good}"
lg="$base/$(printf '%s' "$dir" | cksum | cut -d' ' -f1)"   # one store per real hooks folder: a copy never crosses folders
ts="$(date -u +%Y%m%dT%H%M%SZ)"
good() { [ -f "$1" ] && bash -n "$1" 2>/dev/null && ! grep -qE '^(<<<<<<<|=======$|>>>>>>>)' "$1"; }
if good "$t"; then
  new="$(ls -1t "$lg/$name".2* 2>/dev/null | head -1)"
  if [ -z "$new" ] || ! cmp -s "$t" "$new"; then
    { umask 077; mkdir -p "$lg" && chmod 700 "$base" "$lg" && cp "$t" "$lg/.$name.$$" && mv -f "$lg/.$name.$$" "$lg/$name.$ts" \
      && ls -1t "$lg/$name".2* | tail -n +11 | while IFS= read -r o; do rm -f "$o"; done; } 2>/dev/null || true
  fi
  exec bash "$t" "$@"
fi
alert() { { mkdir -p "$st"; echo "$ts $1" >> "$st/hooks-alerts.log"; printf '{"alert":"hook-runner","hook":"%s","folder":"%s","at":"%s","what":"%s"}\n' "$name" "$dir" "$ts" "$1" > "$st/hooks-alert.json"; } 2>/dev/null; echo "HOOK-RUNNER ALERT: $1" >&2; }
tmp="$dir/.$name.restore.$$"; from=""
if command -v git >/dev/null 2>&1 && git -C "$dir" show "HEAD:./$name" > "$tmp" 2>/dev/null && good "$tmp"; then from="git HEAD"; fi
if [ -z "$from" ]; then
  while IFS= read -r c; do
    cts="${c##*.}"; [[ "$cts" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] && [[ ! "$cts" > "$ts" ]] && good "$c" && cp "$c" "$tmp" 2>/dev/null && { from="last-good ${c##*/}"; break; }
  done < <(ls -1t "$lg/$name".2* 2>/dev/null)
fi
if [ -n "$from" ]; then
  { [ -f "$t" ] && umask 077 && mkdir -p "$lg" && cp "$t" "$lg/$name.broken.$ts"; } 2>/dev/null
  if chmod 755 "$tmp" 2>/dev/null && mv -f "$tmp" "$t" 2>/dev/null; then
    ls -1t "$lg/$name".broken.* 2>/dev/null | tail -n +6 | while IFS= read -r o; do rm -f "$o"; done
    alert "$name could not parse; RESTORED from $from (broken copy kept as $lg/$name.broken.$ts). A tracked file may now differ from your last commit -- find out what broke it."
    exec bash "$t" "$@"
  fi
fi
rm -f "$tmp" 2>/dev/null
alert "$name cannot run (syntax error / conflict markers / missing) and NO usable good copy exists -- FAILING CLOSED. Restore it from a terminal: git checkout -- system/hooks/$name"
exit 2
