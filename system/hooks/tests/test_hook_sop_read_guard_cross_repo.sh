#!/bin/bash
# test_hook_sop_read_guard_cross_repo.sh — R2 Part A regression suite.
#
# Proves guard_hook_sop_read.sh resolves its register-backed switch from the WRITE
# TARGET's own repo (git toplevel of dirname(FILE_PATH), already realpath'd) for a
# Write/Edit/MultiEdit call — never from this hook's own hookdir/_REPO, never from
# CLAUDE_PROJECT_DIR/cwd. See R2-SPEC-A-plugin-guard.md, Decisions 1-5.
#
# The guard-under-test is copied to a directory OUTSIDE any git repo — a
# plugin-cache-like location — for every case below, so this suite genuinely
# exercises the plugin shape the bug was measured in (C1.2), not the same-repo
# fallback that system/hooks/tests/test_hook_edit_switch.sh already covers.
#
# Run: bash system/hooks/tests/test_hook_sop_read_guard_cross_repo.sh

set -u

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
REAL_GUARD="$REPO/system/hooks/guard_hook_sop_read.sh"
REAL_SWITCH_STATE="$REPO/system/register/switch_state.py"

if [ ! -r "$REAL_GUARD" ]; then
  echo "MISSING: $REAL_GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi
if [ ! -r "$REAL_SWITCH_STATE" ]; then
  echo "MISSING: $REAL_SWITCH_STATE — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/hook_sop_read_cross_repo_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT

PASSED=0
FAILED=0

# ── the guard under test lives OUTSIDE any git repo (plugin-cache-like) ──────────────────
PLUGIN_DIR="$SCRATCH/plugin-cache-like/lifehack-brain"
mkdir -p "$PLUGIN_DIR/system/hooks"
cp "$REAL_GUARD" "$PLUGIN_DIR/system/hooks/guard_hook_sop_read.sh"
chmod +x "$PLUGIN_DIR/system/hooks/guard_hook_sop_read.sh"
GUARD="$PLUGIN_DIR/system/hooks/guard_hook_sop_read.sh"

write_register_row() {
  # write_register_row <register_path> <state> <expiry-or-null>
  local reg="$1" state="$2" expiry="$3"
  T_REG="$reg" T_STATE="$state" T_EXPIRY="$expiry" python3 -c '
import json, os
row = {
  "id": "hook:public:/system/hooks/guard_hook_sop_read.sh@PreToolUse:Bash|Write|Edit",
  "type": "hook", "repo": "public",
  "path": "/system/hooks/guard_hook_sop_read.sh",
  "exists": True, "sha": "010a8c21",
  "needs": [], "returns": [],
  "cost_bytes": None, "cost_ms": None,
  "event": "PreToolUse", "matcher": "Bash|Write|Edit", "args": "",
  "status": "Checking the hook SOP was read first...",
  "surfaces": ["settings", "plugin"],
  "status_conflicts": [], "if": None,
  "launch_mode": "both", "group": None,
  "state": os.environ["T_STATE"],
  "expiry": None if os.environ["T_EXPIRY"] == "null" else os.environ["T_EXPIRY"],
}
with open(os.environ["T_REG"], "w", encoding="utf-8") as f:
    f.write(json.dumps(row, sort_keys=True) + "\n")
'
}

# make_harness_repo <name> <state> <expiry-or-null> — a REAL git repo carrying all
# three files Decision 2 requires, plus a target file (system/hooks/x.sh) to edit.
make_harness_repo() {
  local name="$1" state="$2" expiry="$3"
  local r="$SCRATCH/$name"
  mkdir -p "$r/system/hooks" "$r/system/register"
  ( cd "$r" && git init -q && git config user.email test@example.com && git config user.name test )
  cp "$REAL_GUARD" "$r/system/hooks/guard_hook_sop_read.sh"
  cp "$REAL_SWITCH_STATE" "$r/system/register/switch_state.py"
  printf 'echo target\n' > "$r/system/hooks/x.sh"
  write_register_row "$r/system/register/register.jsonl" "$state" "$expiry"
  echo "$r"
}

