#!/bin/bash
# test_fire_journal_decision.sh -- the fire journal records a PreToolUse hook's REAL decision.
# WHY: an ask hook exits 0, so lib/journal.sh (which only sees the exit code) wrote every ask as "allow":
#      15,413 journal rows, not one "ask". The trial's daily read needs asks counted as asks.
# FIX UNDER TEST: an ask emitter also writes its decision JSON to $LHB_JOURNAL_NOTE (lib/journal_note.py, or
#      lhb_journal_note in lib/journal.sh); the EXIT trap parses it: ask / allow / deny / unknown.
# Cases: fixture hooks (ask, allow, explicit allow JSON, exit-2 deny, JSON block, JSON deny, unparseable), the real ask
#      hooks (cloud, sheet, drive) through their registered entry points, stdout byte-identical journal on vs off,
#      the note is consumed, and every ask emitter in system/hooks writes a note (drift check).
# Run: bash system/hooks/tests/test_fire_journal_decision.sh   (exit 0 = all pass)
HERE="$(cd "$(dirname "$0")" && pwd)"; HOOKS="$(cd "$HERE/.." && pwd)"; LIB="$HOOKS/lib/journal.sh"
. "$HERE/pin_roundb_off.sh"
S="$(mktemp -d "${TMPDIR:-/tmp}/fjd.XXXXXX")"; trap 'rm -rf "$S"' EXIT  # guaranteed cleanup: leaked test temp dirs filled a disk, 2026-11-01
mkdir -p "$S/home" "$S/fx" "$S/run"
export HOME="$S/home"
unset LHB_JOURNAL_DISABLE LHB_JOURNAL_NOTE
P=0; F=0
ok() { P=$((P+1)); [ -n "${VERBOSE:-}" ] && echo "PASS $1"; return 0; }
bad() { F=$((F+1)); echo "FAIL: $1"; }

