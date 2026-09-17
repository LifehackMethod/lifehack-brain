#!/bin/bash
# test_plans_truncation_floor_guard.sh — deny-coverage suite for
# system/hooks/guard_plans_truncation_floor.sh (K4, enforcement-layer Phase 2 plan).
#
# WHY THIS GUARD EXISTS: on 2026-09-16 a 493 KB plan file
# (~/.claude/plans/lifehack-migration.plan.md) was flattened to 28 bytes three times in
# one morning; nothing refused it because nothing watched the directory. This suite proves
# the DoD verbatim: "a simulated 493 KB -> 28 B rewrite is refused with the backup made
# first", plus the required companions -- a normal edit that keeps/grows size is allowed,
# a new plan file's creation is allowed, and the documented override path works.
#
# ⚠ ALLOW CASES FIRST — see hook-contract.md.
#
# Invocation form matches the registered one:
#   bash "${CLAUDE_PROJECT_DIR}/system/hooks/guard_plans_truncation_floor.sh"
#   (matcher: Write|Edit|MultiEdit|Bash)
#
# ⛔ ISOLATION: every case below runs with HOME pointed at a scratch directory created by
# this script (never the real ~/.claude/plans). The guard derives its plans directory from
# $HOME/.claude/plans by default, so overriding HOME is sufficient and matches the
# isolation pattern already used by test_brief_truncation_guard.sh.

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_plans_truncation_floor.sh"

if [ ! -r "$GUARD" ]; then
  echo "MISSING: $GUARD — nothing to test. FAILING CLOSED."
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/plans_floor_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
ERRF="$SCRATCH/stderr.txt"
PASSED=0
FAILED=0

TESTHOME="$SCRATCH/home"
PLANSDIR="$TESTHOME/.claude/plans"
mkdir -p "$PLANSDIR"

# A real-shaped substantial plan file: 505,000 bytes, comfortably above the 4096-byte
# default floor and in the same order of magnitude as the real 2026-09-16 incident (493 KB).
BIGPLAN="$PLANSDIR/lifehack-migration.plan.md"
python3 -c "print(\"x\" * 505000, end=\"\")" > "$BIGPLAN"
BIGPLAN_SIZE=$(wc -c < "$BIGPLAN" | tr -d ' ')

mkjson_write() {  # mkjson_write <path> <content>
  T_PATH="$1" T_CONTENT="$2" python3 -c 'import os, json; print(json.dumps({"tool_name": "Write", "tool_input": {"file_path": os.environ["T_PATH"], "content": os.environ["T_CONTENT"]}}))'
}
mkjson_edit() {  # mkjson_edit <path> <old> <new> [replace_all]
  T_PATH="$1" T_OLD="$2" T_NEW="$3" T_ALL="${4:-}" python3 -c 'import os, json; print(json.dumps({"tool_name": "Edit", "tool_input": {"file_path": os.environ["T_PATH"], "old_string": os.environ["T_OLD"], "new_string": os.environ["T_NEW"], "replace_all": bool(os.environ.get("T_ALL"))}}))'
}
mkjson_multiedit() {  # mkjson_multiedit <path> <old1> <new1> <old2> <new2>
  T_PATH="$1" T_O1="$2" T_N1="$3" T_O2="$4" T_N2="$5" python3 -c 'import os, json; print(json.dumps({"tool_name": "MultiEdit", "tool_input": {"file_path": os.environ["T_PATH"], "edits": [{"old_string": os.environ["T_O1"], "new_string": os.environ["T_N1"]}, {"old_string": os.environ["T_O2"], "new_string": os.environ["T_N2"]}]}}))'
}
mkjson_bash() {
  T_CMD="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}}))'
}

TESTTMPDIR="$SCRATCH/tmp"; mkdir -p "$TESTTMPDIR"
run_guard() {  # extra env vars may already be exported by the caller
  cat | HOME="$TESTHOME" CLAUDE_PROJECT_DIR="$REPO" TMPDIR="$TESTTMPDIR" bash "$GUARD" 2>"$ERRF"
}

allow() {
  local desc="$1" payload="$2"
  out=$(printf '%s' "$payload" | run_guard); rc=$?
  if [ "$rc" -eq 0 ]; then
    printf "  PASS  allow  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  allow  %s  (rc=%s) OVER-BLOCK\n" "$desc" "$rc"
    printf "        stderr: %.300s\n" "$(cat "$ERRF")"
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
raw = open(os.environ["T_ERRF"], encoding="utf-8").read().strip()
try:
    d = json.loads(raw)
except Exception as e:
    print("stderr-not-json(%s);" % type(e).__name__); sys.exit(0)
if d.get("decision") != "block":
    print("decision!=block;")
')
  problems="$problems$verdict"
  case "$errtxt" in *"$must"*) ;; *) problems="${problems}missing(${must});" ;; esac
  if [ -z "$problems" ]; then
    printf "  PASS  deny   %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  deny   %s  ->%s\n" "$desc" "$problems"
    printf "        stderr: %.400s\n" "$errtxt"
    FAILED=$((FAILED + 1))
  fi
}

