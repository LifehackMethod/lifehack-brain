#!/bin/bash
# test_numbers_mode.sh — the switch and the thing that reads it.
#
#   numbers_flag.sh                  arm / clear / status, and the TTL
#   inject_compute_mechanically.sh   the three arms, and the silence when none of them fire
#
# THE SILENCE IS THE HARD PART. This runs on every prompt of every session, so the case that
# matters most is the one where it prints NOTHING — a per-turn injector that speaks when it has no
# reason to becomes wallpaper, and wallpaper is what the rule it carries was already tried as and
# lost to (see the donor's own WHY block). Half the cases below assert an empty stdout.
#
# Run: bash system/hooks/tests/test_numbers_mode.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
FLAG_SH="$HOOKS/numbers_flag.sh"
INJ_SH="$HOOKS/inject_compute_mechanically.sh"
for h in "$FLAG_SH" "$INJ_SH"; do
  [ -f "$h" ] || { echo "CANNOT RUN: no script at $h"; exit 1; }
done

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/numbers.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
NOTES="$SANDBOX/notes"; mkdir -p "$NOTES/config" "$NOTES/desks/money" "$NOTES/desks/acting"
FAKEHOME="$SANDBOX/home"; mkdir -p "$FAKEHOME"

pass=0; fail=0
ok()   { pass=$((pass+1)); }
bad()  { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# Every call runs against the sandbox HOME so nothing touches the real ~/.claude/run — a test that
# quietly writes machine state is worse than no test, and this project has already been bitten by it
# once (the T2.7 drill found reader tests appending to a live pause list).
inject() { # inject <prompt> <cwd> [extra env...]
  local p="$1" c="$2"; shift 2
  python3 -c "
import json,sys
print(json.dumps({'prompt': sys.argv[1], 'cwd': sys.argv[2]}))" "$p" "$c" \
    | env HOME="$FAKEHOME" LIFEHACK_ROOT="$NOTES" "$@" bash "$INJ_SH" 2>/dev/null
}

echo "── numbers_flag: arm, status, clear ─────────────────────────────────────"
SID="sess-alpha"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$FLAG_SH" status)"
[ "$out" = "none" ] && ok || bad "status before arming" "expected 'none', got '$out'"
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$FLAG_SH" arm >/dev/null
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$FLAG_SH" status)"
[ "$out" = "armed" ] && ok || bad "status after arming" "expected 'armed', got '$out'"
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$FLAG_SH" clear >/dev/null
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$SID" bash "$FLAG_SH" status)"
[ "$out" = "none" ] && ok || bad "status after clearing" "expected 'none', got '$out'"

echo "   one session's flag is not another's"
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="sess-alpha" bash "$FLAG_SH" arm >/dev/null
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="sess-beta" bash "$FLAG_SH" status)"
[ "$out" = "none" ] && ok || bad "cross-session leak" "beta saw alpha's flag: '$out'"

echo "   and the TTL expires it rather than leaving it armed forever"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="sess-alpha" NUMBERS_TTL_HOURS=0 bash "$FLAG_SH" status)"
[ "$out" = "none" ] && ok || bad "TTL expiry" "expected 'none' at TTL 0, got '$out'"
# ...and expiring it must actually DELETE the flag, not merely report 'none' — otherwise the
# injector, which only checks that the file exists, would stay armed after the switch says it is off.
if [ -z "$(ls "$FAKEHOME/.claude/run/numbers/" 2>/dev/null)" ]; then ok
else bad "TTL removes the file" "status said 'none' but the flag file is still on disk — the injector reads the FILE"; fi

echo "   a bad verb is a usage error, not a silent success"
env HOME="$FAKEHOME" bash "$FLAG_SH" wibble >/dev/null 2>&1
[ "$?" = 2 ] && ok || bad "unknown verb" "expected exit 2"

