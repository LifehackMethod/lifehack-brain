#!/bin/bash
# Matrix for system/hooks/guard_build_mode.sh (v2 plan 3.2 + 3.4). Every case is a deliberate wrong move
# (or a deliberate right one that must stay silent) fired through the REGISTERED entry point with a real
# PreToolUse payload, under a temp HOME. It asserts the exit code AND reads the printed text.
HERE="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$HERE/guard_build_mode.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export HOME="$T/home"; CODE="$T/code"; NOTES="$T/notes"
mkdir -p "$HOME/.config/lifehack" "$CODE/shared/notify" "$CODE/system/register" "$CODE/system/sops" "$CODE/system/hooks" "$CODE/hooks" \
         "$NOTES/desks/marc/tools" "$NOTES/desks/marc/records"
echo "$CODE" > "$HOME/.config/lifehack/code-root"
cp "$HERE/../../shared/brain_root.py" "$HERE/../tools/utf8_stdio.py" "$CODE/shared/"; export LIFEHACK_ROOT="$NOTES"
cp "$HERE/build_mode_sops.conf" "$HERE/placement.conf" "$CODE/system/hooks/"; mkdir -p "$CODE/state" "$NOTES/system"
for s in skill-building jobs hook desk-building; do echo "# $s" > "$CODE/system/sops/$s-sop.md"; done
printf 'echo real notify\n' > "$CODE/shared/notify/notify-send.sh"
printf '| id | cmd |\n' > "$CODE/system/jobs.md"; echo '{"hooks":{}}' > "$CODE/hooks/hooks.json"
cat > "$CODE/system/register/register.jsonl" <<'R'
{"type":"tool","path":"/shared/notify/notify-send.sh"}
{"type":"tool","path":"/shared/notify/notify-governor.py"}
{"type":"tool","path":"/shared/paths.py"}
{"type":"tool","path":"/system/tools/not-shared.py"}
R
cat > "$CODE/system/register/toolbox.md" <<'R'
# Toolbox
## Notify
- `/shared/notify/notify-send.sh` · finds your topic -> asks notify-governor.py for permission -> only on ALLOW posts a TEASER
- `/shared/paths.py` · resolves the notes and code roots
R
pass=0; fail=0; ERR=""
payload() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"cwd":sys.argv[2],"tool_name":sys.argv[3],"tool_input":json.loads(sys.argv[4])}))' "$1" "$NOTES" "$2" "$3"; }
fire() { # fire <session> <tool> <tool_input-json>  -> sets RC, ERR
  ERR="$(payload "$1" "$2" "$3" | bash "$HOOK" 2>&1 >/dev/null)"; RC=$?; }
want() { # want <rc> <label> [text that must appear]
  if [ "$RC" = "$1" ] && { [ -z "${3:-}" ] || printf '%s' "$ERR" | grep -Fq -- "$3"; }; then pass=$((pass+1)); printf '   ok   %s\n' "$2"
  else fail=$((fail+1)); printf '  FAIL  %s (rc=%s want %s; text: %.160s)\n' "$2" "$RC" "$1" "$ERR"; fi; }
silent() { [ -z "$ERR" ] || { fail=$((fail+1)); printf '  FAIL  %s should be silent: %.120s\n' "$1" "$ERR"; }; }
J() { python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2],sys.argv[2::2]))))' "$@"; }

