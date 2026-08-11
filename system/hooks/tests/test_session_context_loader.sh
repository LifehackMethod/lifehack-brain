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

# A genuinely fresh install: no root at all. A legitimate state, so exit 0 — but it must SAY it.
OUT="$(env HOME="$SANDBOX" bash -c "unset LIFEHACK_ROOT; HOME='$SANDBOX' bash '$LOADER'" 2>&1)"; RC=$?
says "No data root set yet" && ok || bad "fresh install" "did not name the state"
[ "$RC" = 0 ] && ok || bad "fresh install: exit code" "a fresh install is not a failure (got $RC)"

# A real internal failure — the hook cannot find its own repository — must exit NON-ZERO. This is
# the original bug in its purest form: the old version exited 0 here and printed nothing.
cp "$LOADER" "$SANDBOX/orphan.sh"
OUT="$(env HOME="$SANDBOX" LIFEHACK_ROOT="$NOTES" bash "$SANDBOX/orphan.sh" 2>&1)"; RC=$?
[ "$RC" != 0 ] && ok || bad "orphaned hook" "reported success from a location with no repository"
says "CANNOT START" && ok || bad "orphaned hook" "failed without saying why"

echo ""
echo "RESULT: $pass passed, $fail failed."
[ "$fail" = 0 ] && echo "SESSION CONTEXT GREEN" || exit 1
