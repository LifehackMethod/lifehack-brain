#!/bin/bash
# The matrix for `system/hooks/lib/bash_write_door.sh` — the shared library that answers ONE question
# for three guards: given a Bash command, which paths does it WRITE TO?
#
# WHY THIS FILE EXISTS AT ALL: the library's SIGNPOST names it. A signpost pointing at a file that
# does not exist is worse than none — it tells the next reader the rule is tested when it is not.
#
# ⛔ THE HALF THAT MATTERS IS THE SECOND ONE. Any pattern can be made to catch writes; the expensive
# failure in this repo has always been the opposite — a guard that fires on correct work. That gets
# routed around, and then it protects nothing. Two of those are on record: a guard that blocked a
# fixture teardown sitting in the same script as a pure read, and one that blocked the very commit
# that repaired it. Every MUST-NOT case below is one of those shapes.

cd "$(dirname "$0")/.." || exit 1
. lib/bash_write_door.sh || { echo "FATAL: cannot source lib/bash_write_door.sh"; exit 1; }

pass=0; fail=0
GUARDED="/notes/state/projects/demo/brief.md"

# does the library report GUARDED as a write target of this command?
hits() { bwd_write_targets "$1" | grep -Fxq "$GUARDED" && echo yes || echo no; }

want() { # want <expected yes|no> <command> <label>
  got=$(hits "$2")
  if [ "$got" = "$1" ]; then
    pass=$((pass+1)); printf '   ok   %s\n' "$3"
  else
    fail=$((fail+1)); printf '  FAIL  %s  (wanted %s, got %s)\n' "$3" "$1" "$got"
  fi
}

echo "── writes the guarded file — MUST be caught ──────────────────────────────"
want yes "cat > $GUARDED"                          "redirect"
want yes "echo hi >> $GUARDED"                     "append"
want yes "rm -f $GUARDED"                          "rm"
want yes "mv $GUARDED /tmp/x"                      "mv — the SOURCE is modified too, not just the dest"
want yes "cp /tmp/x $GUARDED"                      "cp onto it"
want yes "tee $GUARDED"                            "tee"
want yes "sed -i '' s/a/b/ $GUARDED"               "sed -i"
want yes "python3 -c 'open(\"x\",\"w\")' $GUARDED" "interpreter WITH a write call"
want yes "true; cat > $GUARDED"                    "second segment"

echo
echo "── does NOT write it — MUST be left alone (the expensive direction) ──────"
want no  "cat $GUARDED"                            "plain read"
want no  "grep -n frame $GUARDED"                  "grep"
want no  "head -50 $GUARDED"                       "head"
want no  "ls -la $(dirname "$GUARDED")"            "listing the folder"
want no  "cat $GUARDED > /tmp/copy.txt"            "READ it, write somewhere ELSE — the classic false positive"
want no  "rm -rf /tmp/fixture; cat $GUARDED"       "destroy /tmp in a script that also READS it"
want no  "echo 'do not edit $GUARDED'"             "a mere mention in a string"
want no  "git commit -m 'fix $GUARDED wording'"    "a mention in a commit message"
want no  "python3 -c 'print(open(\"$GUARDED\").read())'" "interpreter with NO write call — a pure read"
want no  "diff $GUARDED /tmp/other"                "diff"

echo
echo "── fail-closed ───────────────────────────────────────────────────────────"
if [ -z "$(bwd_write_targets '')" ]; then
  pass=$((pass+1)); printf '   ok   an empty command yields no targets\n'
else
  fail=$((fail+1)); printf '  FAIL  an empty command should yield nothing\n'
fi

echo
printf 'RESULT: %d passed, %d failed.\n' "$pass" "$fail"
if [ "$fail" -eq 0 ]; then echo "BASH WRITE DOOR GREEN"; exit 0; fi
echo "BASH WRITE DOOR RED"; exit 1
