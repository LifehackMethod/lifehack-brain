#!/bin/bash
# Regression-lock for `system/hooks/guard_findings_write.sh`'s library-resolver
# scope (A1.4).
#
# ⚠ NOT a RED->GREEN fix in this session: verified 2026-09-16 that this defect was
# ALREADY FIXED on origin/main, well before this branch existed -- PR #165, commit
# 053d039 ("guard_findings_write: resolve its resolver from the plugin, not the
# session cwd"), merged 2026-09-09. That is the exact one-line change
# records/2026-09-14-lane-triage/triage.md §4 (A1.4) asks for:
#     export GFW_WINFOLD_LIB="$REPO/system/hooks/lib/winpath_fold.py"   (broken)
#  -> export GFW_WINFOLD_LIB="$_HOOKDIR/lib/winpath_fold.py"            (fixed)
# `git -C <repo> log --follow -- system/hooks/guard_findings_write.sh` on this
# branch's base shows 053d039 already in history; `grep GFW_WINFOLD_LIB` on the
# live file already reads $_HOOKDIR. So the triage's "public main/V2 still carry
# the broken line" (true as of 2026-09-14) is stale as of this branch's base --
# this is the SAME kind of subsumption check the task's own brief asked to make
# for A1.3, discovered independently for A1.4 during A1.0's pre-fix RED check.
#
# This suite is added anyway, as a plain regression lock (no guard code changed
# here) -- ported from
# records/2026-09-14-lane-triage/tests/test4_guard_findings_write.sh (nav's
# triage), adapted to the REGISTERED invocation form against the repo's own copy
# only (the original also ran the plugin 0.3.20 cache copy for comparison; that
# comparison is moot now that the repo copy matches it).
#
# THE SCENARIO: a session whose CLAUDE_PROJECT_DIR is NOT the harness repo (i.e.
# any session not rooted at the harness repo) must not have every Bash/Write/Edit
# call denied by this guard's library load, which happens unconditionally, before
# the guard even looks at whether the command touches state/findings/ or
# state/recommendations/.
# Run: bash system/hooks/tests/test_findings_write_resolver_scope.sh   (exit 0 = all pass)

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)" || exit 1
GUARD_REL="system/hooks/guard_findings_write.sh"

pass=0; fail=0
OUTSIDE=$(mktemp -d "${TMPDIR:-/tmp}/findings-write-resolver-test.XXXXXX") || exit 1
cleanup() { rm -rf "$OUTSIDE"; }
trap cleanup EXIT

BENIGN_BASH='{"tool_input":{"command":"ls -la"}}'

# The guard script itself is always located directly (this is what a REGISTERED
# invocation resolves to once ${CLAUDE_PLUGIN_ROOT}/${CLAUDE_PROJECT_DIR} has been
# substituted) -- CLAUDE_PROJECT_DIR is the variable under test here, exactly as in
# the original triage script, so it must NOT also be used to locate the guard file
# (a session whose CLAUDE_PROJECT_DIR is some unrelated folder still has this guard
# wired via ${CLAUDE_PLUGIN_ROOT} in hooks/hooks.json -- the script lives at a fixed
# location regardless of what CLAUDE_PROJECT_DIR names).
GUARD_ABS="$REPO_ROOT/$GUARD_REL"

invoke() { # invoke <payload-json> <CLAUDE_PROJECT_DIR value>
  printf '%s' "$1" | CLAUDE_PROJECT_DIR="$2" bash "$GUARD_ABS"
}

want_allow() { if [ "$1" -eq 0 ]; then pass=$((pass+1)); printf '   ok   %s (allowed)\n' "$2"; else fail=$((fail+1)); printf '  FAIL  %s (expected allow/exit 0, got %s)\n' "$2" "$1"; fi; }

echo "── A. ordinary command, CLAUDE_PROJECT_DIR = the harness repo itself -- must ALLOW ──"
invoke "$BENIGN_BASH" "$REPO_ROOT" >/dev/null 2>&1; want_allow "$?" "benign command, CLAUDE_PROJECT_DIR=harness repo"

echo
echo "── B. the A1.4 scenario: ordinary command, CLAUDE_PROJECT_DIR = an UNRELATED project -- must still ALLOW ──"
invoke "$BENIGN_BASH" "$OUTSIDE" >/dev/null 2>&1; want_allow "$?" "benign command, CLAUDE_PROJECT_DIR=outside project"

echo
printf 'RESULT: %d passed, %d failed.\n' "$pass" "$fail"
if [ "$fail" -eq 0 ]; then echo "FINDINGS WRITE RESOLVER-SCOPE GREEN (defect already fixed via PR #165 / 053d039, prior to this branch)"; exit 0; fi
echo "FINDINGS WRITE RESOLVER-SCOPE RED"; exit 1
