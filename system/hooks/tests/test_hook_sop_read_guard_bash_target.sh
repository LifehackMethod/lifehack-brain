#!/bin/bash
# test_hook_sop_read_guard_bash_target.sh — R2-C regression suite.
#
# Proves guard_hook_sop_read.sh resolves its register-backed switch from a BASH-SHAPED write's
# own target repo(s) too -- not just Write/Edit (R2 Part A) -- reusing the SAME tokenizer that
# already finds a hook-plane target inside a Bash command (the one that decides IS_WRITE), never
# a second parser. See R2-SPEC-A-plugin-guard.md Decisions 1-5 (Decision 5 is the limit R2-C
# removes) and the C1.2 live-verify failure this closes
# (handoff-bundles/2026-09-16-round-4/C1-RESULTS-K1.md).
#
# The guard-under-test is copied to a directory OUTSIDE any git repo -- a plugin-cache-like
# location -- for every case below, exactly like test_hook_sop_read_guard_cross_repo.sh does for
# the Write/Edit path, so this suite genuinely exercises the plugin shape the bug was measured in
# (C1.2), never the same-repo fallback.
#
# Run: bash system/hooks/tests/test_hook_sop_read_guard_bash_target.sh

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

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/hook_sop_read_bash_target_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT

PASSED=0
FAILED=0

# ── the guard under test lives OUTSIDE any git repo (plugin-cache-like) ──────────────────
PLUGIN_DIR="$SCRATCH/plugin-cache-like/lifehack-brain"
mkdir -p "$PLUGIN_DIR/system/hooks"
cp "$REAL_GUARD" "$PLUGIN_DIR/system/hooks/guard_hook_sop_read.sh"
chmod +x "$PLUGIN_DIR/system/hooks/guard_hook_sop_read.sh"
GUARD="$PLUGIN_DIR/system/hooks/guard_hook_sop_read.sh"