mkjson_write() {
  # mkjson_write <tool_name> <file_path> <session_id>
  T_TOOL="$1" T_PATH="$2" T_SID="$3" python3 -c '
import os, json
print(json.dumps({
    "tool_name": os.environ["T_TOOL"],
    "tool_input": {"file_path": os.environ["T_PATH"]},
    "session_id": os.environ["T_SID"],
}))
'
}

fresh_home() { mktemp -d "$SCRATCH/home.XXXXXX"; }

run_guard() {
  # run_guard <file_path> <today> [tool_name]
  local file_path="$1" today="$2" tool="${3:-Write}"
  local home; home="$(fresh_home)"
  local sid="test-$RANDOM-$$"
  mkjson_write "$tool" "$file_path" "$sid" \
    | HOME="$home" CLAUDE_CODE_SESSION_ID="$sid" LHB_REGISTER_TODAY="$today" bash "$GUARD" \
    2>"$SCRATCH/stderr.txt" 1>"$SCRATCH/stdout.txt"
  return $?
}

allow() {
  local desc="$1" file_path="$2" today="${3:-2026-09-16}" tool="${4:-Write}"
  local rc=0
  run_guard "$file_path" "$today" "$tool" || rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s, want 0) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.300s\n" "$(cat "$SCRATCH/stderr.txt")"
    FAILED=$((FAILED + 1))
  fi
}

