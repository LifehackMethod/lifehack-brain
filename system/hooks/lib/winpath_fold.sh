# winpath_fold.sh — fold an ALREADY-CANONICAL path into one comparable spelling, so a bash
# string/glob comparison between paths built by two different runtimes can succeed.
#
# WHY THIS EXISTS (found 2026-08-20, GitHub #73 / #77 D1 / #92 item 3): this repo's trusted-zone
# gate (system/hooks/ingest_gate_enforce.sh) and a couple of the write guards canonicalise a
# ROOT (this repo, the notes root, $HOME) with Git Bash's `pwd -P`, and canonicalise the INCOMING
# path with Windows-native Python's `os.path.realpath`. Off Windows those two calls produce
# identical strings. On Windows they do not — they are both fully correct, but they speak two
# different alphabets for the same directory:
#   pwd -P                -> /c/Users/name/Repo        (MSYS/Git-Bash POSIX form)
#   os.path.realpath(...)  -> C:\Users\name\Repo         (native Windows form)
# A `case "$x" in "$y"/*)` test is a literal string-prefix match, so two spellings of the
# identical folder never match, and every comparison built on it falls through to its deny arm —
# for ingest_gate_enforce.sh that means the user's own repo, ~/.claude, and their notes root all
# read as EXTERNAL. Fixture proof (reported): 20 failed / 47 passed before a fix, 0 failed / 69
# passed after one landed.
#
# WHAT THIS DOES NOT DO: it does not resolve symlinks, follow junctions, or collapse `..` — that
# is `pwd -P` and `os.path.realpath`'s job, already done by the caller before a value reaches
# here, and this file changes nothing about it. Weakening THAT canonicalisation is exactly the
# failure the callers' own headers warn against (macOS /private/tmp, 2026-08-11) — this file only
# runs a SECOND, purely cosmetic pass over an already-fully-resolved path, so two spellings of one
# real directory become one spelling before the string comparison, never so two DIFFERENT
# directories become one spelling. Every caller's glob still carries its own trailing "/*"
# boundary guard, untouched — that is what stops "repo" matching "repo-evil", not this file.
#
# NO NEW DEPENDENCY. Pure bash + POSIX `tr`/`sed`, both already required everywhere else in this
# hook plane. `cygpath` was considered and explicitly NOT taken — it is not present on every
# Git-for-Windows install, and the dependency-free approach here is sufficient once both sides of
# every comparison are folded through it.
#
# Usage: _winfold "<path>" [force]      (or set LIFEHACK_WINFOLD_FORCE=1|0 for the same effect)
#   force = 1  -> always apply the Windows fold (used by tests, so they don't need to fake uname)
#   force = 0  -> never apply it (identity — same string back)
#   omitted    -> autodetect via `uname -s` (the real behaviour every production caller uses)
# Off Windows (autodetect or force=0): returns the input completely UNCHANGED, byte for byte —
# the comparison on macOS/Linux is IDENTICAL to what it was before this file existed.
# On Windows (autodetect or force=1): lowercases, turns `\` into `/`, and folds a leading drive
# letter (`c:/...` or `C:\...`) into the MSYS mount spelling `pwd -P` already produces (`/c/...`).
# Lowercasing is deliberately gated to Windows only: NTFS is case-insensitive, so folding case
# there loses no real distinction; doing the same on a case-sensitive filesystem (Linux, and
# macOS when opted in) would be an actual widening, not a no-op — which is why it never runs
# unless this file has determined (or been told, for a test) that it is on Windows.

_gate_is_windows() {
  case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*) return 0 ;;
    *) return 1 ;;
  esac
}

_winfold() {
  _wf_in="$1"
  # Precedence: explicit argument, then $LIFEHACK_WINFOLD_FORCE, then autodetect.
  # The env door exists so a GUARD can be exercised in its forced state from a Linux CI
  # runner. The argument door only reaches this function directly, which is enough to test
  # the fold itself but NOT enough to test a guard that calls it internally -- and the guards
  # are where the bug actually bites. tests/test_guards_path_spelling.sh needs this.
  # ⛔ Production callers pass no argument and set no env var, so autodetect stays the real
  # behaviour everywhere outside a test. Mirrored in lib/winpath_fold.py -- keep them equal.
  _wf_force="${2:-${LIFEHACK_WINFOLD_FORCE:-}}"
  if [ "$_wf_force" = "1" ]; then
    _wf_win=1
  elif [ "$_wf_force" = "0" ]; then
    _wf_win=0
  elif _gate_is_windows; then
    _wf_win=1
  else
    _wf_win=0
  fi
  if [ "$_wf_win" != "1" ] || [ -z "$_wf_in" ]; then
    printf '%s' "$_wf_in"
    return 0
  fi
  printf '%s' "$_wf_in" | tr 'A-Z' 'a-z' | tr '\\' '/' | sed -E 's#^([a-z]):/#/\1/#'
}
