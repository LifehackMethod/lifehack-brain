#!/bin/bash
# test_no_live_substitution_in_python_blocks.sh — regression lint: no live command substitution
# inside a python3 (or python) -c argument that bash double-quotes, anywhere under system/hooks/.
#
# WHY THIS EXISTS. guard_hook_sop_read.sh's heredoc-fix comment used to carry a BACKTICKED example
# (a tee-into-the-plan-file illustration) sitting inside such a bash double-quoted -c argument.
# Bash resolves backticks as live command substitution while it is still parsing that double-quoted
# string — it does not know or care that the string's contents were meant for Python, only bash's
# own quoting rules apply, and they apply before Python ever sees the text. That one comment ran
# a real tee into ~/.claude/plans/lifehack-migration.plan.md via an empty heredoc and truncated the
# plan file to 28 bytes — four times, once per guard invocation, measured 2026-09-16. An unescaped
# dollar-paren substitution is the identical hazard. This lint forbids the CLASS: any backtick or
# unescaped dollar-paren between a python -c double-quote opener and its closing quote, anywhere
# under system/hooks/.
#
# This file is BOTH the lint (scans the real tree) AND its own self-test (a fixture built fresh in
# a tempdir, never in the repo tree, proves the scanner actually catches the shape and does not cry
# wolf on an escaped or clean one).
#
# CAUTION TO ANY FUTURE EDITOR OF THIS FILE: never spell out, in prose or example, the literal
# sequence  -c  followed by a double-quote character  --  that pair, however it arrives (even a
# markdown-style single-backtick code span split across two lines), is indistinguishable from a
# live opener to the dumb line-scanner below, and system/hooks/tests/ is itself inside the tree
# the real scan walks. Illustrate with single quotes in prose instead (never matches the double-
# quote opener the scanner and bash both key off). The fixture text below is assembled from parts
# at RUNTIME (printf + %s), never written as contiguous literal source, for the same reason. And
# the scanner itself is fed to python3 over STDIN via a single-quoted heredoc, never via a -c
# argument — that would make this very file the thing it scans for.
#
# Run: bash system/hooks/tests/test_no_live_substitution_in_python_blocks.sh   (exit 0 = all pass)

HERE="$(cd "$(dirname "$0")/.." && pwd)"          # system/hooks
REPO_ROOT="$(cd "$HERE/../.." && pwd)"

pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }

# The scanner: reads directories from argv, walks *.sh recursively, finds every python3/python -c
# double-quote opener, and reports file:line for a backtick or an unescaped dollar-paren anywhere
# inside that double-quoted block (which may run across several source lines -- the closing quote
# is found the same way bash would find it: the first UNESCAPED double-quote).
scan() {
  python3 - "$@" <<'PY'
import sys, re, glob, os

def dq_end(s):
    i = 0
    while i < len(s):
        if s[i] == '\\':
            i += 2
            continue
        if s[i] == '"':
            return i
        i += 1
    return -1

hits = []
for root in sys.argv[1:]:
    for f in sorted(glob.glob(os.path.join(root, "**", "*.sh"), recursive=True)):
        lines = open(f, encoding="utf-8", errors="replace").read().split("\n")
        i = 0
        while i < len(lines):
            m = re.search(r'python3?\s+-c\s+"', lines[i])
            if m:
                rest = lines[i][m.end():]
                e = dq_end(rest)
                seg = [(i, rest if e < 0 else rest[:e])]
                j = i
                while e < 0 and j + 1 < len(lines):
                    j += 1
                    e = dq_end(lines[j])
                    seg.append((j, lines[j] if e < 0 else lines[j][:e]))
                for n, t in seg:
                    if '`' in t or re.search(r'(?<!\\)\$\(', t):
                        hits.append("%s:%d: %s" % (f, n + 1, t.strip()[:110]))
                i = j
            i += 1

for h in hits:
    print(h)
print("# hits=%d" % len(hits))
PY
}

SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/dqscan.XXXXXX")"
trap 'rm -rf "$SANDBOX"' EXIT
mkdir -p "$SANDBOX/fixture"

# Build the fixtures from parts -- see the CAUTION note above on why this can't be literal text.
dq='"'
bt='`'
printf '#!/bin/bash\n' > "$SANDBOX/fixture/bad.sh"
printf 'python3 -c %simport sys; x = %sdate%s%s\n' "$dq" "$bt" "$bt" "$dq" >> "$SANDBOX/fixture/bad.sh"

printf '#!/bin/bash\n' > "$SANDBOX/fixture/clean.sh"
printf 'python3 -c %simport sys%s\n' "$dq" "$dq" >> "$SANDBOX/fixture/clean.sh"
# escaped dollar-paren equivalent -- backslash then dollar-paren must NOT trip the lint (mirrors
# the reference scanner's negative lookbehind on an escaped one). Built the same way, from parts.
bs='\'; d='$'; lp='('; rp=')'
printf 'python3 -c %simport sys; note = %s%s%sescaped%s%s\n' "$dq" "$bs" "$d" "$lp" "$rp" "$dq" >> "$SANDBOX/fixture/clean.sh"

echo "── self-test: the scanner must catch the shape on a fixture, and never cry wolf ──────────"

fixture_out="$(scan "$SANDBOX/fixture")"

echo "$fixture_out" | grep -q "bad\.sh:2:" \
  && ok || bad "fixture catches the backtick" "no hit reported for fixture/bad.sh:2 -- got:\n$fixture_out"

echo "$fixture_out" | grep -q "clean\.sh" \
  && bad "fixture: false positive" "clean.sh (plain + escaped dollar-paren) was flagged -- got:\n$fixture_out" || ok

hits_line="$(echo "$fixture_out" | grep '^# hits=')"
[ "$hits_line" = "# hits=1" ] \
  && ok || bad "fixture hit count" "expected exactly 1 hit (bad.sh only), got: $hits_line"

echo "── the real tree: system/hooks/, already fixed, must show zero hits ──────────────────────"

real_out="$(scan "$HERE")"
real_hits_line="$(echo "$real_out" | grep '^# hits=')"
if [ "$real_hits_line" = "# hits=0" ]; then
  ok
else
  bad "real tree is clean" "system/hooks/ reported live substitution inside a python -c block:\n$real_out"
fi

echo
if [ "$fail" = 0 ]; then echo "RESULT: $pass passed, 0 failed."; echo "NO-LIVE-SUBSTITUTION LINT GREEN"; exit 0
else echo "RESULT: $pass passed, $fail failed."; exit 1
fi
