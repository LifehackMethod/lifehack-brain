#!/bin/bash
# hook_swap.sh -- the ONLY sanctioned way to change a LIVE hook. Never patch a live hook in place.
#
# Usage: bash system/tools/hook_swap.sh [--live-dir DIR] [--no-test] <candidate-hook.sh>
#        bash system/tools/hook_swap.sh --help
#
# The candidate lives in a WORKTREE (<worktree>/system/hooks/<name>). This script:
#   1. refuses unless `bash -n` passes and the file has no conflict markers (^<<<<<<< ^======= ^>>>>>>>);
#   2. runs that hook's own test (<candidate dir>/tests/test_<name minus .sh>.sh) against the candidate;
#      no test file = refuse, unless you say --no-test (it prints that it was skipped);
#   3. keeps the CURRENT live file as a last-good copy: $LIFEHACK_HOOKS_LASTGOOD
#      (default ~/.local/state/lifehack/hooks-last-good)/<cksum of the live folder>/<name>.<UTC ts> -- only if the current file parses
#      (a broken file is never saved as "last good"); keeps the newest 10;
#   4. swaps atomically: temp file in the SAME directory as the live file, then mv.
# --live-dir defaults to $CLAUDE_PLUGIN_ROOT/system/hooks, else this script's own repo's system/hooks.
# Exit: 0 swapped | 1 refused (nothing changed) | 2 usage / cannot evaluate.
# Roll back by copying a hooks-last-good/<name>.<ts> file back the same way (or just: run the candidate = old file).
set -u
live="" ; notest=0
while [ $# -gt 0 ]; do
  case "$1" in
    --help|-h) sed -n '2,17p' "$0"; exit 0 ;;
    --live-dir) live="${2:-}"; shift 2 ;;
    --no-test) notest=1; shift ;;
    -*) echo "hook_swap: unknown option $1" >&2; exit 2 ;;
    *) break ;;
  esac
done
cand="${1:-}"
[ -n "$cand" ] && [ -f "$cand" ] || { echo "hook_swap: need a candidate hook file (see --help)" >&2; exit 2; }
cand="$(cd "$(dirname "$cand")" && pwd -P)/$(basename "$cand")"
name="$(basename "$cand")"
case "$name" in *.sh) ;; *) echo "hook_swap: candidate must be a .sh hook" >&2; exit 2 ;; esac
if [ -z "$live" ]; then
  if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then live="$CLAUDE_PLUGIN_ROOT/system/hooks"
  else live="$(cd "$(dirname "$0")/../hooks" && pwd)"; fi
fi
[ -d "$live" ] || { echo "hook_swap: live dir $live does not exist" >&2; exit 2; }
live="$(cd "$live" && pwd -P)"
target="$live/$name"
if [ "$cand" = "$target" ]; then echo "hook_swap: candidate IS the live file -- edit a copy in a worktree instead." >&2; exit 2; fi

REFUSE() { echo "hook_swap: REFUSED -- $1. Live file untouched." >&2; exit 1; }
bash -n "$cand" 2>/tmp/hook_swap_syntax.$$ || { e="$(head -3 /tmp/hook_swap_syntax.$$)"; rm -f /tmp/hook_swap_syntax.$$; REFUSE "candidate fails bash -n: $e"; }
rm -f /tmp/hook_swap_syntax.$$
grep -nE '^(<<<<<<<|=======$|>>>>>>>)' "$cand" >&2 && REFUSE "candidate contains conflict markers"

if [ "$notest" = 1 ]; then
  echo "hook_swap: WARNING tests skipped (--no-test)" >&2
else
  stem="${name%.sh}"; test_file="$(dirname "$cand")/tests/test_${stem}.sh"
  [ -f "$test_file" ] || REFUSE "no test at $test_file (write one, or pass --no-test and own it)"
  HOOK_UNDER_TEST="$cand" bash "$test_file" >/tmp/hook_swap_test.$$ 2>&1 || { tail -15 /tmp/hook_swap_test.$$ >&2; rm -f /tmp/hook_swap_test.$$; REFUSE "its test failed against the candidate"; }
  rm -f /tmp/hook_swap_test.$$
fi

lgbase="${LIFEHACK_HOOKS_LASTGOOD:-${LIFEHACK_STATE_DIR:-$HOME/.local/state/lifehack}/hooks-last-good}"
lg="$lgbase/$(printf '%s' "$live" | cksum | cut -d' ' -f1)"   # per live folder: same key hook_runner.sh uses, so copies never cross folders
ts="$(date -u +%Y%m%dT%H%M%SZ)"
if [ -f "$target" ]; then
  if bash -n "$target" 2>/dev/null && ! grep -qE '^(<<<<<<<|=======$|>>>>>>>)' "$target"; then
    (umask 077; mkdir -p "$lg") && chmod 700 "$lgbase" "$lg" && cp "$target" "$lg/.$name.$$" && mv -f "$lg/.$name.$$" "$lg/$name.$ts" || REFUSE "could not save last-good copy"
    echo "hook_swap: last-good kept: $lg/$name.$ts"
    ls -1r "$lg/$name".2* 2>/dev/null | tail -n +11 | while read -r old; do rm -f "$old"; done
  else
    echo "hook_swap: WARNING current live $name is itself broken; NOT saving it as last-good" >&2
  fi
fi
tmp="$live/.$name.swap.$$"
cp "$cand" "$tmp" && chmod 755 "$tmp" && mv -f "$tmp" "$target" || { rm -f "$tmp"; REFUSE "swap failed"; }
bash -n "$target" || { echo "hook_swap: FATAL post-swap parse failure on $target" >&2; exit 1; }
echo "hook_swap: swapped $name into $live"
exit 0