echo "=== guard_plans_truncation_floor.sh — ALLOW cases first ==="

allow "a Write to a file outside the plans directory" \
  "$(mkjson_write "$SCRATCH/notes.md" 'x')"

allow "a new plan file's creation (nothing on disk yet)" \
  "$(mkjson_write "$PLANSDIR/brand-new.plan.md" 'hello')"

allow "a Write that GROWS the plan file" \
  "$(mkjson_write "$BIGPLAN" "$(python3 -c 'print("x"*600000)')")"

EQUAL_NEW=$(python3 -c 'import sys; sys.stdout.write("y"*505000)')
allow "a Write that KEEPS the plan file's size" \
  "$(mkjson_write "$BIGPLAN" "$EQUAL_NEW")"

allow "an Edit whose delta keeps the file at/above the floor" \
  "$(mkjson_edit "$BIGPLAN" "$(python3 -c 'print("x"*100)')" "$(python3 -c 'print("y"*100)')")"

SMALLPLAN="$PLANSDIR/small.plan.md"
printf 'hi\n' > "$SMALLPLAN"
allow "a plan file already below the floor shrinking further (nothing left to protect)" \
  "$(mkjson_write "$SMALLPLAN" '')"

allow "a Bash APPEND (>>) to the big plan -- cannot truncate" \
  "$(mkjson_bash "echo more >> $BIGPLAN")"

allow "a Bash READ of the big plan via python (open().read())" \
  "$(mkjson_bash "python3 -c \"print(len(open('$BIGPLAN').read()))\"")"

allow "an unrelated Bash command" \
  "$(mkjson_bash 'ls -la')"

allow "an unparseable stdin payload (not our business until a target is identified)" \
  'not valid json at all'

echo
echo "=== DENY — the DoD case: a simulated 493 KB -> 28 B rewrite ==="

deny "typed Write shrinks a 505,000-byte plan file to 28 bytes" \
  "$(mkjson_write "$BIGPLAN" "$(python3 -c 'print("x"*28, end="")')")" \
  "below the 4096-byte floor"

# The DoD's own wording: "refused with the backup made first." Verify a dated backup
# exists ALONGSIDE the refusal above (make_backup() runs synchronously before deny()
# calls exit 2, so by the time run_guard() has returned, the file is already on disk).
BACKUP_COUNT=$(find "$PLANSDIR" -maxdepth 1 -name "$(basename "$BIGPLAN").*.preshrink.bak" | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -ge 1 ]; then
  BACKUP_FILE=$(find "$PLANSDIR" -maxdepth 1 -name "$(basename "$BIGPLAN").*.preshrink.bak" | head -1)
  BACKUP_SIZE=$(wc -c < "$BACKUP_FILE" | tr -d ' ')
  if [ "$BACKUP_SIZE" -eq "$BIGPLAN_SIZE" ]; then
    printf "  PASS  backup made first, full pre-shrink content (%s bytes) preserved at %s\n" "$BACKUP_SIZE" "$BACKUP_FILE"
    PASSED=$((PASSED + 1))
  else
    printf "  FAIL  backup exists but is %s bytes, expected %s\n" "$BACKUP_SIZE" "$BIGPLAN_SIZE"
    FAILED=$((FAILED + 1))
  fi
else
  printf "  FAIL  no dated .preshrink.bak found beside %s after the refusal\n" "$BIGPLAN"
  FAILED=$((FAILED + 1))
fi

# Restore the big plan to its original content for the remaining cases (the guard denied
# the write, so the file on disk is untouched by the Write itself, but earlier ALLOW cases
# in this run mutated it — regenerate deterministically).
python3 -c "print(\"x\" * 505000, end=\"\")" > "$BIGPLAN"

echo
echo "=== DENY — every other door this guard claims to gate ==="

deny "typed Edit whose delta shrinks the plan file below the floor" \
  "$(mkjson_edit "$BIGPLAN" "$(python3 -c 'print("x"*504000)')" "z")" \
  "below the 4096-byte floor"

BIG2="$PLANSDIR/big2.plan.md"
python3 -c "print(\"a\"*3000 + \"b\"*3000, end=\"\")" > "$BIG2"
deny "typed MultiEdit whose combined deltas shrink the plan file below the floor" \
  "$(mkjson_multiedit "$BIG2" "$(python3 -c 'print("a"*3000)')" '' "$(python3 -c 'print("b"*3000)')" 'z')" \
  "below the 4096-byte floor"