# last_decision <journal>: the decision field of the journal's last line ("" if none)
last_decision() { python3 -c 'import json,sys
ls=[l for l in open(sys.argv[1]) if l.strip()] if __import__("os").path.exists(sys.argv[1]) else []
print(json.loads(ls[-1]).get("decision","") if ls else "")' "$1" 2>/dev/null; }
last_rc() { python3 -c 'import json,sys; ls=[l for l in open(sys.argv[1]) if l.strip()]; print(json.loads(ls[-1]).get("exit_code",""))' "$1" 2>/dev/null; }

# fixture <name> <body>: a hook using the real two-line caller pattern, then <body>
fixture() {
  { printf '#!/bin/bash\n'
    printf '. "%s" 2>/dev/null || lhb_journal_fire() { :; }\n' "$LIB"
    printf 'trap '"'"'lhb_journal_fire "$?" "%s" "PreToolUse" "Bash" 2>/dev/null || true'"'"' EXIT\n' "$1"
    printf 'cat >/dev/null\n'
    printf '%s\n' "$2"; } > "$S/fx/$1"
}
# expect <label> <hook-path> <want-decision> [stdin]
expect() {
  local j="$S/run/$RANDOM$RANDOM.jsonl" got rc
  printf '%s' "${4:-{\}}" | LHB_JOURNAL_PATH="$j" bash "$2" >"$S/out" 2>"$S/err"; rc=$?
  got="$(last_decision "$j")"
  if [ "$got" = "$3" ]; then ok "$1"; else bad "$1: journal decision '$got', want '$3' (rc=$rc out=$(head -c 160 "$S/out") err=$(head -c 160 "$S/err"))"; fi
  [ -n "$got" ] && [ "$(last_rc "$j")" != "$rc" ] && bad "$1: journal exit_code $(last_rc "$j") != real rc $rc"
  ls -a "$S/run" | grep -q '^\.fire-note\.' && bad "$1: a .fire-note file was left behind" && mv "$S/run"/.fire-note.* "$S/" 2>/dev/null
  return 0
}

ASKJ='{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": "ASK FIRST (fixture)"}}'
ALLOWJ='{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": "notice"}}'
DENYJ='{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "no"}}'
BLOCKJ='{"decision":"block","reason":"BLOCKED: fixture"}'

echo "── fixtures: allow cases first ──"
fixture allow.sh 'exit 0'
expect "plain exit 0 -> allow" "$S/fx/allow.sh" allow
fixture allow_json.sh "printf '%s\n' '$ALLOWJ'; lhb_journal_note '$ALLOWJ' 2>/dev/null; exit 0"
expect "permissionDecision allow + additionalContext -> allow" "$S/fx/allow_json.sh" allow
fixture ctx_only.sh "J='{\"hookSpecificOutput\": {\"hookEventName\": \"PreToolUse\", \"additionalContext\": \"advisory\"}}'; printf '%s\n' \"\$J\"; lhb_journal_note \"\$J\" 2>/dev/null; exit 0"
expect "JSON with no decision key (advisory only) -> allow" "$S/fx/ctx_only.sh" allow

echo "── fixtures: ask / deny / block / unparseable ──"
fixture ask.sh "printf '%s\n' '$ASKJ'; lhb_journal_note '$ASKJ' 2>/dev/null; exit 0"
expect "permissionDecision ask, exit 0 -> ask" "$S/fx/ask.sh" ask
fixture deny2.sh "echo 'BLOCKED: fixture' >&2; exit 2"
expect "exit 2 -> deny" "$S/fx/deny2.sh" deny
fixture deny2_note.sh "printf '%s\n' '$ASKJ'; lhb_journal_note '$ASKJ' 2>/dev/null; echo 'BLOCKED' >&2; exit 2"
expect "exit 2 wins over an ask note -> deny" "$S/fx/deny2_note.sh" deny
fixture block_json.sh "printf '%s\n' '$BLOCKJ'; lhb_journal_note '$BLOCKJ' 2>/dev/null; exit 0"
expect "decision block JSON on stdout, exit 0 -> deny" "$S/fx/block_json.sh" deny
fixture deny_json.sh "printf '%s\n' '$DENYJ'; lhb_journal_note '$DENYJ' 2>/dev/null; exit 0"
expect "permissionDecision deny, exit 0 -> deny" "$S/fx/deny_json.sh" deny
fixture garbage.sh "echo 'not json {at all'; lhb_journal_note 'not json {at all' 2>/dev/null; exit 0"
expect "unparseable decision output -> unknown" "$S/fx/garbage.sh" unknown
fixture odd.sh "J='{\"hookSpecificOutput\": {\"permissionDecision\": \"maybe\"}}'; printf '%s\n' \"\$J\"; lhb_journal_note \"\$J\" 2>/dev/null; exit 0"
expect "unrecognised permissionDecision value -> unknown" "$S/fx/odd.sh" unknown
fixture py_ask.sh "python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); s=sys.argv[2]; print(s)
import journal_note; journal_note.note(s)' '$HOOKS/lib' '$ASKJ'; exit 0"
expect "python emitter via lib/journal_note.py -> ask" "$S/fx/py_ask.sh" ask

echo "── a stale note from a dead process with the same pid never leaks into a new fire ──"
fixture stale.sh 'exit 0'
J="$S/run/stale.jsonl"
: $(LHB_JOURNAL_PATH="$J" bash -c 'printf "%s" "$1" > "${LHB_JOURNAL_PATH%/*}/.fire-note.$$"; exec bash "$2" </dev/null' _ "$ASKJ" "$S/fx/stale.sh")
[ "$(last_decision "$J")" = "allow" ] && ok "stale note cleared at source time" || bad "stale note: got '$(last_decision "$J")', want allow"

echo "── the journal never changes a hook's stdout, stderr or exit code ──"
for h in ask.sh garbage.sh block_json.sh deny2_note.sh; do
  printf '{}' | LHB_JOURNAL_PATH="$S/run/on.jsonl" bash "$S/fx/$h" >"$S/on.out" 2>"$S/on.err"; r1=$?
  printf '{}' | LHB_JOURNAL_DISABLE=1 bash "$S/fx/$h" >"$S/off.out" 2>"$S/off.err"; r2=$?
  if [ "$r1" = "$r2" ] && cmp -s "$S/on.out" "$S/off.out" && cmp -s "$S/on.err" "$S/off.err"; then ok "$h byte-identical"; else bad "$h differs journal on vs off (rc $r1/$r2)"; fi
done
printf '{}' | LHB_JOURNAL_PATH="/nonexistent-dir-$$/x/j.jsonl" bash "$S/fx/ask.sh" >"$S/ro.out" 2>"$S/ro.err"; r=$?
if [ $r -eq 0 ] && grep -q '"ask"' "$S/ro.out" && [ ! -s "$S/ro.err" ]; then ok "unwritable journal dir: ask still printed, nothing on stderr"; else bad "unwritable journal dir changed the hook (rc=$r err=$(head -c 120 "$S/ro.err"))"; fi

echo "── real ask hooks, through their registered entry points ──"
bashjson() { T="$1" python3 -c 'import os,json; print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["T"]},"cwd":"/tmp"}))'; }
# cloud (python engine lib/cloud_guard.py)
ROUNDB_FC_CLOUD_DESTRUCTIVE_ASK=on expect "guard_cloud_destructive ask -> ask" "$HOOKS/guard_cloud_destructive.sh" ask "$(bashjson 'gcloud storage rm gs://pond-bucket/old.csv')"
ROUNDB_FC_CLOUD_DESTRUCTIVE_ASK=on expect "guard_cloud_destructive read -> allow" "$HOOKS/guard_cloud_destructive.sh" allow "$(bashjson 'gcloud storage ls gs://pond-bucket')"
# sheet (inline python ask_json)
mkdir -p "$S/marks"
SID="1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEf"
CLR="gws sheets spreadsheets values clear --params '{\"spreadsheetId\":\"$SID\",\"range\":\"Data!A:Z\"}'"
SHEET_LLM_MARKDIR="$S/marks" ROUNDB_FC_ASK_NOT_TOKEN=on expect "guard_sheet_writes ask -> ask" "$HOOKS/guard_sheet_writes.sh" ask "$(bashjson "$CLR")"
SHEET_LLM_MARKDIR="$S/marks" ROUNDB_FC_ASK_NOT_TOKEN=on expect "guard_sheet_formula_writes ask -> ask" "$HOOKS/guard_sheet_formula_writes.sh" ask "$(bashjson "LIFEHACK_SHEET_CONFIRM=1 gws sheets spreadsheets values update --params '{\"spreadsheetId\":\"$SID\"}'")"
expect "guard_sheet_writes non-sheet command -> allow" "$HOOKS/guard_sheet_writes.sh" allow "$(bashjson 'ls -la')"
# drive (inline python ask)
mkdir -p "$S/bin"; printf '%s\n' '#!/bin/bash' 'exit 1' > "$S/bin/gws"; chmod +x "$S/bin/gws"
PLAIN='gws drive files update --params '\''{"fileId":"mystery0001"}'\'' --json '\''{"trashed":true}'\'''
GWS_BIN="$S/bin/gws" SHEET_LLM_MARKDIR="$S/marks" ROUNDB_FC_DRIVE_BULK_DELETE=on ROUNDB_FC_SHEET_FILE_DELETE=on \
  expect "guard_drive_destructive ask -> ask" "$HOOKS/guard_drive_destructive.sh" ask "$(bashjson "$PLAIN")"
# stdout of a real ask hook is byte-identical with the journal on vs off
bashjson 'gcloud storage rm gs://pond-bucket/old.csv' > "$S/cl.in"
ROUNDB_FC_CLOUD_DESTRUCTIVE_ASK=on LHB_JOURNAL_PATH="$S/run/cl.jsonl" bash "$HOOKS/guard_cloud_destructive.sh" <"$S/cl.in" >"$S/a.out" 2>"$S/a.err"; r1=$?
ROUNDB_FC_CLOUD_DESTRUCTIVE_ASK=on LHB_JOURNAL_DISABLE=1 bash "$HOOKS/guard_cloud_destructive.sh" <"$S/cl.in" >"$S/b.out" 2>"$S/b.err"; r2=$?
if [ "$r1" = "$r2" ] && cmp -s "$S/a.out" "$S/b.out" && cmp -s "$S/a.err" "$S/b.err" && [ -s "$S/a.out" ]; then ok "real cloud ask byte-identical on vs off"; else bad "real cloud ask differs journal on vs off"; fi

echo "── drift: every ask emitter in system/hooks also writes the journal note ──"
for f in $(grep -lE "permissionDecision['\"]?[[:space:]]*[:=][[:space:]]*['\"]ask" "$HOOKS"/*.sh "$HOOKS"/lib/*.py 2>/dev/null); do
  if grep -qE "LHB_JOURNAL_NOTE|journal_note|lhb_journal_note" "$f"; then ok "$(basename "$f") notes its ask"; else bad "$(basename "$f") emits an ask but never writes the journal note (lib/journal_note.py)"; fi
done

echo "test_fire_journal_decision: $P passed, $F failed"
[ "$F" -eq 0 ]
