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
want no  "python3 read.py $GUARDED 2>&1"           "interpreter+path+stderr-merge, no write"
want no  "python3 read.py $GUARDED 2>/dev/null"    "interpreter+path+stderr-to-null, no write"
want no  "python3 read.py $GUARDED >&2"            "interpreter+path+fd-dup, no write"
want no  "node script.js $GUARDED 1>&2"            "node + fd-dup, no write"

echo
echo "── WINDOWS + QUOTED paths (added 2026-09-04) ─────────────────────────────"
# TWO defects, both DETECTION-side, both fixed in lib/bash_write_door.sh on 2026-09-04.
#
#  (1) `looks_like_path` tested only for "/" or a known extension. A native Windows path has
#      neither once it reaches this library as an INTERPRETER write, because the whole
#      expression is ONE token that ends in ")". So it was dropped, the caller received an
#      EMPTY target list, and every guard downstream read that as "nothing to check" and
#      exited 0. That is the exact shape that truncated a live project brief to zero bytes
#      on 2026-09-04 — the third such loss since 2026-08-30.
#  (2) the redirect scanner stopped at the first space, so ANY quoted target containing one
#      was truncated to an unmatchable fragment. ⚠ NOT Windows-specific: measured the same
#      day, `echo hi > "$HOME/My Notes/x/brief.md"` emitted the fragment up to the space. Posix installs with a
#      space in the path had this too.
#
# Measured against the pre-fix library that day: (1) returned nothing, (2) returned `D:\My`
# and a truncated fragment. Everything else in this file was already green and stayed green.
WIN="D:\Notes\state\projects\demo\brief.md"
WIN_SP="D:\My Notes\state\projects\demo\brief.md"
POSIX_SP="/notes/My Files/state/projects/demo/brief.md"

hits_exact() { bwd_write_targets "$2" | grep -Fxq "$1" && echo yes || echo no; }
hits_sub()   { bwd_write_targets "$2" | grep -Fq  "$1" && echo yes || echo no; }

wx() { # wx <exact|sub> <expected yes|no> <path> <command> <label>
  case "$1" in
    exact) got=$(hits_exact "$3" "$4") ;;
    sub)   got=$(hits_sub   "$3" "$4") ;;
  esac
  if [ "$got" = "$2" ]; then
    pass=$((pass+1)); printf '   ok   %s\n' "$5"
  else
    fail=$((fail+1)); printf '  FAIL  %s  (wanted %s, got %s)\n' "$5" "$2" "$got"
  fi
}

# the expensive direction FIRST, as everywhere else in this file
wx exact no "$WIN"      "cat \"$WIN\""                     "windows path, plain read"
wx exact no "$WIN"      "grep -n frame \"$WIN\""           "windows path, grep"
wx exact no "$WIN_SP"   "cat \"$WIN_SP\""                  "windows path with a space, plain read"
wx exact no "$WIN"      "python3 read.py \"$WIN\" 2>/dev/null" "windows path, interpreter with NO write call"

wx sub   yes "$WIN"     "python3 -c 'open(r\"$WIN\",\"w\").write(x)'" "WINDOWS interpreter write — the 2026-09-04 vector"
wx exact yes "$WIN"     "cat > $WIN"                       "windows redirect"
wx exact yes "$WIN"     "rm -f \"$WIN\""                   "windows rm"
wx exact yes "$WIN_SP"  "echo hi > \"$WIN_SP\""            "windows redirect, QUOTED with a space"
wx exact yes "$POSIX_SP" "echo hi > \"$POSIX_SP\""         "POSIX redirect, QUOTED with a space — not a windows bug"

echo
echo "── fail-closed ───────────────────────────────────────────────────────────"
if [ -z "$(bwd_write_targets '')" ]; then
  pass=$((pass+1)); printf '   ok   an empty command yields no targets\n'
else
  fail=$((fail+1)); printf '  FAIL  an empty command should yield nothing\n'
fi

echo
echo "── variable resolution (FIXCARD-CROSS-PROJECT-WRITE-VAR-PATHS, 2026-09-17) ────────────────"
# The incident: B="$HOME/.../_ClaudeOps"; cat >> "$B/plans/enforcement-layer.phase-2.plan.md"
# emitted the LITERAL, unexpanded "$B/plans/..." -- so acking the real absolute path (the only
# thing a person actually has to paste) could never match the hash of the literal string that was
# captured. Each case below is phrased so a reverted fix, OR a "fix" that silently resolves-and-
# passes-through on failure, visibly fails.

resolve_eq() { # resolve_eq <expected single line of output> <command> <label>
  got=$(bwd_write_targets "$2")
  if [ "$got" = "$1" ]; then
    pass=$((pass+1)); printf '   ok   %s\n' "$3"
  else
    fail=$((fail+1)); printf '  FAIL  %s  (wanted %s, got %s)\n' "$3" "$1" "$got"
  fi
}

resolve_sentinel() { # resolve_sentinel <$NAME as it should appear> <command> <label>
  got=$(bwd_write_targets "$2")
  case "$got" in
    *"__BWD_UNRESOLVED_VAR__"*"$1"*)
      pass=$((pass+1)); printf '   ok   %s\n' "$3" ;;
    *)
      fail=$((fail+1)); printf '  FAIL  %s  (wanted a sentinel naming %s, got: %s)\n' "$3" "$1" "$got" ;;
  esac
}

# 1. the card's own repro, resolved
resolve_eq "/tmp/proj-a/plans/x.plan.md" 'B="/tmp/proj-a"; cat >> "$B/plans/x.plan.md"' \
  "double-quoted same-command assignment resolves in the write target (card repro #1)"