allow_with_text() {
  local desc="$1" file_path="$2" must="$3" today="${4:-2026-09-16}" tool="${5:-Write}"
  local rc=0
  run_guard "$file_path" "$today" "$tool" || rc=$?
  local problems=""
  [ "$rc" -eq 0 ] || problems="${problems}rc=$rc(want 0);"
  local errtxt; errtxt="$(cat "$SCRATCH/stderr.txt")"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  if [ -z "$problems" ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

deny() {
  local desc="$1" file_path="$2" must="$3" today="${4:-2026-09-16}" tool="${5:-Write}"
  local rc=0
  run_guard "$file_path" "$today" "$tool" || rc=$?
  local problems=""
  [ "$rc" -eq 2 ] || problems="${problems}rc=$rc(want 2);"
  local errtxt; errtxt="$(cat "$SCRATCH/stderr.txt")"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

TODAY="2026-09-16"
FUTURE="2026-10-01"
PAST="2026-09-01"

REPO_ACTIVE="$(make_harness_repo repo-active active null)"
REPO_SUSPENDED="$(make_harness_repo repo-suspended suspended "$FUTURE")"
REPO_EXPIRED="$(make_harness_repo repo-expired suspended "$PAST")"

printf "=== guard_hook_sop_read.sh — R2 Part A cross-repo switch tests (guard runs from a plugin-cache-like dir OUTSIDE any repo) ===\n\n"

echo "--- sanity: non-hook-plane edit is untouched regardless of register ---"
allow "edit outside the hook plane -> untouched, no register consulted" "$REPO_ACTIVE/README.md" "$TODAY"

echo
echo "--- case 1: target repo active -> BLOCK ---"
deny "target repo active -> BLOCK" "$REPO_ACTIVE/system/hooks/x.sh" "BLOCKED" "$TODAY"

echo
echo "--- case 2: target repo suspended+unexpired -> ALLOW (+NOTICE) [the fix; C1.2 as a unit test] ---"
allow_with_text "target repo suspended+unexpired -> ALLOW with NOTICE" "$REPO_SUSPENDED/system/hooks/x.sh" "NOTICE" "$TODAY"

echo
echo "--- case 3: target repo suspended+EXPIRED -> BLOCK + ALARM ---"
deny "target repo suspended EXPIRED -> BLOCK + ALARM" "$REPO_EXPIRED/system/hooks/x.sh" "EXPIRY HAS PASSED" "$TODAY"

echo
echo "--- case 4: spoofed dir (register.jsonl present, switch_state.py MISSING) fails Decision 2 -> BLOCK ---"
SPOOF_DIR="$SCRATCH/repo-spoof"
mkdir -p "$SPOOF_DIR/system/hooks" "$SPOOF_DIR/system/register"
( cd "$SPOOF_DIR" && git init -q && git config user.email test@example.com && git config user.name test )
cp "$REAL_GUARD" "$SPOOF_DIR/system/hooks/guard_hook_sop_read.sh"
# switch_state.py deliberately OMITTED — data file (register.jsonl) with no mechanism.
printf 'echo target\n' > "$SPOOF_DIR/system/hooks/x.sh"
write_register_row "$SPOOF_DIR/system/register/register.jsonl" suspended "$FUTURE"
deny "spoofed dir (register present, switch_state.py missing) fails Decision 2 -> BLOCK" "$SPOOF_DIR/system/hooks/x.sh" "BLOCKED" "$TODAY"

echo
echo "--- case 4b: spoofed dir (register.jsonl present, the guard itself MISSING) fails Decision 2 -> BLOCK ---"
SPOOF2_DIR="$SCRATCH/repo-spoof2"
mkdir -p "$SPOOF2_DIR/system/hooks" "$SPOOF2_DIR/system/register"
( cd "$SPOOF2_DIR" && git init -q && git config user.email test@example.com && git config user.name test )
cp "$REAL_SWITCH_STATE" "$SPOOF2_DIR/system/register/switch_state.py"
# guard_hook_sop_read.sh deliberately OMITTED at this target repo — mechanism half missing.
printf 'echo target\n' > "$SPOOF2_DIR/system/hooks/x.sh"
write_register_row "$SPOOF2_DIR/system/register/register.jsonl" suspended "$FUTURE"
deny "spoofed dir (register present, guard itself missing) fails Decision 2 -> BLOCK" "$SPOOF2_DIR/system/hooks/x.sh" "BLOCKED" "$TODAY"

echo
echo "--- case 5: cross-repo — suspension declared in repo X, target physically inside repo Y(active) -> DENY (never reads X's register) ---"
deny "cross-repo: X suspended, Y(active) target -> DENY" "$REPO_ACTIVE/system/hooks/x.sh" "BLOCKED" "$TODAY"

echo
echo "--- case 5b: target inside the plugin-cache-like dir itself (no repo at all) -> DENY ---"
printf 'echo target\n' > "$PLUGIN_DIR/system/hooks/plugin_target.sh"
deny "target inside the plugin-cache-like dir itself -> DENY" "$PLUGIN_DIR/system/hooks/plugin_target.sh" "BLOCKED" "$TODAY"

echo
echo "--- case 6: symlink in a SUSPENDED repo pointing at a file physically in an ACTIVE repo -> judged by real location -> DENY ---"
ln -s "$REPO_ACTIVE/system/hooks/x.sh" "$REPO_SUSPENDED/system/hooks/escape_link.sh"
deny "symlink escapes suspended repo into active repo -> DENY (proves Decision 3)" "$REPO_SUSPENDED/system/hooks/escape_link.sh" "BLOCKED" "$TODAY"

echo
echo "--- case 7: target repo has NO register.jsonl -> default active -> BLOCK ---"
NOREG_DIR="$SCRATCH/repo-no-register"
mkdir -p "$NOREG_DIR/system/hooks" "$NOREG_DIR/system/register"
( cd "$NOREG_DIR" && git init -q && git config user.email test@example.com && git config user.name test )
cp "$REAL_GUARD" "$NOREG_DIR/system/hooks/guard_hook_sop_read.sh"
cp "$REAL_SWITCH_STATE" "$NOREG_DIR/system/register/switch_state.py"
printf 'echo target\n' > "$NOREG_DIR/system/hooks/x.sh"
# register.jsonl deliberately absent.
deny "target repo has no register.jsonl -> default active -> DENY" "$NOREG_DIR/system/hooks/x.sh" "BLOCKED" "$TODAY"

echo
echo "--- case 7b: target repo's register.jsonl is malformed (not JSON) -> fail safe -> BLOCK ---"
MALFORMED_DIR="$(make_harness_repo repo-malformed active null)"
printf 'this is not json\n' > "$MALFORMED_DIR/system/register/register.jsonl"
deny "malformed register.jsonl -> fail safe -> DENY" "$MALFORMED_DIR/system/hooks/x.sh" "BLOCKED" "$TODAY"

echo
echo "--- MultiEdit tool_name takes the same target-repo path as Write/Edit ---"
allow_with_text "MultiEdit against a suspended repo -> ALLOW with NOTICE" "$REPO_SUSPENDED/system/hooks/x.sh" "NOTICE" "$TODAY" "MultiEdit"

echo ""
echo "$PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
else
  echo "--- RESULT: RED ---"
  exit 1
fi
