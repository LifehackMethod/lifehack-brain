#!/bin/bash
# test_throughline_scope.sh — the switch and the wall around a read-only investigation.
#
#   throughline_flag.sh                  arm / clear / status, and the 30-minute TTL
#   guard_throughline_write_scope.sh     while armed, one folder is writable and nothing else is
#
# TWO THINGS THIS SUITE EXISTS TO CATCH, both of which shipped in the donor:
#
#   1. THE GUARD BLOCKING THE SKILL'S OWN OUTPUT. The destination was one machine's absolute path,
#      so anywhere else the comparison matched nothing and an armed run could not write the file it
#      was armed to write. A guard that stops the only permitted write is not a strict guard, it is
#      a broken one — and its symptom is a refusal naming a folder nobody has.
#   2. COMPARING A RESOLVED PATH AGAINST A CONFIGURED STRING. On macOS /tmp and /var are symlinks,
#      so a notes folder under either is handed to the hook as /private/... and matches nothing.
#      The whole "does the person own this path" question then answers backwards. The egress wall
#      hit exactly this on 2026-08-11 through string formatting rather than symlinks.
#
# THE UN-ARMED CASES MATTER MOST. This hook sits in front of every Write and Edit in every session.
# If it ever blocks outside an armed run it breaks the whole tool, so the no-op half is tested first.
#
# Deny = exit 2. Allow = exit 0.
# Run: bash system/hooks/tests/test_throughline_scope.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
FLAG_SH="$HOOKS/throughline_flag.sh"
GUARD="$HOOKS/guard_throughline_write_scope.sh"
for h in "$FLAG_SH" "$GUARD"; do
  [ -f "$h" ] || { echo "CANNOT RUN: no script at $h"; exit 1; }
done

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/tlscope.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
FAKEHOME="$SANDBOX/home"; mkdir -p "$FAKEHOME"
NOTES="$SANDBOX/notes"; mkdir -p "$NOTES/records/insights/throughline" "$NOTES/state/projects/alpha"

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

flag() { env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID="$1" bash "$FLAG_SH" "$2"; }

# write <label> <expected-rc> <session-id> <file-path> [notes-root-override]
#
# ⚠ CLAUDE_CODE_SESSION_ID IS SET EXPLICITLY, and that is not decoration. `env` inherits the
# surrounding environment, and this suite is run FROM a session that has that variable set — so
# without this the guard keyed on the real session, found no flag, and allowed everything. Twelve
# cases passed as "no block" while proving nothing at all. A test harness that leaks the ambient
# environment into the thing it is testing measures the room, not the code.
write() {
  # ⚠ ${5-...} WITHOUT THE COLON. With `:-`, passing an explicit empty string — which is how the
  # "no notes root" cases are written — falls back to the default, so those cases silently ran
  # against a perfectly good notes folder and proved nothing.
  local label="$1" exp="$2" sid="$3" fp="$4" root="${5-$NOTES}" got
  python3 -c "
import json,sys
print(json.dumps({'session_id': sys.argv[1], 'cwd': '/somewhere',
                  'tool_input': {'file_path': sys.argv[2]}}))" "$sid" "$fp" \
    | env HOME="$FAKEHOME" LIFEHACK_ROOT="$root" CLAUDE_CODE_SESSION_ID="$sid" bash "$GUARD" >/dev/null 2>&1
  got=$?
  [ "$got" = "$exp" ] && ok || bad "$label" "expected exit $exp, got $got"
}

echo "── un-armed: the hook must be invisible ─────────────────────────────────"
write "someone else's brief"   0 "sess-quiet" "$NOTES/state/projects/alpha/brief.md"
write "a file in the repo"     0 "sess-quiet" "$HOOKS/whatever.sh"
write "a path outside notes"   0 "sess-quiet" "/etc/hosts"
# No notes root at all, un-armed: still silent. A guard that starts blocking because a setting is
# missing would wall in every session that has not finished setting up.
write "no notes root, un-armed" 0 "sess-quiet" "/anything.md" ""

echo "── the switch ───────────────────────────────────────────────────────────"
out="$(flag sess-run status)"; [ "$out" = "none" ] && ok || bad "status before arm" "got '$out'"
flag sess-run arm >/dev/null
out="$(flag sess-run status)"; [ "$out" = "armed" ] && ok || bad "status after arm" "got '$out'"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID=sess-other bash "$FLAG_SH" status)"
[ "$out" = "none" ] && ok || bad "cross-session leak" "another session saw the arm: '$out'"
out="$(env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID=sess-run THROUGHLINE_TTL_MIN=0 bash "$FLAG_SH" status)"
[ "$out" = "none" ] && ok || bad "TTL expiry" "expected 'none' at TTL 0, got '$out'"
# ...and the expiry must remove the FILE, since that is what the guard checks.
[ -z "$(ls "$FAKEHOME/.claude/run/throughline/" 2>/dev/null)" ] && ok \
  || bad "TTL removes the file" "status said 'none' but the flag is still on disk — the guard reads the FILE"