echo "── the injector: silence when nothing armed it ───────────────────────────"
out="$(inject "how do I write a cover letter" "$NOTES/desks/acting")"
[ -z "$out" ] && ok || bad "quiet by default" "printed on an ordinary turn: $out"
out="$(inject "" "$NOTES")"
[ -z "$out" ] && ok || bad "empty prompt" "printed on an empty prompt: $out"
out="$(inject "we have 3 auditions and 2 callbacks this week" "$NOTES")"
[ -z "$out" ] && ok || bad "digits are not maths" "counting words tripped the backstop: $out"
out="$(inject "read version 2.0 of the file" "$NOTES")"
[ -z "$out" ] && ok || bad "a version number is not maths" "printed: $out"

echo "── arm 3: the backstop, on the shapes it is meant for ───────────────────"
for p in "can we cover the \$4200 rent" "that is a 30% cut" "what is 12 * 40"; do
  out="$(inject "$p" "$NOTES")"
  printf '%s' "$out" | grep -q "hard math token" && ok || bad "backstop: $p" "no injection"
done

echo "── arm 2: you said so ───────────────────────────────────────────────────"
env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="sess-armed" bash "$FLAG_SH" arm >/dev/null
out="$(inject "what should we do next" "$NOTES" CLAUDE_CODE_SESSION_ID=sess-armed)"
printf '%s' "$out" | grep -q "numbers-mode armed" && ok || bad "manual arm" "armed session got nothing"
out="$(inject "what should we do next" "$NOTES" CLAUDE_CODE_SESSION_ID=sess-other)"
[ -z "$out" ] && ok || bad "manual arm is per-session" "an unrelated session was armed too: $out"

echo "── arm 1: a folder the READER nominated, never one this repo named ──────"
# The donor hardcoded two of the author's desks here. These cases are the proof that shipped as
# nobody's list: with no file, no folder arms — and that is the state a new install is in.
out="$(inject "what should we do next" "$NOTES/desks/money")"
[ -z "$out" ] && ok || bad "no list, no auto-arm" "a folder armed itself with no list on disk: $out"
printf 'money\n' > "$NOTES/config/numbers-auto-arm"
out="$(inject "what should we do next" "$NOTES/desks/money")"
printf '%s' "$out" | grep -q "the money folder is on your list" && ok || bad "listed folder arms" "got: $out"
out="$(inject "what should we do next" "$NOTES/desks/acting")"
[ -z "$out" ] && ok || bad "unlisted folder stays quiet" "acting armed off someone else's line: $out"

echo "   the match is the whole line, so a prefix is not a member"
printf 'money\n' > "$NOTES/config/numbers-auto-arm"
mkdir -p "$NOTES/desks/moneyball"
out="$(inject "what should we do next" "$NOTES/desks/moneyball")"
[ -z "$out" ] && ok || bad "prefix match" "'moneyball' matched the line 'money': $out"

echo "   comments and blank lines are not folder names"
printf '# my subjects\n\n  acting  \n' > "$NOTES/config/numbers-auto-arm"
out="$(inject "what should we do next" "$NOTES/desks/acting")"
printf '%s' "$out" | grep -q "on your list" && ok || bad "surrounding whitespace" "a padded line did not match: $out"
mkdir -p "$NOTES/desks/# my subjects"
out="$(inject "what should we do next" "$NOTES/desks/# my subjects")"
[ -z "$out" ] && ok || bad "comment line" "a comment was read as a folder name: $out"

echo "   and with no notes root at all it stays quiet rather than guessing"
out="$(python3 -c "
import json
print(json.dumps({'prompt':'what next','cwd':'$NOTES/desks/money'}))" \
  | env HOME="$FAKEHOME" LIFEHACK_ROOT="" bash "$INJ_SH" 2>/dev/null)"
[ -z "$out" ] && ok || bad "no notes root" "printed with nothing resolved: $out"

echo "── the text it injects actually carries the rule ─────────────────────────"
out="$(inject "can we cover the \$4200 rent" "$NOTES")"
printf '%s' "$out" | grep -q "not typed by the person" && ok || bad "injection is labelled" "the model could read it as user input"
printf '%s' "$out" | grep -qi "show the expression" && ok || bad "the checkable half" "no instruction to show the working"
printf '%s' "$out" | grep -qi "work backwards" && ok || bad "the back-solve half" "no instruction against bending the input"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "NUMBERS MODE GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1; fi