python3 -c "print(\"x\" * 505000, end=\"\")" > "$BIGPLAN"
deny "Bash overwrite-shaped write (python open/write) to the plan file, no override" \
  "$(mkjson_bash "python3 -c \"open('$BIGPLAN','w').write('short')\"")" \
  "overwrite-shaped write"

python3 -c "print(\"x\" * 505000, end=\"\")" > "$BIGPLAN"
deny "Bash overwrite-shaped write via a heredoc tee, no override" \
  "$(mkjson_bash "tee $BIGPLAN <<'EOF'
short
EOF")" \
  "overwrite-shaped write"

echo
echo "=== the documented override path — LHB_PLANS_FLOOR_OVERRIDE lifts the block for ONE named file ==="

python3 -c "print(\"x\" * 505000, end=\"\")" > "$BIGPLAN"
out=$(mkjson_write "$BIGPLAN" 'short' | LHB_PLANS_FLOOR_OVERRIDE="$BIGPLAN" HOME="$TESTHOME" CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>"$ERRF")
rc=$?
if [ "$rc" -eq 0 ] && grep -q "override applied" "$ERRF" 2>/dev/null; then
  printf "  PASS  override  LHB_PLANS_FLOOR_OVERRIDE=<exact path> allows an intended shrink\n"
  PASSED=$((PASSED + 1))
else
  printf "  FAIL  override  rc=%s stderr=%.300s\n" "$rc" "$(cat "$ERRF" 2>/dev/null)"
  FAILED=$((FAILED + 1))
fi
# The override must still be scoped to the NAMED path -- a mismatched override value must
# not lift the block for a DIFFERENT plans file.
python3 -c "print(\"x\" * 505000, end=\"\")" > "$BIGPLAN"
out=$(mkjson_write "$BIGPLAN" 'short' | LHB_PLANS_FLOOR_OVERRIDE="$PLANSDIR/some-other-file.plan.md" HOME="$TESTHOME" CLAUDE_PROJECT_DIR="$REPO" bash "$GUARD" 2>"$ERRF")
rc=$?
if [ "$rc" -eq 2 ]; then
  printf "  PASS  override  a mismatched LHB_PLANS_FLOOR_OVERRIDE value does NOT lift the block\n"
  PASSED=$((PASSED + 1))
else
  printf "  FAIL  override  a mismatched override value allowed the write (rc=%s) -- override is not scoped\n" "$rc"
  FAILED=$((FAILED + 1))
fi

echo
echo "=== guard_plans_truncation_floor.sh — unresolved-var scope narrowing (lead review, 2026-09-17) ==="
# An unresolved variable alone is NOT evidence a Bash write lands under the plans directory --
# `echo x > "$TMPDIR/foo"` produced a false block in the first cut of the var-resolve fix
# (FIXCARD-CROSS-PROJECT-WRITE-VAR-PATHS); this is the lead-review correction.

# NOTE: these use a single ">" (overwrite), never ">>" -- this guard SCRUBS ">>" before analysis
# (appends cannot truncate, so they are never its business, unrelated to this fix). Each command
# also mentions the REAL plans dir in a harmless second segment so it clears the guard's own
# cheap ".claude/plans" pre-filter, the same way a real command naming the directory would.

allow "an ordinary \$TMPDIR write (unrelated to the plans dir)" \
  "$(mkjson_bash "echo x > \"\$TMPDIR/foo.txt\"; ls \"$PLANSDIR\" >/dev/null")"

allow "unresolved var whose remainder is OUT of the plans-dir scope" \
  "$(mkjson_bash "cat > \"\$UNSET_PLANS_VAR/records/notes.md\"; ls \"$PLANSDIR\" >/dev/null")"

deny "unresolved var whose remainder looks like the plans dir -- names the var" \
  "$(mkjson_bash "cat > \"\$UNSET_PLANS_VAR/plans/x.plan.md\"; ls \"$PLANSDIR\" >/dev/null")" \
  "UNSET_PLANS_VAR"

deny "a bare unresolved var with no remainder at all -- could be anything" \
  "$(mkjson_bash "cat > \"\$UNSET_PLANS_VAR\"; ls \"$PLANSDIR\" >/dev/null")" "UNSET_PLANS_VAR"

allow "a same-command variable assignment resolves normally (below the floor, so allowed)" \
  "$(mkjson_bash "B=\"$PLANSDIR\"; printf 'short' > \"\$B/brand-new-2.plan.md\"")"

echo
echo "=================================================================="
echo "PASSED: $PASSED   FAILED: $FAILED"
if [ "$FAILED" -eq 0 ]; then
  echo "RESULT: GREEN"
  exit 0
else
  echo "RESULT: RED"
  exit 1
fi
