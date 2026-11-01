#!/bin/bash
# test_hook_sop_read_pure_reads.sh -- switch hooksop_pure_reads: pure reads pass, real writes still block.
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
REPO="$(cd "$HERE/../../.." 2>/dev/null && pwd)"
GUARD="$REPO/system/hooks/guard_hook_sop_read.sh"
T=$(mktemp -d) || exit 1; T=$(cd "$T" && pwd -P) || exit 1
case "$T" in /private/var/folders/*|/private/tmp/*|/tmp/*|/var/folders/*) ;; *) echo "bad T=$T"; exit 1;; esac
PASSED=0; FAILED=0
H="$REPO/system/hooks/guard_write_paths.sh"
run() {  # run <switch on|off> <command>  -> rc (fresh HOME, no receipt)
  mkdir -p "$T/home"
  C="$2" python3 -c 'import os,json;print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["C"]},"session_id":"pr-nosuch","cwd":os.environ["R"]}))' > "$T/in.json"
  R="$REPO" ROUNDB_HOOKSOP_PURE_READS="$1" HOME="$T/home" bash "$GUARD" < "$T/in.json" >/dev/null 2>&1
}
want() {  # want <rc-class allow|block> <switch> <desc> <cmd>
  C="$4" R="$REPO" run "$2" "$4"; rc=$?
  exp=0; [ "$1" = block ] && exp=2
  if [ $rc -eq $exp ]; then echo "  PASS  [$2] $1 $3"; PASSED=$((PASSED+1)); else echo "  FAIL  [$2] $1 $3 (rc=$rc)"; FAILED=$((FAILED+1)); fi
}
# ON: pure reads pass
want allow on "sed -n range"             "sed -n '1,5p' $H"
want allow on "sed -n regex range"       "sed -n '/foo/,/bar/p' $H"
want allow on "sed -n piped to head"     "sed -n '10,20p' $H | head"
want allow on "sed -n 2>&1"              "sed -n '1,5p' $H 2>&1"
want allow on "grep with a quoted >"     "grep -c '>' $H"
want allow on "sed -n with a quoted >"   "sed -n '/=>/p' $H"
# ON: real writes still block
want block on "sed -i"                   "sed -i s/a/b/ $H"
want block on "sed w command"            "sed -n '1,5w $REPO/system/hooks/out.sh' /etc/hosts"
want block on "sed W command"            "sed -n '1W $REPO/system/hooks/out.sh' /etc/hosts"
want block on "redirect >"               "sed -n 1p /etc/hosts > $REPO/system/hooks/out.sh"
want block on "redirect >> glued"        "echo x >>$REPO/system/hooks/out.sh"
want block on "tee into hooks"           "sed -n 1p /etc/hosts | tee $REPO/system/hooks/out.sh"
want block on "quoted > AND real >"      "grep -c '>' $H > $REPO/system/hooks/out.sh"
want block on "unbalanced quote + cp"    "sed -n '1p' $H | cp x $REPO/system/hooks/o; echo 'unbalanced"
# OFF: old behaviour (the quoted > false alarm is back; the w gap is open)
want block off "old behaviour: quoted > still blocks" "grep -c '>' $H"
want allow off "old behaviour: sed w not caught"      "sed -n '1,5w $REPO/system/hooks/out.sh' /etc/hosts"
want block off "old behaviour: sed -i blocks"         "sed -i s/a/b/ $H"
# the switch is a REAL line in roundB.conf, not inside a comment
if grep -qE '^hooksop_pure_reads=(on|off)$' "$REPO/system/hooks/roundB.conf"; then echo "  PASS  switch is a real line in roundB.conf"; PASSED=$((PASSED+1)); else echo "  FAIL  switch line missing"; FAILED=$((FAILED+1)); fi
echo "  $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ] && { echo "--- RESULT: GREEN ---"; exit 0; }
echo "--- RESULT: RED ---"; exit 1