echo "── armed: exactly one folder is writable ────────────────────────────────"
flag sess-run arm >/dev/null
write "the findings file"        0 "sess-run" "$NOTES/records/insights/throughline/alpha-2026-08-11.md"
write "a nested findings file"   0 "sess-run" "$NOTES/records/insights/throughline/sub/x.md"
# ⭐ THE FIRST WRITE EVER, into a notes folder where the destination has never been created. This is
# the case a suite naturally skips, because setup makes the folder before the assertions start — and
# it is the one that decides whether the skill works at all on day one. A guard that only permits
# writes into folders that already exist permits nothing on a fresh install.
FRESH="$SANDBOX/fresh-notes"; mkdir -p "$FRESH"
write "day one, no folder yet"   0 "sess-run" "$FRESH/records/insights/throughline/alpha-2026-08-11.md" "$FRESH"
write "day one, still not a way in" 2 "sess-run" "$FRESH/state/projects/beta/brief.md" "$FRESH"
echo "   and everything else is refused — including the things it is reading"
write "the project brief"        2 "sess-run" "$NOTES/state/projects/alpha/brief.md"
write "the top-level canon"      2 "sess-run" "$NOTES/canon.md"
write "a sibling record type"    2 "sess-run" "$NOTES/records/insights/other.md"
write "the repo itself"          2 "sess-run" "$HOOKS/guard_throughline_write_scope.sh"
write "somewhere off the map"    2 "sess-run" "/tmp/scratch.md"
echo "   a near-miss that shares the prefix is still outside"
write "the sibling directory"    2 "sess-run" "$NOTES/records/insights/throughline-notes/x.md"

echo "── armed and fail-CLOSED: no answer means no, not yes ───────────────────"
# Unreadable payload during an armed run. The session id comes from the env here, so the hook knows
# it IS armed and must refuse rather than shrug.
printf 'not json at all' | env HOME="$FAKEHOME" CLAUDE_CODE_SESSION_ID=sess-run bash "$GUARD" >/dev/null 2>&1
[ "$?" = 2 ] && ok || bad "unparseable while armed" "expected a refusal"
# A notes folder that will not resolve, during an armed run: there is no permitted destination, so
# every write is outside it. Refusing is the only honest answer.
write "no notes root, armed"     2 "sess-run" "$NOTES/records/insights/throughline/x.md" ""
write "notes root set to /"      2 "sess-run" "$NOTES/records/insights/throughline/x.md" "/"

echo "── the deny TEXT, not just the exit code ────────────────────────────────"
# A hook's job is to re-teach the boundary. A refusal that does not say where to write instead just
# stops the run; the session then guesses, or gives up. Checked because payload tests that assert
# only the return code let a wrong redirect ship (hook-sop.md §4).
MSG="$(python3 -c "
import json; print(json.dumps({'session_id':'sess-run','cwd':'/x','tool_input':{'file_path':'$NOTES/canon.md'}}))" \
  | env HOME="$FAKEHOME" LIFEHACK_ROOT="$NOTES" CLAUDE_CODE_SESSION_ID=sess-run bash "$GUARD" 2>&1 >/dev/null)"
printf '%s' "$MSG" | grep -q "records/insights/throughline" && ok || bad "deny names the destination" "$MSG"
printf '%s' "$MSG" | grep -q "throughline_flag.sh clear" && ok || bad "deny names the way out" "$MSG"
printf '%s' "$MSG" | grep -q "SKILL.md" && ok || bad "deny names the rule" "$MSG"

echo "── a symlinked notes folder — the failure that shipped twice ────────────"
# The tool hands over the path with symlinks resolved; the destination is built from a configured
# string. If the two are compared unresolved, the person's own findings file reads as somebody
# else's and the run is blocked from its only permitted write.
REAL="$SANDBOX/real-notes"; mkdir -p "$REAL/records/insights/throughline"
LINK="$SANDBOX/linked-notes"; ln -s "$REAL" "$LINK"
write "configured via the link, written via the link" 0 "sess-run" "$LINK/records/insights/throughline/a.md" "$LINK"
write "configured via the link, arriving resolved"    0 "sess-run" "$REAL/records/insights/throughline/a.md" "$LINK"
write "configured resolved, arriving via the link"    0 "sess-run" "$LINK/records/insights/throughline/a.md" "$REAL"
echo "   and resolving must not become a way in"
write "a stranger, through the link"                  2 "sess-run" "$LINK/canon.md" "$REAL"

flag sess-run clear >/dev/null
echo "   after clear, the session is ordinary again"
write "post-clear write"         0 "sess-run" "$NOTES/state/projects/alpha/brief.md"

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "THROUGHLINE SCOPE GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1; fi
