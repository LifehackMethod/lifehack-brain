#!/bin/bash
# test_winpath_fold_parity.sh — proves lib/winpath_fold.sh's `_winfold` and lib/winpath_fold.py's
# `winfold` return BYTE-IDENTICAL output for the same input, at the same force setting, for both
# the environment-variable door and the positional-argument door.
#
# WHY THIS EXISTS: several guards in this plane do their path classification in embedded Python
# (guard_canon_write.sh, enforce_skill_frontmatter.sh, enforce_multiphase_contract.sh, ...), not in
# the bash body that reads the hook's stdin. Both halves fold a Windows-native path into one
# comparable spelling before classifying it, and they are two INDEPENDENT implementations of the
# same idea, in two languages, with no shared runtime. If they ever disagree, the SAME logical path
# would be treated as "in scope" by the bash half of a guard and "out of scope" by the python half
# (or vice versa) depending only on which language happened to do the classifying — a silent,
# guard-specific inconsistency that nothing else here would catch. This file is what makes carrying
# two copies of one idea safe: it feeds identical inputs to both and fails the instant one output
# differs from the other, or from a hand-derived expected value.
#
# WHAT THIS PROVES: for a fixed table of inputs, at force=1 and force=0, and through both the
# positional-argument door and the LIFEHACK_WINFOLD_FORCE door: bash and python return the same
# bytes, and force=0 is the identity transform in both.
#
# WHAT THIS CANNOT PROVE: whether the fold is the RIGHT transform for a real Windows/Git-Bash pair
# of spellings (that is test_winpath_fold.sh's job, with the GitHub #77 D1 repro) — only that the
# two copies of it never drift apart. A change that breaks both languages identically, in the same
# wrong direction, passes this file and would only be caught by test_winpath_fold.sh or manual
# inspection.
#
# Run: bash system/hooks/tests/test_winpath_fold_parity.sh   (exit 0 = all pass)

HOOKDIR="$(cd "$(dirname "$0")/.." && pwd)"
LIB_SH="$HOOKDIR/lib/winpath_fold.sh"
LIB_PY="$HOOKDIR/lib/winpath_fold.py"
[ -f "$LIB_SH" ] || { echo "CANNOT RUN: no lib at $LIB_SH"; exit 1; }
[ -f "$LIB_PY" ] || { echo "CANNOT RUN: no lib at $LIB_PY"; exit 1; }
. "$LIB_SH"

# MSYS_NO_PATHCONV: an ENVIRONMENT gotcha, not a fold bug. On Git Bash for Windows, an argv that
# LOOKS like a POSIX absolute path ("/Users/name/Repo") and is handed to a NATIVE (non-MSYS) exe --
# which the Windows python3.exe this file drives always is -- gets silently rewritten by the MSYS
# runtime's own automatic path conversion before python ever sees it (observed: "/Users/name/Repo"
# arrived as "C:/Program Files/Git/Users/name/Repo"). That conversion is MSYS's, not this repo's,
# and it only touches argv -- production guards hand winpath_fold.py its path through JSON on
# stdin, which this rewriting never sees. Disabled for exactly this script's python3 invocations so
# the table below tests the FOLD, not Git Bash's own argv mangling.
# ⚠ THE SCRIPT PATH ITSELF still needs to resolve for python3 to open it, and with conversion off a
# literal "/c/.../winpath_fold.py" argv is no longer translated to a Windows path for it either
# (observed: python3 tried to open "C:\c\Users\...\winpath_fold.py" and failed). Sidestepped below
# by invoking python3 with a RELATIVE filename from inside lib/ (via a subshell cd) instead of an
# absolute POSIX path -- a bare relative name was never subject to this conversion either way.
export MSYS_NO_PATHCONV=1
LIB_PY_DIR="$HOOKDIR/lib"
LIB_PY_NAME="winpath_fold.py"

pass=0; fail=0
eq() {  # label · expected · actual
  if [ "$2" = "$3" ]; then pass=$((pass+1)); else fail=$((fail+1)); echo "  FAIL [$1]: expected [$2] got [$3]"; fi
}

