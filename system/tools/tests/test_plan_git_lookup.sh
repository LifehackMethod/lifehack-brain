#!/usr/bin/env bash
# LK1 — regression test: plan_git_check.py --hash must find the REAL commit, not a lookalike
# that merely shares the "<id>:" subject prefix. Scoped by --subject and/or --path.
# Prints one line per case (PASS/FAIL <letter> <what>) and a final LOOKUP-OK|LOOKUP-FAIL <n>/5.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS="$(dirname "$HERE")"
CHECK="$TOOLS/plan_git_check.py"

D=$(mktemp -d)
trap 'rm -rf "$D"' EXIT
R1="$D/repo1"
R2="$D/repo2"

mkrepo() {
  mkdir -p "$1"
  git -C "$1" init -q
  git -C "$1" config user.email t@example.com
  git -C "$1" config user.name t
  git -C "$1" config commit.gpgsign false
}
commit_file() {  # repo file subject
  echo "$3 $(date +%s%N) $RANDOM" >> "$1/$2"
  git -C "$1" add "$2"
  git -C "$1" commit -q -m "$3"
}

mkrepo "$R1"
commit_file "$R1" other.txt "3.1: unrelated work from another plan"
commit_file "$R1" x.txt "3.1: the real fix"
REAL=$(git -C "$R1" rev-parse --short HEAD)
commit_file "$R1" other.txt "3.1: later unrelated"

mkrepo "$R2"
commit_file "$R2" other.txt "3.1: unrelated work from another plan"

PASSN=0
report() {  # ok letter what got
  if [ "$1" = 1 ]; then
    PASSN=$((PASSN + 1)); echo "PASS $2 $3"
  else
    echo "FAIL $2 $3 got=$4"
  fi
}
# short hashes may differ in length between callers; accept a prefix match either way
same_hash() { [ -n "$1" ] && { [[ "$REAL" == "$1"* ]] || [[ "$1" == "$REAL"* ]]; }; }

# (a) --subject picks the real commit
got=$(PLAN_GIT_REPO="$R1" python3 "$CHECK" --task 3.1 --hash --subject "3.1: the real fix" 2>/dev/null)
if same_hash "$got"; then report 1 a "subject-scoped lookup returns the real commit"
else report 0 a "subject-scoped lookup returns the real commit" "$got"; fi

# (b) --path picks the real commit
got=$(PLAN_GIT_REPO="$R1" python3 "$CHECK" --task 3.1 --hash --path x.txt 2>/dev/null)
if same_hash "$got"; then report 1 b "path-scoped lookup returns the real commit"
else report 0 b "path-scoped lookup returns the real commit" "$got"; fi

# (c) only a lookalike exists -> NO-COMMIT, exit 4
got=$(PLAN_GIT_REPO="$R2" python3 "$CHECK" --task 3.1 --hash --subject "3.1: the real fix" 2>/dev/null)
rc=$?
if [ "$got" = "NO-COMMIT 3.1" ] && [ "$rc" = 4 ]; then report 1 c "lookalike-only repo gives NO-COMMIT and exit 4"
else report 0 c "lookalike-only repo gives NO-COMMIT and exit 4" "'$got' rc=$rc"; fi

# (d) unscoped lookup warns on stderr
err=$(PLAN_GIT_REPO="$R1" python3 "$CHECK" --task 3.1 --hash 2>&1 >/dev/null)
if [[ "$err" == WARN\ unscoped* ]]; then report 1 d "unscoped lookup warns on stderr"
else report 0 d "unscoped lookup warns on stderr" "'$err'"; fi

# (e) plan_retire.get_evidence uses the card's Where:/Commit: to find the real commit
got=$(PLAN_GIT_REPO="$R1" python3 -c '
import sys
sys.path.insert(0, sys.argv[1])
import plan_retire
lines = ["- [ ] 3.1 Fix the thing", "  Where: x.txt", "  Commit: 3.1: the real fix"]
try:
    print(plan_retire.get_evidence(lines, "3.1"))
except SystemExit as e:
    print("EXIT", e.code)
' "$TOOLS" 2>/dev/null | tail -n 1)
if same_hash "$got"; then report 1 e "get_evidence returns the real commit from the card"
else report 0 e "get_evidence returns the real commit from the card" "$got"; fi

if [ "$PASSN" = 5 ]; then echo "LOOKUP-OK $PASSN/5"; exit 0
else echo "LOOKUP-FAIL $PASSN/5"; exit 1; fi
