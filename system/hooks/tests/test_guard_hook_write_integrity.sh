#!/bin/bash
# test_guard_hook_write_integrity.sh -- guard_hook_write_integrity.sh. Deny = exit 2, allow = exit 0.
# Run: bash system/hooks/tests/test_guard_hook_write_integrity.sh   (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
GUARD="${HOOK_UNDER_TEST:-$HOOKS/guard_hook_write_integrity.sh}"
[ -f "$GUARD" ] || { echo "CANNOT RUN: no $GUARD"; exit 1; }
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
LIVE="$T/live"; WT="$T/wt"; mkdir -p "$LIVE/system/hooks" "$WT/system/hooks"
export LIFEHACK_LIVE_ROOT="$LIVE"; unset CLAUDE_PLUGIN_ROOT
L="<<<<<<<"; M="======="; R=">>>>>>>"
GOODSRC=$'#!/bin/bash\necho hi\n'
printf '%s' "$GOODSRC" > "$LIVE/system/hooks/h.sh"; printf '%s' "$GOODSRC" > "$WT/system/hooks/h.sh"

# j <tool> <json-tool_input-as-python-dict-literal> [cwd]
run() { local label="$1" exp="$2" tool="$3" ti="$4" cwd="${5:-$T}" got
  python3 -c "import json,sys; print(json.dumps({'tool_name':sys.argv[1],'tool_input':eval(sys.argv[2]),'cwd':sys.argv[3],'session_id':'s'}))" "$tool" "$ti" "$cwd" | bash "$GUARD" >/dev/null 2>&1
  got=$?; [ "$got" = "$exp" ] && ok || bad "$label" "expected $exp got $got"; }
bashcmd() { run "$1" "$2" Bash "{'command': $(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$3")}" "${4:-$T}"; }

bash -n "$GUARD" && ok || bad syntax "guard fails bash -n"

echo "── ALLOW ──"
run "write good hook"            0 Write "{'file_path':'$LIVE/system/hooks/h.sh','content':'#!/bin/bash\necho ok\n'}"
run "write non-hook file"        0 Write "{'file_path':'$T/notes.md','content':'$L x'}"
run "write a hook TEST w/ broken text" 0 Write "{'file_path':'$WT/system/hooks/tests/test_x.sh','content':'if then'}"
run "edit good->good"            0 Edit  "{'file_path':'$WT/system/hooks/h.sh','old_string':'hi','new_string':'bye'}"
run "edit whose old_string absent (tool will error)" 0 Edit "{'file_path':'$WT/system/hooks/h.sh','old_string':'ZZZ','new_string':'if'}"
run "multiedit good"             0 MultiEdit "{'file_path':'$WT/system/hooks/h.sh','edits':[{'old_string':'hi','new_string':'a'},{'old_string':'a','new_string':'b'}]}"
bashcmd "git apply in a WORKTREE"    0 "git apply --3way p.diff" "$WT"
bashcmd "git -C worktree cherry-pick" 0 "git -C $WT cherry-pick abc123"
bashcmd "git status in live root"    0 "git status" "$LIVE"
bashcmd "git log live hooks"         0 "git log -- $LIVE/system/hooks/h.sh" "$LIVE"
bashcmd "cat live hook"              0 "cat $LIVE/system/hooks/h.sh"
bashcmd "patch a worktree file"      0 "patch -p1 -d $WT < p.diff" "$T"
bashcmd "mention in heredoc body"    0 "cat > notes.md <<'EOF'
run git apply in $LIVE/system/hooks and it's bad
EOF" "$T"
bashcmd "hook_swap is the sanctioned way" 0 "bash system/tools/hook_swap.sh $WT/system/hooks/h.sh" "$T"
bashcmd "unbalanced quote, unrelated"     0 "echo it's fine" "$T"

echo "── DENY: Write/Edit that would break a hook ──"
run "write: syntax error"        2 Write "{'file_path':'$LIVE/system/hooks/h.sh','content':'#!/bin/bash\nif true; then\n'}"
run "write: conflict markers"    2 Write "{'file_path':'$LIVE/system/hooks/h.sh','content':'#!/bin/bash\n$L HEAD\necho a\n$M\necho b\n$R x\n'}"
run "write: markers inside otherwise valid script" 2 Write "{'file_path':'$WT/system/hooks/new.sh','content':'#!/bin/bash\n: <<X\n$M\nX\n'}"
run "edit: introduces syntax error" 2 Edit "{'file_path':'$WT/system/hooks/h.sh','old_string':'echo hi','new_string':'if ['}"
run "edit: introduces a marker"     2 Edit "{'file_path':'$WT/system/hooks/h.sh','old_string':'echo hi','new_string':'echo hi\n$L'}"
run "multiedit: 2nd edit breaks it" 2 MultiEdit "{'file_path':'$WT/system/hooks/h.sh','edits':[{'old_string':'hi','new_string':'a'},{'old_string':'echo a','new_string':'fi'}]}"
run "write: ~/.claude/hooks path"   2 Write "{'file_path':'$T/.claude/hooks/x.sh','content':'fi'}"

echo "── repair path: already-broken hook ──"
printf '#!/bin/bash\n%s HEAD\necho a\n%s\necho b\n%s x\n' "$L" "$M" "$R" > "$T/broken.sh"; mkdir -p "$T/r/system/hooks"; cp "$T/broken.sh" "$T/r/system/hooks/b.sh"
run "repair: full fix allowed"      0 Write "{'file_path':'$T/r/system/hooks/b.sh','content':'#!/bin/bash\necho ok\n'}"
run "repair: partial progress allowed" 0 Edit "{'file_path':'$T/r/system/hooks/b.sh','old_string':'$L HEAD\n','new_string':''}"
run "repair: no progress denied"    2 Edit "{'file_path':'$T/r/system/hooks/b.sh','old_string':'echo b','new_string':'echo c'}"

echo "── DENY: patch tools against the live hooks ──"
bashcmd "git apply --3way live file (the incident)" 2 "git apply --3way $LIVE/system/hooks/h.sh.patch" "$T"
bashcmd "git apply from inside live root"  2 "git apply --3way /tmp/p.diff" "$LIVE"
bashcmd "cd live && git apply"             2 "cd $LIVE && git apply p.diff" "$T"
bashcmd "git -C live cherry-pick"          2 "git -C $LIVE cherry-pick abc123" "$T"
bashcmd "git merge in live root"           2 "git merge feat/x" "$LIVE"
bashcmd "git am in live root"              2 "git am p.mbox" "$LIVE"
bashcmd "patch live hook file"             2 "patch $LIVE/system/hooks/h.sh p.diff" "$T"
bashcmd "patch -d live"                    2 "patch -p1 -d $LIVE < p.diff" "$T"
bashcmd "env-prefixed apply, chained"      2 "echo a; GIT_X=1 git apply $LIVE/system/hooks/x.patch" "$T"
bashcmd "unparseable cmd but live+apply"   2 "git apply $LIVE/system/hooks/x.patch; echo it's" "$T"

echo "── FAIL CLOSED ──"
printf 'not json' | bash "$GUARD" >/dev/null 2>&1; [ $? = 2 ] && ok || bad garbage "unparseable payload must deny"

echo "$pass passed, $fail failed"; [ "$fail" = 0 ]
