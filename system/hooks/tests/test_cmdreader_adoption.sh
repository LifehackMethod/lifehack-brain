#!/bin/bash
# Round B piece 4: the three guards that adopt shared/cmdreader.py (push signpost, repoint guard, build mode)
# read a command BY THE SWITCH (ROUNDB_CMDREADER=on|off). OFF must behave as before; ON must (a) stop treating
# heredoc/quoted TEXT as a command and (b) see the roads the old text matching missed.
# Run: bash system/hooks/tests/test_cmdreader_adoption.sh
HERE="$(cd "$(dirname "$0")/.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
J() { python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2],sys.argv[2::2]))))' "$@"; }
payload() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"cwd":sys.argv[2],"tool_name":sys.argv[3],"tool_input":json.loads(sys.argv[4])}))' "$1" "$2" "$3" "$4"; }

# ---------------------------------------------------------------- build mode
export HOME="$T/home"; CODE="$T/code"; NOTES="$T/notes"
mkdir -p "$HOME/.config/lifehack" "$CODE/shared/notify" "$CODE/system/register" "$CODE/system/sops" "$CODE/system/hooks" "$CODE/hooks" \
         "$NOTES/desks/marc/tools" "$NOTES/desks/marc/records" "$CODE/state" "$NOTES/system"
echo "$CODE" > "$HOME/.config/lifehack/code-root"
cp "$HERE/../../shared/brain_root.py" "$HERE/../tools/utf8_stdio.py" "$CODE/shared/"; export LIFEHACK_ROOT="$NOTES"
cp "$HERE/build_mode_sops.conf" "$HERE/placement.conf" "$CODE/system/hooks/"
for s in skill-building jobs hook desk-building; do echo "# $s" > "$CODE/system/sops/$s-sop.md"; done
printf 'echo real notify\n' > "$CODE/shared/notify/notify-send.sh"
printf '{"type":"tool","path":"/shared/notify/notify-send.sh"}\n' > "$CODE/system/register/register.jsonl"
printf '# Toolbox\n' > "$CODE/system/register/toolbox.md"
bm() { # bm <switch> <session> <command>  -> RC
  payload "$2" "$CODE" Bash "$(J command "$3")" | ROUNDB_CMDREADER="$1" bash "$HERE/guard_build_mode.sh" >/dev/null 2>&1; RC=$?; }

VARCP="SRC=$CODE/shared/notify; DST=$NOTES/desks/marc/tools; cp \"\$SRC/notify-send.sh\" \"\$DST/\""
bm off b1 "$VARCP"; [ "$RC" = 0 ] && ok "build_mode OFF: copy via variables passes (today's gap, unchanged)" || bad "build_mode OFF var copy rc=$RC"
bm on  b2 "$VARCP"; [ "$RC" = 2 ] && ok "build_mode ON: copy from shared/ via variables is blocked" || bad "build_mode ON var copy rc=$RC"
PYCP="python3 -c \"import shutil,os; shutil.copy(os.path.join('$CODE','shared','notify','notify-send.sh'), '$NOTES/desks/marc/tools/n.sh')\""
bm off b3 "$PYCP"; [ "$RC" = 0 ] && ok "build_mode OFF: one-line python copy passes (unchanged)" || bad "build_mode OFF python copy rc=$RC"
bm on  b4 "$PYCP"; [ "$RC" = 2 ] && ok "build_mode ON: one-line python copy from shared/ is blocked" || bad "build_mode ON python copy rc=$RC"
HDOC="cat >> $NOTES/desks/marc/records/log.md <<'EOF'
cp $CODE/shared/notify/notify-send.sh $NOTES/desks/marc/tools/
EOF"
for sw in off on; do bm $sw b5$sw "$HDOC"; [ "$RC" = 0 ] && ok "build_mode $sw: a cp line inside a heredoc body is text, allowed" || bad "build_mode $sw heredoc rc=$RC"; done
bm on b6 "cp $CODE/shared/notify/notify-send.sh $NOTES/desks/marc/tools/"; [ "$RC" = 2 ] && ok "build_mode ON: plain cp from shared/ still hard-blocked" || bad "build_mode ON plain cp rc=$RC"
bm on b7 "echo 'cp $CODE/shared/x.sh $NOTES/desks/marc/'"; [ "$RC" = 0 ] && ok "build_mode ON: cp inside a quoted echo allowed" || bad "build_mode ON quoted cp rc=$RC"
bm on b8 "cp $CODE/shared/notify/notify-send.sh /tmp/scratch-x.sh"; [ "$RC" = 0 ] && ok "build_mode ON: cp from shared/ to /tmp allowed" || bad "build_mode ON tmp cp rc=$RC"

