#!/bin/bash
# test_no_repoint_into_personal_code_guard.sh — deny-coverage suite for
# system/hooks/guard_no_repoint_into_personal_code.sh (B6.0 — this guard had NO test anywhere before
# this file.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# Nothing here actually creates a real symlink under ~/.claude/skills or ~/.claude/agents, or edits
# a real settings.json — every payload is fed to the guard's stdin as JSON text describing a
# HYPOTHETICAL tool call; the guard never executes the command it inspects, it only parses it.
#
# Invocation form matches the registered one:
#   bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_no_repoint_into_personal_code.sh"  (matcher: Bash|Write|Edit)

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_no_repoint_into_personal_code.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/no_repoint_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
# The person's setup, in a throwaway HOME: a personal-code pointer naming a folder that is NOT called anything
# in particular. The guard must learn the folder from the pointer alone.
PC="$SCRATCH/hm/my-own-code"
mkdir -p "$PC/.claude/skills/foo" "$SCRATCH/hm/.config/lifehack" "$SCRATCH/nopointer"
printf '%s\n' "$PC" > "$SCRATCH/hm/.config/lifehack/personal-code"
PASSED=0
FAILED=0

mkjson_bash() {
  T_CMD="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}}))'
}

mkjson_write() {  # mkjson_write <file_path> <content>
  T_PATH="$1" T_CONTENT="$2" python3 -c 'import os, json; print(json.dumps({"tool_name": "Write", "tool_input": {"file_path": os.environ["T_PATH"], "content": os.environ["T_CONTENT"]}}))'
}

run_guard() {
  cat | HOME="${T_HOME:-$SCRATCH/hm}" CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>"$ERRF"
}

allow() {
  local desc="$1" payload="$2"
  out=$(printf '%s' "$payload" | run_guard); rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.200s\n" "$(cat "$ERRF")"
    FAILED=$((FAILED + 1))
  fi
}

deny() {
  local desc="$1" payload="$2" must="$3"
  out=$(printf '%s' "$payload" | run_guard); rc=$?
  problems=""
  [ "$rc" -eq 2 ] || problems="${problems}rc=$rc(want 2);"
  [ -z "$out" ] || problems="${problems}stdout-not-empty;"
  errtxt="$(cat "$ERRF")"
  verdict=$(T_ERRF="$ERRF" python3 -c '
import os, json, sys
raw = open(os.environ["T_ERRF"]).read().strip()
if not raw:
    print("stderr-empty;"); sys.exit(0)
try:
    d = json.loads(raw)
except Exception as e:
    print("stderr-not-json(%s);" % type(e).__name__); sys.exit(0)
r = d.get("reason", "")
missing = [k for k in ("WHY", "REDIRECT", "RULE") if k not in r]
if d.get("decision") != "block":
    missing.append("decision!=block")
print(("missing:" + ",".join(missing) + ";") if missing else "")
')
  problems="$problems$verdict"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

echo "=== guard_no_repoint_into_personal_code.sh — ALLOW cases first ==="

allow "unrelated Bash command"                "$(mkjson_bash 'ls -la')"
allow "a symlink op unrelated to skills/agents" "$(mkjson_bash 'ln -s /tmp/a /tmp/b')"
allow "a re-point AT the plugin cache (the correct target)" \
  "$(mkjson_bash 'ln -sf /fakebase/.claude/plugins/cache/lifehack-brain/lifehack-brain/0.3.20/.claude/skills/foo /fakebase/.claude/skills/foo')"
allow "a settings.json write with no private-repo command"  \
  "$(mkjson_write /tmp/settings.json '{"hooks":{"PreToolUse":[{"hooks":[{"command":"bash ${CLAUDE_PLUGIN_ROOT}/system/hooks/guard_write_paths.sh"}]}]}}')"
allow "a Write to an unrelated file"          "$(mkjson_write /tmp/notes.md 'just some notes')"

echo
echo "=== DENY cases — every distinct protection this guard's header claims ==="

deny "ln -sf re-points a skills symlink at the private repo" \
  "$(mkjson_bash "ln -sf $PC/.claude/skills/foo /fakebase/.claude/skills/foo")" \
  "re-point"

deny "ln -s re-points an agents symlink at the private repo" \
  "$(mkjson_bash "ln -s $PC/.claude/agents/bar /fakebase/.claude/agents/bar")" \
  "re-point"

deny "the same re-point scripted inside a for-loop body" \
  "$(mkjson_bash "for f in foo bar; do ln -sf $PC/.claude/skills/\$f /fakebase/.claude/skills/\$f; done")" \
  "re-point"

deny "settings.json write registers a hook command inside the private repo" \
  "$(mkjson_write /tmp/settings.json "{\"hooks\":{\"PreToolUse\":[{\"hooks\":[{\"command\":\"bash $PC/system/hooks/guard_write_paths.sh\"}]}]}}")" \
  "re-point"

echo
echo "=== v2 3b-gaps side roads: variable-held paths and one-line scripts ==="
allow "variable-held ln pointing at the plugin cache" \
  "$(mkjson_bash 'TG=/fb/.claude/plugins/cache/lifehack-brain/lifehack-brain/0.4.0/.claude/skills/foo; LK=/fb/.claude/skills/foo; ln -sfn $TG $LK')"
allow "python one-liner symlink unrelated to skills/agents" \
  "$(mkjson_bash "python3 -c \"import os; os.symlink('/fb/a','/fb/b')\"")"
deny "ln -s through shell variables re-points a skills symlink at the private repo" \
  "$(mkjson_bash "TG=$PC/.claude/skills/foo; LK=/fb/.claude/skills/foo; ln -sfn \$TG \$LK")" \
  "re-point"
deny "python os.symlink one-liner re-points a skills symlink at the private repo" \
  "$(mkjson_bash "python3 -c \"import os; os.symlink('$PC/.claude/skills/foo','/fb/.claude/skills/foo')\"")" \
  "re-point"
echo
echo "=== part2: every spelling of the personal code folder, and a fresh install ==="
deny "settings.json hook command spelled with \$HOME" \
  "$(mkjson_write /tmp/settings.json '{"hooks":{"PreToolUse":[{"hooks":[{"command":"bash \"$HOME/my-own-code/system/hooks/x.sh\""}]}]}}')" \
  "re-point"
deny "ln target spelled with ~" \
  "$(mkjson_bash 'ln -sfn ~/my-own-code/.claude/skills/foo ~/.claude/skills/foo')" \
  "re-point"
allow "a sibling folder that only starts with the same name is not the personal folder" \
  "$(mkjson_bash "ln -sfn $PC-other/.claude/skills/foo /fb/.claude/skills/foo")"
T_HOME="$SCRATCH/nopointer" allow "no personal-code pointer: nothing private to re-point at" \
  "$(mkjson_bash "ln -sfn $PC/.claude/skills/foo /fb/.claude/skills/foo")"
if grep -qiE 'claude''ops' "$GUARD" "${GUARD%.sh}.py"; then
  printf "  FAIL  the guard names a private folder\n"; FAILED=$((FAILED + 1))
else
  printf "  PASS  the guard names no private folder\n"; PASSED=$((PASSED + 1))
fi
echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