S=s1
fire $S Write "$(J file_path "$HOME/.claude/skills/foo/SKILL.md" content hi)"; want 2 "new SKILL.md denied once" "building a skill"
printf '%s' "$ERR" | grep -Fq "skill-building-sop.md" && { pass=$((pass+1)); echo "   ok   message names the configured SOP path"; } || { fail=$((fail+1)); echo "  FAIL  SOP path not in message"; }
for x in toolbox.md /build "RULE: system/hooks/build_mode_sops.conf"; do printf '%s' "$ERR" | grep -Fq -- "$x" && { pass=$((pass+1)); echo "   ok   message names $x"; } || { fail=$((fail+1)); echo "  FAIL  message lacks $x"; }; done
printf '%s' "$ERR" | grep -Fq "may already do this" && { fail=$((fail+1)); echo "  FAIL  tool list shown with nothing matching"; } || { pass=$((pass+1)); echo "   ok   no tool list when nothing matches"; }
fire $S Write "$(J file_path "$HOME/.claude/skills/foo/SKILL.md" content hi)"; want 0 "identical retry passes"
fire ph1 Write "$(J file_path "$HOME/.claude/skills/phone-alert/SKILL.md" content 'send a phone alert')"; want 2 "phone-alert skill: denied" "building a skill"
printf '%s' "$ERR" | grep -Fq "shared/notify/notify-send.sh" && { pass=$((pass+1)); echo "   ok   phone-alert lists notify-send.sh"; } || { fail=$((fail+1)); echo "  FAIL  notify-send.sh not listed"; }
printf '%s' "$ERR" | grep -Fq "shared/paths.py" && { fail=$((fail+1)); echo "  FAIL  unrelated tool listed"; } || { pass=$((pass+1)); echo "   ok   unrelated tool not listed"; }
fire $S Write "$(J file_path "$HOME/.claude/skills/bar/SKILL.md" content hi)"; want 0 "second skill, same session: passes (once per kind)"
fire $S Bash "$(J command "mkdir -p $NOTES/desks/newdesk")"; want 2 "mkdir new desk denied once (different kind)" "building a desk"
fire $S Bash "$(J command "mkdir -p $NOTES/desks/newdesk")"; want 0 "desk retry passes"
mkdir -p "$HOME/.claude/run/sop"; : > "$HOME/.claude/run/sop/hook.$S.receipt"   # hook-SOP receipt present: no sibling deny
fire $S Bash "$(J command "echo x > $CODE/system/hooks/x.sh")"; want 2 "new system/hooks/x.sh (Bash, receipt) denied once" "building a hook"
fire $S Bash "$(J command "echo x > $CODE/system/hooks/x.sh")"; want 0 "hook retry passes"
fire $S Edit "$(J file_path "$CODE/system/jobs.md" old_string '| id | cmd |' new_string $'| id | cmd |\n| newjob | x |')"; want 2 "jobs.md new row denied once" "building a job"
fire s2 Write "$(J file_path "$CODE/system/foo-run.sh" content x)"; want 2 "new *-run.sh denied once (fresh session)" "building a job"
fire s2 Edit "$(J file_path "$CODE/hooks/hooks.json" old_string '{}' new_string '{"x":[{"command":"y"}]}')"; want 2 "hooks.json adding a command denied once" "building a hook"
fire s3 Bash "$(J command "cp $CODE/shared/notify/notify-send.sh $NOTES/desks/marc/tools/")"; want 2 "cp from shared/ into desk: hard" "BLOCKED"
printf '%s' "$ERR" | grep -Fq "/shared/notify/notify-send.sh" && { pass=$((pass+1)); echo "   ok   refusal names the shared path to use"; } || { fail=$((fail+1)); echo "  FAIL  no shared path in refusal"; }
fire s3 Bash "$(J command "cp $CODE/shared/notify/notify-send.sh $NOTES/desks/marc/tools/")"; want 2 "same cp again: hard-blocked twice in a row"
fire s3 Bash "$(J command "cp $CODE/shared/notify/notify-send.sh $NOTES/desks/marc/tools/renamed.sh")"; want 2 "renamed copy from shared/: hard"
fire s3 Bash "$(J command "cp $CODE/shared/notify/notify-send.sh /tmp/scratch-x.sh")"; want 0 "cp from shared/ to a tmp dir: allowed"
fire s3 Bash "$(J command "echo 'cp $CODE/shared/x.sh $NOTES/desks/marc/'")"; want 0 "cp inside a quoted echo string: allowed"
FULL="$(python3 -c 'print("\n".join("line %d of a full copy"%i for i in range(40)))')"
fire s4 Write "$(J file_path "$NOTES/desks/marc/tools/notify-governor.py" content "$FULL")"; want 2 "distinctive name, full content: hard" "BLOCKED"
fire s4 Write "$(J file_path "$NOTES/desks/marc/tools/notify-governor.py" content "$FULL")"; want 2 "distinctive name again: still hard"
fire s4 Write "$(J file_path "$NOTES/desks/marc/tools/notify-governor.py" content $'#!/usr/bin/env python3\nimport os, sys\nS = "$(cat ~/.config/lifehack/code-root)/shared/notify/notify-governor.py"\nos.execv(sys.executable, [sys.executable, S] + sys.argv[1:])\n')"; want 0 "5-line wrapper naming the shared path: allowed"
fire s4 Write "$(J file_path "$NOTES/desks/marc/tools/notify-send.sh" content "# wraps-shared: /shared/notify/notify-send.sh"$'\n'"$FULL")"; want 0 "wraps-shared marker: allowed"
fire s5 Write "$(J file_path "$NOTES/desks/marc/tools/paths.py" content "X = 1")"; want 2 "generic paths.py: denied once" "HOLD"
fire s5 Write "$(J file_path "$NOTES/desks/marc/tools/paths.py" content "X = 1")"; want 0 "generic paths.py: retry passes"
fire s5 Write "$(J file_path "$NOTES/desks/marc/README.md" content "skills/ and desks are nice")"; want 0 "ordinary README edit: allowed"; silent "README"
fire s5 Write "$(J file_path "$NOTES/desks/marc/records/skills/note.md" content "x")"; want 0 "existing desk, non-skill path: allowed"; silent "desk note"
fire s5 Edit "$(J file_path "$HERE/guard_build_mode.sh" old_string a new_string b)"; want 0 "edit of an existing file: allowed"
# ---- check 3: placement
fire p1 Write "$(J file_path "$NOTES/system/helper.py" content 'print(1)')"; want 2 "code into the notes folder: denied once" "private repo"
fire p1 Write "$(J file_path "$NOTES/system/helper.py" content 'print(1)')"; want 0 "code into notes: retry passes"
fire p1 Write "$(J file_path "$CODE/state/my-note.md" content 'dear diary')"; want 2 "personal note into the harness: denied once" "notes folder"
fire p1 Write "$(J file_path "$CODE/state/my-note.md" content 'dear diary')"; want 0 "note into harness: retry passes"
fire p2 Write "$(J file_path "$NOTES/system/snapshot.json" content '{}')"; want 0 "json snapshot to the notes folder: allowed"; silent "json snapshot"
fire p2 Write "$(J file_path "$NOTES/system/run.jsonl" content '{}')"; want 0 "jsonl to notes: allowed"; silent "jsonl"
fire p2 Write "$(J file_path "$CODE/system/tools/newtool.py" content 'print(1)')"; want 0 "normal new code inside the repo: silent"; silent "repo code"
fire p2 Edit "$(J file_path "$CODE/system/jobs.md" old_string zzz new_string yyy)"; want 0 "normal edit of an existing repo file: silent"; silent "repo edit"
fire p3 Bash "$(J command "cp $CODE/system/jobs.md $NOTES/system/copy.sh")"; want 2 "bash cp target of code into notes: denied once" "private repo"
mv "$CODE/system/hooks/placement.conf" "$CODE/system/hooks/placement.bak"
fire p4 Write "$(J file_path "$NOTES/system/helper2.py" content 'print(1)')"; want 0 "placement list missing: fail open" "placement list"
mv "$CODE/system/hooks/placement.bak" "$CODE/system/hooks/placement.conf"
# user-level override switches a rule off (the remaining tests probe the register, not placement)
printf 'code-in-notes\toff\n' > "$HOME/.config/lifehack/placement.conf"
fire p5 Write "$(J file_path "$NOTES/system/helper3.py" content 'print(1)')"; want 0 "user override 'off': rule disabled"
# fail-open proof
ERR="$(printf '{not json skills/ desks' | bash "$HOOK" 2>&1 >/dev/null)"; RC=$?; want 0 "corrupt payload (passes pre-filter): exit 0" "allowing"
mv "$CODE/system/register/register.jsonl" "$CODE/system/register/r.bak"
fire s6 Write "$(J file_path "$NOTES/desks/marc/tools/notify-governor.py" content "$FULL")"; want 0 "missing register: exit 0" "register"
mv "$CODE/system/register/r.bak" "$CODE/system/register/register.jsonl"
mv "$HOME/.config/lifehack/code-root" "$HOME/.config/lifehack/cr.bak"
fire s7 Write "$(J file_path "$HOME/.claude/skills/zz/SKILL.md" content hi)"; want 0 "missing code-root pointer: exit 0" "code-root"
mv "$HOME/.config/lifehack/cr.bak" "$HOME/.config/lifehack/code-root"
printf 'garbage line\n' > "$CODE/system/register/register.jsonl"
fire s8 Write "$(J file_path "$NOTES/desks/marc/tools/notify-governor.py" content "$FULL")"; want 0 "corrupt register: exit 0 (nothing to match)"
# masked-by-a-sibling (3b-n2): do not spend the marker when guard_hook_sop_read / guard_write_paths will certainly deny too
MK="$HOME/.claude/run/build-mode"
fire m1 Bash "$(J command "echo x > $CODE/system/hooks/y.sh")"; want 2 "hooks write, no receipt: still denied" "building a hook"
[ ! -e "$MK/hook.m1.seen" ] && { pass=$((pass+1)); echo "   ok   no receipt: marker NOT written"; } || { fail=$((fail+1)); echo "  FAIL  marker written despite sibling deny"; }
: > "$HOME/.claude/run/sop/hook.m1.receipt"
fire m1 Bash "$(J command "echo x > $CODE/system/hooks/y.sh")"; want 2 "after receipt: build-mode bump shows" "building a hook"
[ -e "$MK/hook.m1.seen" ] && { pass=$((pass+1)); echo "   ok   with receipt: marker written on first deny"; } || { fail=$((fail+1)); echo "  FAIL  marker not written with receipt"; }
fire m1 Bash "$(J command "echo x > $CODE/system/hooks/y.sh")"; want 0 "then retry passes"
fire m2 Write "$(J file_path "$CODE/system/hooks/z.sh" content '#!/bin/bash')"; want 2 "Write tool into hooks: denied" "building a hook"
[ ! -e "$MK/hook.m2.seen" ] && { pass=$((pass+1)); echo "   ok   Write-tool into hooks: marker NOT written"; } || { fail=$((fail+1)); echo "  FAIL  marker written for Write into hooks"; }
# ---- F6a: git worktree in the wrong home (placement.conf worktree-home, Bash `git worktree add`)
fire w1 Bash "$(J command "git worktree add $NOTES/desks/marc/wt -b feat")"; want 2 "worktree inside notes: denied once" "Git worktrees live in"
fire w1 Bash "$(J command "git worktree add $NOTES/desks/marc/wt -b feat")"; want 0 "worktree wrong home: retry passes"
fire w2 Bash "$(J command "git -C $CODE worktree add ../sibling-wt")"; want 2 "worktree beside the repo (-C, relative): denied once" "Git worktrees live in"
fire w3 Bash "$(J command "git worktree add $HOME/worktrees/v2-x -b v2-x")"; want 0 "worktree in ~/worktrees/<name>: allowed"; silent "worktree home"
fire w3 Bash "$(J command "git worktree add $CODE/.claude/worktrees/agent1")"; want 0 "Claude-managed .claude/worktrees: allowed"; silent "managed worktree"
fire w3 Bash "$(J command "echo 'git worktree add /elsewhere/x'")"; want 0 "worktree add inside a quoted echo: allowed"
# ---- placement rule 4 (3b.3-P3): new code outside EVERY home (switch placement_outside_homes). Fictional paths.
cp "$HERE/../../shared/personal_code_root.py" "$CODE/shared/"
PCODE="$T/personal-code"; mkdir -p "$PCODE/tools" "$HOME/odd-widget" "$HOME/.claude/scratch"; echo "$PCODE" > "$HOME/.config/lifehack/personal-code"
PCREAL="$(cd "$PCODE" && pwd -P)"
# OFF: exactly today's behaviour, the rule never fires
export ROUNDB_PLACEMENT_OUTSIDE_HOMES=off
fire o1 Write "$(J file_path "$HOME/odd-widget/ping.py" content 'print(1)')"; want 0 "OFF: new .py in an odd folder: silent"; silent "outside OFF"
export ROUNDB_PLACEMENT_OUTSIDE_HOMES=on
# ON, ALLOW cases first
fire o2 Write "$(J file_path "$PCODE/tools/ping.py" content 'print(1)')"; want 0 "ON: new code in the personal code folder: allowed"; silent "personal code"
fire o2 Write "$(J file_path "$CODE/system/tools/ping2.py" content 'print(1)')"; want 0 "ON: new code in the harness: allowed"; silent "harness code"
fire o2 Write "$(J file_path "$NOTES/system/data.json" content '{}')"; want 0 "ON: data file outside homes untouched"; silent "json"
fire o2 Write "$(J file_path "$HOME/odd-widget/notes.md" content 'x')"; want 0 "ON: non-code file in an odd folder: allowed"; silent "md"
fire o2 Write "$(J file_path "/tmp/lh-fixture-nope/ping.py" content 'print(1)')"; want 0 "ON: /tmp scratch: allowed"; silent "tmp"
fire o2 Write "$(J file_path "/private/tmp/lh-fixture-nope/ping.sh" content 'echo')"; want 0 "ON: /private/tmp scratch: allowed"; silent "private tmp"
fire o2 Write "$(J file_path "$HOME/.claude/scratch/ping.py" content 'print(1)')"; want 0 "ON: under ~/.claude: allowed"; silent "dot-claude"
touch "$HOME/odd-widget/existing.py"
fire o2 Edit "$(J file_path "$HOME/odd-widget/existing.py" old_string a new_string b)"; want 0 "ON: edit of an EXISTING file: allowed"; silent "existing"
# ON, the bump
fire o3 Write "$(J file_path "$HOME/odd-widget/ping.py" content 'print(1)')"; want 2 "ON: new .py in an odd folder: denied once" "this belongs in your personal code folder: $PCREAL"
fire o3 Write "$(J file_path "$HOME/odd-widget/ping.py" content 'print(1)')"; want 0 "ON: identical retry passes"
fire o3 Write "$(J file_path "$HOME/odd-widget/other.sh" content 'echo')"; want 0 "ON: second file, same session: passes (once per rule)"
fire o4 Bash "$(J command "echo hi > $HOME/odd-widget/run.sh")"; want 2 "ON: Bash redirect to new .sh outside homes: denied once" "personal code folder: $PCREAL"
# unresolved personal code folder: no bump
mv "$HOME/.config/lifehack/personal-code" "$HOME/.config/lifehack/personal-code.bak"
fire o5 Write "$(J file_path "$HOME/odd-widget/ping3.py" content 'print(1)')"; want 0 "ON: personal folder unresolved: no bump"; silent "unresolved"
mv "$HOME/.config/lifehack/personal-code.bak" "$HOME/.config/lifehack/personal-code"
unset ROUNDB_PLACEMENT_OUTSIDE_HOMES
echo "passed=$pass failed=$fail"; [ "$fail" -eq 0 ]