write_register_rows() {
  # write_register_rows <register_path> <state> <expiry-or-null>
  # ALWAYS writes TWO rows (the guard's own + a decoy) so a pass can never be explained by the
  # register comparing its own wiring to itself -- the task's own mutation-provability bar.
  local reg="$1" state="$2" expiry="$3"
  T_REG="$reg" T_STATE="$state" T_EXPIRY="$expiry" python3 -c '
import json, os
row = {
  "id": "hook:public:/system/hooks/guard_hook_sop_read.sh@PreToolUse:Bash|Write|Edit",
  "type": "hook", "repo": "public",
  "path": "/system/hooks/guard_hook_sop_read.sh",
  "exists": True, "sha": "863de7d2",
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
decoy = dict(row)
decoy["id"] = "hook:public:/system/hooks/guard_write_paths.sh@PreToolUse:Bash"
decoy["path"] = "/system/hooks/guard_write_paths.sh"
decoy["state"] = "active"
decoy["expiry"] = None
with open(os.environ["T_REG"], "w", encoding="utf-8") as f:
    f.write(json.dumps(row, sort_keys=True) + "\n")
    f.write(json.dumps(decoy, sort_keys=True) + "\n")
'
}

# make_harness_repo <name> <state> <expiry-or-null> — a REAL git repo carrying all three files
# Decision 2 requires, plus a target file (system/hooks/scratch-c1.txt) to write into (the exact
# shape of the C1.2 live-verify probe).
make_harness_repo() {
  local name="$1" state="$2" expiry="$3"
  local r="$SCRATCH/$name"
  mkdir -p "$r/system/hooks" "$r/system/register"
  ( cd "$r" && git init -q && git config user.email test@example.com && git config user.name test )
  cp "$REAL_GUARD" "$r/system/hooks/guard_hook_sop_read.sh"
  cp "$REAL_SWITCH_STATE" "$r/system/register/switch_state.py"
  printf 'baseline\n' > "$r/system/hooks/scratch-c1.txt"
  write_register_rows "$r/system/register/register.jsonl" "$state" "$expiry"
  echo "$r"
}

mkjson_bash() {
  # mkjson_bash <command> <session_id> <cwd>
  T_CMD="$1" T_SID="$2" T_CWD="$3" python3 -c '
import os, json
print(json.dumps({
    "tool_name": "Bash",
    "tool_input": {"command": os.environ["T_CMD"]},
    "session_id": os.environ["T_SID"],
    "cwd": os.environ["T_CWD"],
}))
'
}

fresh_home() { mktemp -d "$SCRATCH/home.XXXXXX"; }

run_guard() {
  # run_guard <cmd> <cwd> <today>
  local cmd="$1" cwd="$2" today="$3"
  local home; home="$(fresh_home)"
  local sid="test-$RANDOM-$$"
  mkjson_bash "$cmd" "$sid" "$cwd" \
    | HOME="$home" LHB_REGISTER_TODAY="$today" bash "$GUARD" \
    2>"$SCRATCH/stderr.txt" 1>"$SCRATCH/stdout.txt"
  return $?
}

allow_with_text() {
  local desc="$1" cmd="$2" cwd="$3" must="$4" today="${5:-2026-09-16}"
  local rc=0
  run_guard "$cmd" "$cwd" "$today" || rc=$?
  local problems=""
  [ "$rc" -eq 0 ] || problems="${problems}rc=$rc(want 0);"
  local errtxt; errtxt="$(cat "$SCRATCH/stderr.txt")"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  if [ -z "$problems" ]; then
    printf " PASS allow %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf " FAIL allow %s ->%s\n" "$desc" "$problems"
    printf " stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

deny() {
  local desc="$1" cmd="$2" cwd="$3" must="$4" today="${5:-2026-09-16}"
  local rc=0
  run_guard "$cmd" "$cwd" "$today" || rc=$?
  local problems=""
  [ "$rc" -eq 2 ] || problems="${problems}rc=$rc(want 2);"
  local errtxt; errtxt="$(cat "$SCRATCH/stderr.txt")"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  if [ -z "$problems" ]; then
    printf " PASS deny %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf " FAIL deny %s ->%s\n" "$desc" "$problems"
    printf " stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

TODAY="2026-09-16"
FUTURE="2026-10-01"
PAST="2026-09-01"

REPO_ACTIVE="$(make_harness_repo repo-active active null)"
REPO_SUSPENDED="$(make_harness_repo repo-suspended suspended "$FUTURE")"
REPO_EXPIRED="$(make_harness_repo repo-expired suspended "$PAST")"
ELSEWHERE="$SCRATCH/elsewhere-nonrepo"
mkdir -p "$ELSEWHERE"

printf "=== guard_hook_sop_read.sh — R2-C Bash-target switch tests (guard runs from a plugin-cache-like dir OUTSIDE any repo) ===\n\n"

echo "--- case 1: Bash write, RELATIVE target, cwd=suspended+unexpired repo -> ALLOW (+NOTICE) [C1.2 as a unit test] ---"
allow_with_text "relative redirect target, cwd=suspended repo" \
  "echo '# c1.2 probe' >> system/hooks/scratch-c1.txt" "$REPO_SUSPENDED" "NOTICE" "$TODAY"

echo
echo "--- case 2: same, but the suspension is EXPIRED -> BLOCK + ALARM ---"
deny "relative redirect target, cwd=EXPIRED-suspension repo" \
  "echo '# c1.2 probe' >> system/hooks/scratch-c1.txt" "$REPO_EXPIRED" "EXPIRY HAS PASSED" "$TODAY"

echo
echo "--- case 3: cwd = a non-Harness git repo with a system/hooks dir (register.jsonl present, switch_state.py MISSING) -> fails Decision 2 -> BLOCK ---"
SPOOF_DIR="$SCRATCH/repo-spoof"
mkdir -p "$SPOOF_DIR/system/hooks" "$SPOOF_DIR/system/register"
( cd "$SPOOF_DIR" && git init -q && git config user.email test@example.com && git config user.name test )
cp "$REAL_GUARD" "$SPOOF_DIR/system/hooks/guard_hook_sop_read.sh"
# switch_state.py deliberately OMITTED -- data file (register.jsonl) with no mechanism.
printf 'baseline\n' > "$SPOOF_DIR/system/hooks/scratch-c1.txt"
write_register_rows "$SPOOF_DIR/system/register/register.jsonl" suspended "$FUTURE"
deny "cwd is a non-Harness repo (spoofed register, no switch_state.py) -> BLOCK" \
  "echo '# probe' >> system/hooks/scratch-c1.txt" "$SPOOF_DIR" "BLOCKED" "$TODAY"

echo
echo "--- case 4: ABSOLUTE target into the suspended repo, cwd ELSEWHERE entirely -> ALLOW (cwd is irrelevant to an absolute target) ---"
allow_with_text "absolute target in suspended repo, cwd=unrelated non-repo dir" \
  "echo '# c1.2 probe' >> $REPO_SUSPENDED/system/hooks/scratch-c1.txt" "$ELSEWHERE" "NOTICE" "$TODAY"

echo
echo "--- case 5: two targets in two DIFFERENT repos, one suspended -> targets disagree -> no lift -> BLOCK ---"
deny "two targets, two repos (one suspended, one active) -> BLOCK" \
  "cp $REPO_SUSPENDED/system/hooks/scratch-c1.txt $REPO_ACTIVE/system/hooks/scratch-c1.txt" "$ELSEWHERE" "BLOCKED" "$TODAY"

echo
echo "--- case 6: is a 'cd' INSIDE the command tracked? NO -- documented, not implemented. A relative target always"
echo "    resolves against the payload's own cwd, never an embedded cd's target -- so this is BLOCKED (cwd here is"
echo "    NOT the suspended repo, even though the command cd's into it before writing). ---"
deny "cd <suspended repo> && relative write -- cd is NOT tracked -> BLOCK" \
  "cd $REPO_SUSPENDED && echo '# probe' >> system/hooks/scratch-c1.txt" "$ELSEWHERE" "BLOCKED" "$TODAY"

echo
echo "--- case 7: unparseable command (unbalanced quote -> shlex ValueError -> regex fallback, no resolved target at all) -> BLOCK ---"
deny "unbalanced quote -> tokenizer fails -> regex fallback, no target -> BLOCK" \
  "echo 'unterminated >> system/hooks/scratch-c1.txt" "$REPO_SUSPENDED" "BLOCKED" "$TODAY"

echo ""
echo "$PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
else
  echo "--- RESULT: RED ---"
  exit 1
fi