# ── the two doors, driven identically for both languages ────────────────────────────────────────
# bash_fold <input> [force]     -- omit force to exercise autodetect + $LIFEHACK_WINFOLD_FORCE
# py_fold   <input> [force]     -- same signature, drives lib/winpath_fold.py's __main__
bash_fold() {
  if [ $# -ge 2 ]; then _winfold "$1" "$2"; else _winfold "$1"; fi
}
py_fold() {
  if [ $# -ge 2 ]; then
    ( cd "$LIB_PY_DIR" && python3 "$LIB_PY_NAME" "$1" "$2" )
  else
    ( cd "$LIB_PY_DIR" && python3 "$LIB_PY_NAME" "$1" )
  fi
}

# ── the input table ───────────────────────────────────────────────────────────────────────────────
# Parallel arrays: LABELS[i] / INPUTS[i] / EXPECT1[i] (the hand-derived force=1 fold, asserted
# against BOTH languages so a shared-wrong-answer bug can't hide behind mutual agreement).
LABELS=(
  "posix path"
  "mixed-case posix path"
  "native backslash, drive letter"
  "forward-slash drive letter"
  "empty string"
  "path with spaces"
  "UNC-ish path"
  "trailing slash"
  "relative path"
)
INPUTS=(
  "/Users/name/Repo"
  "/Users/Name/Repo"
  'C:\Users\name\Repo'
  'C:/Users/name/Repo'
  ""
  "/Users/name/My Repo/sub dir"
  '\\server\share\x'
  "/Users/name/Repo/"
  "sub/dir/File.md"
)
EXPECT1=(
  "/users/name/repo"
  "/users/name/repo"
  "/c/users/name/repo"
  "/c/users/name/repo"
  ""
  "/users/name/my repo/sub dir"
  "//server/share/x"
  "/users/name/repo/"
  "sub/dir/file.md"
)

N=${#INPUTS[@]}

echo "-- FORCE=1: bash == python == hand-derived expected, for every input in the table --"
i=0
while [ "$i" -lt "$N" ]; do
  label="${LABELS[$i]}"; input="${INPUTS[$i]}"; want="${EXPECT1[$i]}"
  b="$(bash_fold "$input" 1)"
  p="$(py_fold "$input" 1)"
  eq "force=1 bash [$label]"          "$want" "$b"
  eq "force=1 python [$label]"        "$want" "$p"
  eq "force=1 PARITY bash==python [$label]" "$b" "$p"
  i=$((i+1))
done

echo "-- FORCE=0: identity, byte for byte, in BOTH languages, for every input --"
i=0
while [ "$i" -lt "$N" ]; do
  label="${LABELS[$i]}"; input="${INPUTS[$i]}"
  b="$(bash_fold "$input" 0)"
  p="$(py_fold "$input" 0)"
  eq "force=0 bash identity [$label]"   "$input" "$b"
  eq "force=0 python identity [$label]" "$input" "$p"
  eq "force=0 PARITY bash==python [$label]" "$b" "$p"
  i=$((i+1))
done

echo "-- THE ENV DOOR: LIFEHACK_WINFOLD_FORCE must produce the SAME result as the positional arg --"
# Representative subset, not the whole table -- the doors are orthogonal to the fold logic itself
# (already fully exercised above), so this section only has to prove the PRECEDENCE wiring.
ENV_LABELS=("native backslash, drive letter" "forward-slash drive letter" "relative path")
ENV_INPUTS=('C:\Users\name\Repo' 'C:/Users/name/Repo' "sub/dir/File.md")
j=0
while [ "$j" -lt "${#ENV_INPUTS[@]}" ]; do
  label="${ENV_LABELS[$j]}"; input="${ENV_INPUTS[$j]}"

  # env=1, no positional arg -> must equal the positional force=1 call, in both languages
  b_env1="$(LIFEHACK_WINFOLD_FORCE=1 bash_fold "$input")"
  p_env1="$(LIFEHACK_WINFOLD_FORCE=1 py_fold "$input")"
  b_pos1="$(bash_fold "$input" 1)"
  p_pos1="$(py_fold "$input" 1)"
  eq "env=1 == positional 1, bash [$label]"   "$b_pos1" "$b_env1"
  eq "env=1 == positional 1, python [$label]" "$p_pos1" "$p_env1"

  # env=0, no positional arg -> must equal the positional force=0 call (identity), in both languages
  b_env0="$(LIFEHACK_WINFOLD_FORCE=0 bash_fold "$input")"
  p_env0="$(LIFEHACK_WINFOLD_FORCE=0 py_fold "$input")"
  eq "env=0 == positional 0 (identity), bash [$label]"   "$input" "$b_env0"
  eq "env=0 == positional 0 (identity), python [$label]" "$input" "$p_env0"

  j=$((j+1))
done

echo "-- THE OVERRIDE: an explicit positional argument beats \$LIFEHACK_WINFOLD_FORCE, both directions --"
k=0
while [ "$k" -lt "${#ENV_INPUTS[@]}" ]; do
  label="${ENV_LABELS[$k]}"; input="${ENV_INPUTS[$k]}"

  # env says fold (1), positional argument says don't (0) -> positional wins -> identity
  b="$(LIFEHACK_WINFOLD_FORCE=1 bash_fold "$input" 0)"
  p="$(LIFEHACK_WINFOLD_FORCE=1 py_fold "$input" 0)"
  eq "positional 0 overrides env=1, bash [$label]"   "$input" "$b"
  eq "positional 0 overrides env=1, python [$label]" "$input" "$p"

  # env says don't fold (0), positional argument says fold (1) -> positional wins -> folded
  b2="$(LIFEHACK_WINFOLD_FORCE=0 bash_fold "$input" 1)"
  p2="$(LIFEHACK_WINFOLD_FORCE=0 py_fold "$input" 1)"
  b1="$(bash_fold "$input" 1)"  # the known-good force=1 value for this exact input
  eq "positional 1 overrides env=0, bash [$label]"    "$b1" "$b2"
  eq "positional 1 overrides env=0, python [$label]"  "$b1" "$p2"
  eq "positional 1 overrides env=0, PARITY [$label]"  "$b2" "$p2"

  k=$((k+1))
done

echo
echo "-- LENGTH PRESERVATION: len(folded) == len(input), both halves, force=1 --"
# ⛔ DO NOT DELETE THIS SECTION AS REDUNDANT. system/hooks/observability_logger.sh depends on it.
# That hook folds the cwd to FIND the "/desks/" marker, then slices the desk NAME out of the
# ORIGINAL string by offset, so the real on-disk casing survives into the log rather than being
# lowercased by the fold. That slice is only correct while the fold is character-count preserving.
# It is today: lowercasing preserves length, `\` -> `/` preserves length, and the drive-letter fold
# `c:/` -> `/c/` is three characters for three. A future "improvement" to the fold -- collapsing
# repeated separators, stripping a trailing slash, expanding a mount alias -- would break that
# property and silently corrupt every desk name in the logs instead of failing loudly. This section
# is what turns that into a build failure.
LEN_INPUTS=(
  '/Users/name/Repo'
  'C:\Users\name\Repo'
  'C:/Users/name/Repo'
  '/c/users/name/repo'
  '\\server\share\desks\D\x.md'
  'relative/desks/D/x.md'
  'C:'
  'C:foo'
  'D:\Notes\Brain\desks\MyDesk\canon\current.md'
  '/path/with spaces/desks/A Desk/x.md'
  'C:\trailing\slash\'
)
for input in "${LEN_INPUTS[@]}"; do
  b="$(bash_fold "$input" 1)"
  pf="$(py_fold "$input" 1)"
  eq "length preserved, bash   [$input]" "${#input}" "${#b}"
  eq "length preserved, python [$input]" "${#input}" "${#pf}"
  eq "length parity            [$input]" "${#b}"     "${#pf}"
done

echo
echo "RESULT: $pass passed, $fail failed."
[ "$fail" -eq 0 ] && echo "WINPATH FOLD PARITY GREEN" || echo "WINPATH FOLD PARITY RED"
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
