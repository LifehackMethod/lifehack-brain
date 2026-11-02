#!/bin/bash
# test_repoint_guard_forwarding_shim.sh — the old-name forwarding shim must behave EXACTLY like
# system/hooks/guard_no_repoint_into_personal_code.sh: same stdin in, same stdout, stderr and exit code out,
# for one allow case and one deny case.
#
# temporary: forwards for windows opened before 2026-11-01; remove once all pre-11-01 windows are restarted
# (delete this test together with the shim).
#
# The shim's file name carries the old private-repo component, and live code may not spell that name
# (check_no_private_desks.py R8). So the shim is found by pattern: the one guard_no_repoint_into_*.sh in
# system/hooks/ that is not the real guard. Exactly one such file must exist.

HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
REAL="$REPO/system/hooks/guard_no_repoint_into_personal_code.sh"

SHIM=""
N=0
for f in "$REPO"/system/hooks/guard_no_repoint_into_*.sh; do
  [ "$f" = "$REAL" ] && continue
  [ -e "$f" ] || continue
  SHIM="$f"; N=$((N + 1))
done
if [ ! -r "$REAL" ] || [ "$N" -ne 1 ]; then
  echo "MISSING: real guard or exactly one forwarding shim (found $N) — FAILING CLOSED."
  exit 1
fi
if [ ! -x "$SHIM" ]; then
  echo "FAIL  the forwarding shim is not executable"
  exit 1
fi

SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/repoint_shim_test.XXXXXX")"
trap 'rm -rf "$SCRATCH"' EXIT
PC="$SCRATCH/hm/my-own-code"
mkdir -p "$PC/.claude/skills/foo" "$SCRATCH/hm/.config/lifehack"
printf '%s\n' "$PC" > "$SCRATCH/hm/.config/lifehack/personal-code"
PASSED=0
FAILED=0

mkjson_bash() {
  T_CMD="$1" python3 -c 'import os, json; print(json.dumps({"tool_name": "Bash", "tool_input": {"command": os.environ["T_CMD"]}}))'
}

run() {  # run <script> <payload> <tag>  -> writes $SCRATCH/<tag>.{out,err,rc}; invoked the way the hook config does
  printf '%s' "$2" | HOME="$SCRATCH/hm" CLAUDE_PROJECT_DIR="$REPO" bash "$1" >"$SCRATCH/$3.out" 2>"$SCRATCH/$3.err"
  echo $? >"$SCRATCH/$3.rc"
}

same() {  # same <desc> <payload> <want_rc>
  local desc="$1" payload="$2" want="$3" problems=""
  run "$REAL" "$payload" real
  run "$SHIM" "$payload" shim
  cmp -s "$SCRATCH/real.rc" "$SCRATCH/shim.rc" || problems="${problems}rc differs ($(cat "$SCRATCH/real.rc") vs $(cat "$SCRATCH/shim.rc"));"
  cmp -s "$SCRATCH/real.out" "$SCRATCH/shim.out" || problems="${problems}stdout differs;"
  cmp -s "$SCRATCH/real.err" "$SCRATCH/shim.err" || problems="${problems}stderr differs;"
  [ "$(cat "$SCRATCH/shim.rc")" = "$want" ] || problems="${problems}rc=$(cat "$SCRATCH/shim.rc")(want $want);"
  if [ -z "$problems" ]; then
    printf "  PASS  %s\n" "$desc"; PASSED=$((PASSED + 1))
  else
    printf "  FAIL  %s  ->%s\n" "$desc" "$problems"; FAILED=$((FAILED + 1))
  fi
}

echo "=== forwarding shim == real guard ==="
same "allow: unrelated Bash command" "$(mkjson_bash 'ls -la')" 0
same "deny: ln -sf re-points a skills symlink at the personal code folder" \
  "$(mkjson_bash "ln -sf $PC/.claude/skills/foo /fakebase/.claude/skills/foo")" 2

echo
echo "RESULT: $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
