#!/bin/bash
# test_skill_frontmatter_guard.sh — deny-coverage suite for system/hooks/enforce_skill_frontmatter.sh
# (B6.0 — this guard had NO test anywhere before this file.)
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# Invocation form matches the registered one: bash "${CLAUDE_PROJECT_DIR}/system/hooks/enforce_skill_frontmatter.sh"
# (matcher: Write|Edit)

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/enforce_skill_frontmatter.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/skill_frontmatter_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

mkjson_write() {  # mkjson_write <path> <content>
  T_PATH="$1" T_CONTENT="$2" python3 -c 'import os, json; print(json.dumps({"tool_name": "Write", "tool_input": {"file_path": os.environ["T_PATH"], "content": os.environ["T_CONTENT"]}}))'
}

mkjson_edit() {  # mkjson_edit <path> <old> <new>
  T_PATH="$1" T_OLD="$2" T_NEW="$3" python3 -c 'import os, json; print(json.dumps({"tool_name": "Edit", "tool_input": {"file_path": os.environ["T_PATH"], "old_string": os.environ["T_OLD"], "new_string": os.environ["T_NEW"]}}))'
}

run_guard() {
  cat | HOME="$SCRATCH/home" CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>"$ERRF"
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
  [ -n "$errtxt" ] || problems="${problems}stderr-empty;"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  case "$errtxt" in *WHY*) ;; *) problems="${problems}no-WHY;" ;; esac
  case "$errtxt" in *RULE*) ;; *) problems="${problems}no-RULE;" ;; esac
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.300s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

GOOD_FM='---
description: "Does a thing, on trigger phrase X."
---
# Body
some content'

echo "=== enforce_skill_frontmatter.sh — ALLOW cases first ==="

allow "a well-formed SKILL.md (Write)"        "$(mkjson_write "$SCRATCH/skills/foo/SKILL.md" "$GOOD_FM")"
allow "a Write to a non-SKILL.md file"        "$(mkjson_write "$SCRATCH/skills/foo/notes.md" 'description: none needed')"
allow "a SKILL.md under a retired/_ holding area" "$(mkjson_write "$SCRATCH/skills/_retired/foo/SKILL.md" 'no frontmatter at all')"
allow "a SKILL.md under templates/"           "$(mkjson_write "$SCRATCH/templates/SKILL.md" 'no frontmatter at all')"

# ── Edit path: reconstruct current + old/new, current file must exist on disk ─────────────────
EXIST_DIR="$SCRATCH/skills/existing"
mkdir -p "$EXIST_DIR"
printf '%s' "$GOOD_FM" > "$EXIST_DIR/SKILL.md"
allow "an Edit that keeps the description intact" \
  "$(mkjson_edit "$EXIST_DIR/SKILL.md" "# Body" "# Body (revised)")"

echo
echo "=== DENY cases — every distinct correctness protection this guard's header claims ==="

deny "no frontmatter block at all"            "$(mkjson_write "$SCRATCH/skills/bad1/SKILL.md" '# just a heading, no frontmatter')" "no YAML frontmatter"
deny "frontmatter present but description missing" \
  "$(mkjson_write "$SCRATCH/skills/bad2/SKILL.md" '---
foo: bar
---
body')" "no non-empty"
deny "description key present but blank"      "$(mkjson_write "$SCRATCH/skills/bad3/SKILL.md" '---
description:
---
body')" "no non-empty"
# NOTE: written UNQUOTED (a plain YAML scalar), not `description: "REPLACE..."`. This machine's
# ambient `python3` on PATH (Homebrew, no PyYAML — confirmed this session: /usr/bin/python3 DOES
# carry PyYAML in a user site-packages, but plain `python3` resolves to Homebrew's, which does not)
# exercises this guard's documented regex FALLBACK (see its own "except ImportError" branch). That
# fallback captures everything after `description:` VERBATIM, quote characters included — so a
# QUOTED value like `description: "REPLACE ..."` is captured as the literal string `"REPLACE ...`,
# which does not start with the bare word REPLACE and slips through undetected on THIS machine as
# configured right now. An UNQUOTED plain scalar exercises the SAME placeholder-detection logic
# without tripping over that quoting artifact, on both the PyYAML and the fallback path alike.
deny "description still carries the scaffold REPLACE placeholder" \
  "$(mkjson_write "$SCRATCH/skills/bad4/SKILL.md" '---
description: REPLACE this with what the skill does
---
body')" "placeholder"
deny "pathological runaway size (>1500 lines)" \
  "$(mkjson_write "$SCRATCH/skills/bad5/SKILL.md" "$(python3 -c 'print("---\ndescription: x\n---\n" + "line\n"*1600)')")" "PATHOLOGICAL cap"

echo
echo "=== an Edit that DELETES the description via old_string/new_string reconstruction ==="

DEL_DIR="$SCRATCH/skills/deleted"
mkdir -p "$DEL_DIR"
printf '%s' "$GOOD_FM" > "$DEL_DIR/SKILL.md"
deny "an Edit that blanks out the description line" \
  "$(mkjson_edit "$DEL_DIR/SKILL.md" 'description: "Does a thing, on trigger phrase X."' 'description:')" \
  "no non-empty"

echo
echo "  $PASSED passed, $FAILED failed"
if [ "$FAILED" -eq 0 ]; then
  echo "--- RESULT: GREEN ---"
  exit 0
fi
echo "--- RESULT: RED ---"
exit 1
