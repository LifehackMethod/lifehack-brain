#!/bin/bash
# test_session_context_loader.sh — proof that the thing which puts memory in front of a session
# actually does, and says so honestly when it cannot.
#
# WHY THIS SUITE EXISTS. This hook's own header describes the bug it was built against: the version
# it came from suppressed stderr, ended on an unconditional `exit 0`, and so on a machine where the
# data was not where it expected it reported success and delivered nothing — silently, every session,
# for as long as nobody noticed. That failure mode is invisible by construction: a system that cannot
# see its own memory looks exactly like a system that has none yet. Nothing here was checking that
# the fix held, and on 2026-08-11 a SECOND instance of the same class was found in this same file —
# the root canon was never loaded while four shipped documents said it was. Both are locked below.
#
# Run: bash system/hooks/tests/test_session_context_loader.sh   (exit 0 = all pass)

HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
LOADER="$HOOKS/session_context_loader.sh"
REPO="${HOOKS%/system/hooks}"
[ -f "$LOADER" ] || { echo "CANNOT RUN: no loader at $LOADER"; exit 1; }

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/loader.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
NOTES="$SANDBOX/notes"
mkdir -p "$NOTES/desks/lamps/canon" "$NOTES/desks/money/canon"

pass=0; fail=0
ok()   { pass=$((pass+1)); }
bad()  { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# Runs the loader against the sandbox and captures BOTH streams plus the exit code.
runit() {
  OUT="$(env HOME="$SANDBOX" LIFEHACK_ROOT="${1:-$NOTES}" bash "$LOADER" 2>&1)"
  RC=$?
}
says()    { printf '%s' "$OUT" | grep -q "$1"; }
saysnot() { ! printf '%s' "$OUT" | grep -q "$1"; }

echo "── the root canon, which four documents promise is loaded every session ──"
printf '# Canon\n\nMy name is spelled with one L.\n' > "$NOTES/canon.md"
runit
says "one L" && ok || bad "root canon is loaded" "it was not in the output"
[ "$RC" = 0 ] && ok || bad "root canon: exit code" "expected 0, got $RC"

# ⭐ The exact regression: this used to print "no subject folders, nothing to load" and exit BEFORE
# ever looking at the root canon — so on day one, the file the system had just told you was carried
# into every conversation was the one thing it never read.
mv "$NOTES/desks" "$SANDBOX/desks-parked"
runit
says "one L" && ok || bad "root canon with no subjects yet" "the day-one case dropped it entirely"
saysnot "^No subject folders yet — nothing standing to load\." && ok || bad "day-one wording" "still claims nothing to load"
mv "$SANDBOX/desks-parked" "$NOTES/desks"

echo "── the subject folders ────────────────────────────────────────────────────"
printf 'Prefer warm bulbs, 2700K.\n' > "$NOTES/desks/lamps/canon/current.md"
printf 'The tax year ends in April.\n' > "$NOTES/desks/money/canon/current.md"
runit
says "2700K"       && ok || bad "subject canon loaded" "lamps missing"
says "ends in April" && ok || bad "subject canon loaded" "money missing"
says "one L"       && ok || bad "root canon still loaded alongside subjects" "root dropped"
says "2 subject folder" && ok || bad "the count" "did not report two folders"

echo "── the ceiling announces itself rather than dropping the tail quietly ─────"
python3 -c "print('x'*400)" > "$NOTES/desks/lamps/canon/current.md"
python3 -c "print('y'*400)" > "$NOTES/desks/money/canon/current.md"
OUT="$(env HOME="$SANDBOX" LIFEHACK_ROOT="$NOTES" SESSION_CONTEXT_CHAR_CEIL=500 bash "$LOADER" 2>&1)"
says "STOPPED HERE" && ok || bad "ceiling" "truncated without saying so — the worst outcome"
says "NOT loaded"   && ok || bad "ceiling" "did not name what was left out"
printf 'Prefer warm bulbs, 2700K.\n' > "$NOTES/desks/lamps/canon/current.md"
printf 'The tax year ends in April.\n' > "$NOTES/desks/money/canon/current.md"

echo "── it never reports success while delivering nothing ─────────────────────"
# A remembered folder that is not there. This is a cloud drive that did not mount, and it must NOT
# read as an empty system — telling this person to "set it once" invites them to point at an empty
# folder and lose the link to everything they have written.
OUT="$(env HOME="$SANDBOX" LIFEHACK_ROOT="$SANDBOX/vanished" bash "$LOADER" 2>&1)"; RC=$?
says "NOT WHERE THIS SYSTEM REMEMBERS THEM\|No data root set yet" && ok || bad "missing root" "said neither of the two honest things"
saysnot "one L" && ok || bad "missing root" "claimed to load canon from a folder that is not there"
# ⚠ exit 0, DELIBERATELY, even though this IS a real failure. Confirmed against the official
# SessionStart hook contract: this event cannot block regardless of exit code, and on a non-zero
# exit Claude Code discards this hook's stdout instead of injecting it into the model's context —
# only stderr renders, as a UI-only notice the model never sees. `exit 1` here would not fail any
# more safely; it would just make the "NOT WHERE THIS SYSTEM REMEMBERS THEM" line above invisible
# to the one reader it's for. See session_context_loader.sh's own FAIL_POSTURE header for the full
# reasoning and citation.
[ "$RC" = 0 ] && ok || bad "missing root: exit code" "expected 0 (SessionStart can't block, and non-zero hides stdout from the model) — got $RC"

# A genuinely fresh install: no root at all. A legitimate state, so exit 0 — but it must SAY it.
OUT="$(env HOME="$SANDBOX" bash -c "unset LIFEHACK_ROOT; HOME='$SANDBOX' bash '$LOADER'" 2>&1)"; RC=$?
says "No data root set yet" && ok || bad "fresh install" "did not name the state"
[ "$RC" = 0 ] && ok || bad "fresh install: exit code" "a fresh install is not a failure (got $RC)"

# A real internal failure — the hook cannot find its own repository. Historically this suite
# required a NON-zero exit here, on the theory that a genuine failure must say so through the exit
# code. That theory doesn't hold for THIS hook: SessionStart is structurally non-blocking (no
# exit-2-blocks path the way PreToolUse has), and a non-zero exit makes Claude Code drop this
# hook's stdout entirely rather than inject it — so `exit 1` would have hidden the "CANNOT START"
# line below from the model, reproducing the ORIGINAL bug (report nothing, deliver nothing) one
# exit code later. `exit 0` + a loud stdout line is what actually reaches the model, so that is
# now the required shape: exit 0, AND the message.
cp "$LOADER" "$SANDBOX/orphan.sh"
OUT="$(env HOME="$SANDBOX" LIFEHACK_ROOT="$NOTES" bash "$SANDBOX/orphan.sh" 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok || bad "orphaned hook: exit code" "expected 0 (SessionStart can't block, and non-zero would hide the message below from the model) — got $RC"
says "CANNOT START" && ok || bad "orphaned hook" "failed without saying why"

echo ""
echo "── a file that EXISTS and is non-empty but cannot be READ is not the same as nothing to say ──"
# The gap this locks in: `-s` (non-empty) passing but the subsequent `cat` failing (permissions)
# used to be indistinguishable from "nothing to load" — the file just silently disappeared from
# the output, no different from a folder that was never ingested. Root canon first, then a subject
# canon file, with a HEALTHY sibling subject alongside it to prove one unreadable file cannot also
# take down everything that DID read fine.
if [ "$(id -u)" = "0" ]; then
  echo "  (skipped: running as root — chmod 000 does not block root's own reads)"
else
  printf '# Canon\nshould not leak\n' > "$NOTES/canon.md"
  chmod 000 "$NOTES/canon.md"
  runit
  says "COULD NOT READ" && says "canon.md" && ok || bad "unreadable root canon" "no visible failure message"
  saysnot "should not leak" && ok || bad "unreadable root canon" "leaked content despite chmod 000 -- check test environment, not just the hook"
  [ "$RC" = 0 ] && ok || bad "unreadable root canon: exit code" "session must still come up — expected 0, got $RC"
  chmod 644 "$NOTES/canon.md"
  printf '# Canon\n\nMy name is spelled with one L.\n' > "$NOTES/canon.md"

  printf 'good money notes\n' > "$NOTES/desks/money/canon/current.md"
  printf 'should not leak either\n' > "$NOTES/desks/lamps/canon/current.md"
  chmod 000 "$NOTES/desks/lamps/canon/current.md"
  runit
  says "COULD NOT READ" && says "lamps" && ok || bad "unreadable subject canon" "no visible failure message naming lamps"
  says "good money notes" && ok || bad "unreadable subject canon" "the OTHER, readable subject stopped loading too"
  saysnot "should not leak either" && ok || bad "unreadable subject canon" "leaked content despite chmod 000"
  [ "$RC" = 0 ] && ok || bad "unreadable subject canon: exit code" "expected 0, got $RC"
  chmod 644 "$NOTES/desks/lamps/canon/current.md"
  printf 'Prefer warm bulbs, 2700K.\n' > "$NOTES/desks/lamps/canon/current.md"
fi

echo ""
echo "── health_line.py itself unavailable is a different failure than 'nothing to report' ──────"
# Locks in the note-vs-silence distinction _findings_banner() draws: a working health_line.py that
# finds nothing prints nothing (never tested here — that's the default/healthy case exercised by
# every other block above), but a health_line.py that could not even START must say so, not just
# go quiet the same way. Moved aside, not deleted, and restored immediately after capture so a
# failure mid-assertion still leaves the real file in place.
HEALTH_LINE="$REPO/system/tools/health_line.py"
mv "$HEALTH_LINE" "$HEALTH_LINE.bak"
runit
mv "$HEALTH_LINE.bak" "$HEALTH_LINE"
says "health_line.py did not run this session" && ok || bad "health_line unavailable" "no visible note when the tool itself could not start"
[ "$RC" = 0 ] && ok || bad "health_line unavailable: exit code" "expected 0, got $RC"

echo ""
echo "RESULT: $pass passed, $fail failed."
[ "$fail" = 0 ] && echo "SESSION CONTEXT GREEN" || exit 1
