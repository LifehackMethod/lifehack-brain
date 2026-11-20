#!/bin/bash
# test_delegation_override.sh — inject_delegation_standing.sh honors an operator override file.
# Cases: no file -> default text; non-empty file -> its text instead; empty/whitespace file -> default.
# Run: bash system/hooks/tests/test_delegation_override.sh   (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
I="$HOOKS/inject_delegation_standing.sh"
[ -f "$I" ] || { echo "CANNOT RUN: no hook at $I"; exit 1; }
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
SB="$(mktemp -d)"; trap 'rm -rf "$SB"' EXIT
run() { printf '{}' | env HOME="$SB/fakehome" LIFEHACK_DELEGATION_OVERRIDE="$1" bash "$I" 2>/dev/null; }

OUT=$(run "$SB/missing.txt"); RC=$?
[ "$RC" = 0 ] && ok || bad "no file: exit 0" "rc=$RC"
case "$OUT" in *"Sub-agent delegation IS user-requested"*) ok ;; *) bad "no file: default text" "got: $OUT" ;; esac

printf 'CUSTOM POLICY LINE\n' > "$SB/o.txt"
OUT=$(run "$SB/o.txt"); RC=$?
[ "$RC" = 0 ] && ok || bad "file: exit 0" "rc=$RC"
[ "$OUT" = "CUSTOM POLICY LINE" ] && ok || bad "file: override text only" "got: $OUT"

: > "$SB/empty.txt"
OUT=$(run "$SB/empty.txt")
case "$OUT" in *"Sub-agent delegation IS user-requested"*) ok ;; *) bad "empty file: default text" "got: $OUT" ;; esac
printf '  \n\n' > "$SB/ws.txt"
OUT=$(run "$SB/ws.txt")
case "$OUT" in *"Sub-agent delegation IS user-requested"*) ok ;; *) bad "whitespace file: default text" "got: $OUT" ;; esac

# default path under HOME is used when the env var is unset
mkdir -p "$SB/fakehome/.config/lifehack"; printf 'HOME PATH OVERRIDE\n' > "$SB/fakehome/.config/lifehack/delegation-override.txt"
OUT=$(printf '{}' | env -u LIFEHACK_DELEGATION_OVERRIDE HOME="$SB/fakehome" bash "$I" 2>/dev/null)
[ "$OUT" = "HOME PATH OVERRIDE" ] && ok || bad "default path under HOME" "got: $OUT"

echo "pass=$pass fail=$fail"; [ "$fail" = 0 ]
