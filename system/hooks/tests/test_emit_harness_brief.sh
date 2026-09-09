#!/bin/bash
# Suite for system/hooks/emit_harness_brief.sh — the SessionStart hook that delivers the plugin's
# own standing brief. EMIT cases come first (hook-sop.md's "ALLOW cases first" rule: the common,
# correct path is what a reader should see before the refusals).
#
# ⛔ WHY THIS SUITE EXISTS AT ALL: the private predecessor of this hook read a HARDCODED repo path
# and went silently dark the day that path was deleted — no error, no output, and nobody noticed
# for hours. Every case below therefore asserts on OUTPUT, never on exit code alone: this hook's
# exit code is 0 on every path by design, so an exit-code test would pass on a hook that emits
# nothing. That is exactly the failure being guarded against.

set -uo pipefail
HOOK="$(cd "$(dirname "$0")/.." && pwd)/emit_harness_brief.sh"
PASS=0; FAIL=0
ok(){ printf '  PASS  %s\n' "$1"; PASS=$((PASS+1)); }
no(){ printf '  FAIL  %s\n' "$1"; printf '        %s\n' "$2"; FAIL=$((FAIL+1)); }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
ROOT="$TMP/plugin"; mkdir -p "$ROOT"
printf '# The Harness Brief\nline two\n' > "$ROOT/CLAUDE.md"
WORK="$TMP/work"; mkdir -p "$WORK"

run(){ ( cd "$1" && CLAUDE_PLUGIN_ROOT="${2-}" bash "$HOOK" </dev/null 2>/dev/null ); }

echo "EMIT cases —"

out="$(run "$WORK" "$ROOT")"
case "$out" in *"The Harness Brief"*) ok "emits the brief in an ordinary folder" ;;
  *) no "emits the brief in an ordinary folder" "got: ${out:-<empty>}" ;; esac

printf '# Some other project entirely\n' > "$WORK/CLAUDE.md"
out="$(run "$WORK" "$ROOT")"
case "$out" in *"The Harness Brief"*) ok "still emits when the folder has a DIFFERENT CLAUDE.md" ;;
  *) no "still emits when the folder has a DIFFERENT CLAUDE.md" "got: ${out:-<empty>}" ;; esac
rm -f "$WORK/CLAUDE.md"

echo "SUPPRESS cases —"

cp "$ROOT/CLAUDE.md" "$WORK/CLAUDE.md"
out="$(run "$WORK" "$ROOT")"
[ -z "$out" ] && ok "silent when an IDENTICAL brief is already auto-loaded here" \
  || no "silent when an IDENTICAL brief is already auto-loaded here" "expected nothing, got: $out"

mkdir -p "$WORK/nested/deeper"
out="$(run "$WORK/nested/deeper" "$ROOT")"
[ -z "$out" ] && ok "silent when the identical brief sits in an ANCESTOR folder" \
  || no "silent when the identical brief sits in an ANCESTOR folder" "expected nothing, got: $out"
rm -rf "$WORK/nested"; rm -f "$WORK/CLAUDE.md"

echo "FAIL-OPEN cases — every one must be silent AND exit 0"

out="$(run "$WORK" "")"; rc=$?
{ [ -z "$out" ] && [ "$rc" = 0 ]; } && ok "CLAUDE_PLUGIN_ROOT unset: silent, exit 0" \
  || no "CLAUDE_PLUGIN_ROOT unset: silent, exit 0" "out='${out}' rc=$rc"

out="$(run "$WORK" "$TMP/does-not-exist")"; rc=$?
{ [ -z "$out" ] && [ "$rc" = 0 ]; } && ok "plugin root missing: silent, exit 0" \
  || no "plugin root missing: silent, exit 0" "out='${out}' rc=$rc"

mkdir -p "$TMP/nobrief"
out="$(run "$WORK" "$TMP/nobrief")"; rc=$?
{ [ -z "$out" ] && [ "$rc" = 0 ]; } && ok "brief file absent: silent, exit 0" \
  || no "brief file absent: silent, exit 0" "out='${out}' rc=$rc"

echo
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