# 2. undeclared var -> sentinel, never the raw literal, never nothing
got=$(bwd_write_targets 'cat >> "$UNDECLARED_VAR/plans/x.plan.md"')
if printf '%s\n' "$got" | grep -Fxq '$UNDECLARED_VAR/plans/x.plan.md'; then
  fail=$((fail+1)); printf '  FAIL  an undeclared var must never be emitted as a bare literal path line\n'
else
  pass=$((pass+1)); printf '   ok   an undeclared var is never emitted as a bare literal path line\n'
fi
resolve_sentinel '$UNDECLARED_VAR' 'cat >> "$UNDECLARED_VAR/plans/x.plan.md"' \
  "an undeclared var emits the __BWD_UNRESOLVED_VAR__ sentinel (card repro #2)"
if [ -n "$got" ]; then
  pass=$((pass+1)); printf '   ok   an undeclared var emits SOMETHING -- never silently nothing\n'
else
  fail=$((fail+1)); printf '  FAIL  an undeclared var emitted nothing -- a caller would read that as "no targets"\n'
fi

# 3. chained/shadowed assignment -- last one wins, same-command order respected
resolve_eq "/tmp/b/plans/x.plan.md" 'B="/tmp/a"; B="/tmp/b"; cat >> "$B/plans/x.plan.md"' \
  "a re-assignment shadows the earlier one -- last assignment wins (card repro #3)"

# literal path, unaffected by any of this
resolve_eq "$GUARDED" "cat > $GUARDED" "a literal path with no \$VAR at all is completely unaffected"

# a real prefix env-assignment (VAR=val cmd ...) is NOT mistaken for a bare NAME=value assignment,
# and the write it prefixes is still detected
want yes "FOO=/tmp cat file > $GUARDED" \
  "a prefix env-assignment before a real command is still scanned as a write"

# B=/x; cat >> "$B/f.md"  ->  /x/f.md
resolve_eq "/x/f.md" 'B=/x; cat >> "$B/f.md"' "unquoted RHS assignment resolves"

# export B=/x && echo >> $B/f  ->  /x/f  (export-prefixed, &&-chained, unquoted target)
resolve_eq "/x/f" 'export B=/x && echo >> $B/f' "export-prefixed assignment, &&-chained, resolves"

# ${B} brace form
resolve_eq "/x/f.md" 'B=/x; cat >> "${B}/f.md"' "brace form \${B} resolves"

# a variable defined AFTER its use is NOT retroactively resolved -- order matters, same as a real shell
got=$(bwd_write_targets 'cat >> "$B/f.md"; B=/x')
if printf '%s\n' "$got" | grep -Fxq "/x/f.md"; then
  fail=$((fail+1)); printf '  FAIL  a later assignment must not retroactively resolve an earlier use\n'
else
  pass=$((pass+1)); printf '   ok   a later assignment does not retroactively resolve an earlier use\n'
fi
resolve_sentinel '$B' 'cat >> "$B/f.md"; B=/x' \
  "a variable defined AFTER use emits the unresolved sentinel instead"

# command substitution in the RHS is NEVER evaluated -- no shell execution happens in this file at
# all, only text analysis. Mutation-provable: a "fix" that actually shells out to run $(pwd) would
# make this assert the real $PWD-based path, which this test explicitly rejects.
REAL_PWD="$(pwd)"
got=$(bwd_write_targets 'B=$(pwd); cat >> "$B/f.md"')
if printf '%s\n' "$got" | grep -Fxq "$REAL_PWD/f.md"; then
  fail=$((fail+1)); printf '  FAIL  a command-substitution RHS must never be executed or resolved\n'
else
  pass=$((pass+1)); printf '   ok   a command-substitution RHS ( \$(...) ) is never executed or resolved\n'
fi
resolve_sentinel '$B' 'B=$(pwd); cat >> "$B/f.md"' \
  "\$(...) command substitution in the RHS resolves to the unresolved sentinel"
resolve_sentinel '$B' 'B=`pwd`; cat >> "$B/f.md"' \
  "backtick command substitution in the RHS also resolves to the unresolved sentinel"

# the narrow inherited-var allowlist: HOME, USER, PWD -- and ONLY those three
HOME_TEST_VAL="/tmp/bwd-allowlist-test-$$"
got=$(HOME="$HOME_TEST_VAL" bwd_write_targets 'cat >> "$HOME/f.md"')
if [ "$got" = "$HOME_TEST_VAL/f.md" ]; then
  pass=$((pass+1)); printf '   ok   %s\n' "bare \$HOME resolves via the narrow inherited-var allowlist"
else
  fail=$((fail+1)); printf '  FAIL  %s  (wanted %s, got %s)\n' "bare \$HOME resolves via the narrow inherited-var allowlist" "$HOME_TEST_VAL/f.md" "$got"
fi
got=$(SOME_RANDOM_BUILD_VAR="/should/not/be/used" bwd_write_targets 'cat >> "$SOME_RANDOM_BUILD_VAR/f.md"')
case "$got" in
  *"__BWD_UNRESOLVED_VAR__"*)
    pass=$((pass+1)); printf '   ok   %s\n' "an arbitrary INHERITED env var outside the 3-name allowlist is NOT resolved" ;;
  *)
    fail=$((fail+1)); printf '  FAIL  %s  (got %s) -- the allowlist must never silently widen to the full environment\n' "an arbitrary inherited env var must not be resolved" "$got" ;;
esac

echo
printf 'RESULT: %d passed, %d failed.\n' "$pass" "$fail"
if [ "$fail" -eq 0 ]; then echo "BASH WRITE DOOR GREEN"; exit 0; fi
echo "BASH WRITE DOOR RED"; exit 1