# ---------------------------------------------------------------- repoint guard
M="Claude""Ops"
RP="$HERE/guard_no_repoint_into_claudeops.py"
rp() { printf '%s' "$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$2")" | ROUNDB_CMDREADER="$1" python3 "$RP" | cut -d: -f1; }
RPH="cat >> $T/notes.md <<'EOF'
the bad move:
ln -sf $HOME/.claude/skills/$M/foo $HOME/.claude/skills/foo
EOF"
[ "$(rp off "$RPH")" = BLOCK ] && ok "repoint OFF: an ln line inside a heredoc body blocks (the false block, unchanged)" || bad "repoint OFF heredoc"
[ "$(rp on  "$RPH")" = ALLOW ] && ok "repoint ON: the same heredoc text is data, allowed" || bad "repoint ON heredoc"
RPR="ln -sfn $HOME/.claude/skills/$M/foo $HOME/.claude/skills/foo"
[ "$(rp on "$RPR")" = BLOCK ] && ok "repoint ON: a real re-point still blocks" || bad "repoint ON real"
RPQ="echo 'run ln -sf $HOME/.claude/skills/$M/foo $HOME/.claude/skills/foo later'"
[ "$(rp on "$RPQ")" = ALLOW ] && ok "repoint ON: ln inside a quoted echo allowed" || bad "repoint ON quoted"
RPB="bash -c 'ln -sfn $HOME/.claude/skills/$M/foo $HOME/.claude/skills/foo'"
[ "$(rp on "$RPB")" = BLOCK ] && ok "repoint ON: ln inside bash -c blocks" || bad "repoint ON bash -c"
[ "$(rp on "echo 'unterminated")" = ALLOW ] && ok "repoint ON: unparsable and names nothing protected: allowed" || bad "repoint ON unparsable harmless"
[ "$(rp on "echo 'ln $HOME/.claude/skills/$M/x")" = BLOCK ] && ok "repoint ON: unparsable but names the protected area: denied" || bad "repoint ON unparsable protected"

# ---------------------------------------------------------------- push signpost
R="$T/repo1"; mkdir -p "$R"; git init -q "$R" 2>/dev/null
ps() { # ps <switch> <command> -> OUT
  OUT="$(payload ps1 "$R" Bash "$(J command "$2")" | HOME="$T/hp_$1" ROUNDB_CMDREADER="$1" CLAUDE_CODE_SESSION_ID="s_$1_$RANDOM" bash "$HERE/guard_git_push_signpost.sh" 2>&1)"; }
mkdir -p "$T/hp_off" "$T/hp_on"
ps off "bash -c 'cd $R && git push origin main'"; printf '%s' "$OUT" | grep -q "PUSH" && bad "signpost OFF saw a push inside bash -c (should be today's gap)" || ok "signpost OFF: push inside bash -c not seen (unchanged)"
ps on  "bash -c 'cd $R && git push origin main'"; printf '%s' "$OUT" | grep -q "PUSH" && ok "signpost ON: push inside bash -c is signposted" || bad "signpost ON bash -c: $OUT"
ps on "sh -s <<'EOF'
cd $R
git push origin main
EOF"; printf '%s' "$OUT" | grep -q "PUSH" && ok "signpost ON: push in a heredoc fed to a shell is signposted" || bad "signpost ON heredoc-to-shell"
for sw in off on; do
  ps $sw "cat > $T/n.md <<'EOF'
the man said \"then git push and it's done
EOF"; [ -z "$OUT" ] && ok "signpost $sw: prose in a heredoc body stays silent" || bad "signpost $sw prose: $OUT"
done
ps on "git -C $R push origin main 2>&1 | tail -3"; printf '%s' "$OUT" | grep -q "2>&1" && bad "signpost ON: redirection leaked into refspec" || ok "signpost ON: redirection not a refspec"

echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
