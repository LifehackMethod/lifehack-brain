#!/bin/bash
# test_fine_china_guards.sh -- Round C fine-china guards, ALLOW cases first, every switch OFF then ON.
#   guard_drive_destructive.sh   fc_sheet_file_delete, fc_drive_bulk_delete   (ask first; exit 2 / permissionDecision ask)
#   guard_git_push_signpost.sh   fc_force_push, fc_private_push (hard stops), fc_plain_push_quiet
#   Round C gap closure: wrappers (bash -c, eval, env), remote.<n>.push config, aliases, many MCP trashes, shell overwrite through wrappers/dd
# Fictional names only. No network, no real remote: the guards only read local git state. gws is a stub.
# GIT-WORD HYGIENE: payload commands are assembled from fragments in python so a live guard never sees a literal push.
# Run: bash system/hooks/tests/test_fine_china_guards.sh   (exit 0 = all pass)
HERE="$(cd "$(dirname "$0")" && pwd)"; HOOKS="$(cd "$HERE/.." && pwd)"
DRIVE="$HOOKS/guard_drive_destructive.sh"; PUSH="$HOOKS/guard_git_push_signpost.sh"
for h in "$DRIVE" "$PUSH"; do [ -f "$h" ] || { echo "CANNOT RUN: $h"; exit 1; }; done
S="$(mktemp -d "${TMPDIR:-/tmp}/fcg.XXXXXX")"; trap 'rm -rf "$S"' EXIT
P=0; F=0; ERRF="$S/err"; OUTF="$S/out"

# stub gws: answers `drive files get` from the file id's name
mkdir -p "$S/bin"
printf '%s\n' '#!/bin/bash' 'case "$*" in' \
  '  *pondSheet*) echo "{\"mimeType\":\"application/vnd.google-apps.spreadsheet\",\"name\":\"Pond Ledger\"}" ;;' \
  '  *pondNote*)  echo "{\"mimeType\":\"text/plain\",\"name\":\"scratch note\"}" ;;' \
  '  *) exit 1 ;;' 'esac' > "$S/bin/gws"
chmod +x "$S/bin/gws"
export GWS_BIN="$S/bin/gws" SHEET_LLM_MARKDIR="$S/marks"; mkdir -p "$S/marks"

mk() { python3 -c 'import sys; print(" ".join(sys.argv[1:]))' "$@"; }
bashjson() { T="$1" python3 -c 'import os,json; print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["T"]}}))'; }
mcpjson() { T="$1" python3 -c 'import os,json; print(json.dumps({"tool_name":"mcp__claude_ai_Google_Drive__trash_file","tool_input":{"fileId":os.environ["T"]}}))'; }
ok() { P=$((P+1)); }
bad() { F=$((F+1)); echo "FAIL: $1"; }

drive() { HOME="$S/home" bash "$DRIVE" <<<"$1" >"$OUTF" 2>"$ERRF"; RC=$?; }
d_allow() { drive "$2"; if [ $RC -eq 0 ] && ! grep -q '"ask"' "$OUTF"; then ok; else bad "ALLOW $1 (rc=$RC $(head -c 150 "$ERRF"))"; fi; }
d_ask()   { drive "$2"; if [ $RC -eq 2 ] && grep -q "ASK FIRST" "$ERRF" && grep -q "WHY:" "$ERRF" && grep -q "WAY THROUGH:" "$ERRF" && grep -q "RULE:" "$ERRF"; then ok; else bad "ASK $1 (rc=$RC)"; fi; }
d_mcp_ask() { drive "$1"; if [ $RC -eq 0 ] && grep -q '"permissionDecision": "ask"' "$OUTF"; then ok; else bad "MCP-ASK $2 (rc=$RC $(cat "$OUTF"))"; fi; }

SHEET_DEL=$(mk gws drive files delete --params "'{\"fileId\":\"pondSheet0001\"}'")
NOTE_DEL=$(mk gws drive files delete --params "'{\"fileId\":\"pondNote0001\"}'")
UNK_DEL=$(mk gws drive files delete --params "'{\"fileId\":\"mystery0001\"}'")
XARGS=$(mk "gws drive files list --params '{\"q\":\"name contains pond\"}' | xargs -I{} gws drive files delete --params {}")
LOOP=$(mk "for i in a b c; do gws drive files delete --params \"{\\\"fileId\\\":\\\"\$i\\\"}\"; done")
EMPTY=$(mk gws drive files emptyTrash)
TWO=$(mk "gws drive files delete --params '{\"fileId\":\"pondNote0001\"}' ; gws drive files delete --params '{\"fileId\":\"pondNote0002\"}'")
QUERY=$(mk gws drive files delete --params "'{\"q\":\"name contains pond\"}'")
BASHC=$(mk bash -c "\"gws drive files delete --params '{\\\"fileId\\\":\\\"pondSheet0001\\\"}'\"")
LIST=$(mk gws drive files list --params "'{\"q\":\"name contains pond\"}'")
MENTION=$(mk "echo 'note: gws drive files delete is guarded now'")
RMSCR=$(mk rm -f /tmp/scratch-pond.tmp)
CONFIRMED="LIFEHACK_DRIVE_CONFIRM=1 $SHEET_DEL"
TABDEL=$(mk gws sheets spreadsheets batchUpdate --params "'{\"spreadsheetId\":\"pondSheet0001\"}'" --json "'{\"requests\":[{\"deleteSheet\":{\"sheetId\":0}}]}'")

echo "-- drive, both switches OFF (= today): everything passes"
export ROUNDB_FC_SHEET_FILE_DELETE=off ROUNDB_FC_DRIVE_BULK_DELETE=off
for c in "$SHEET_DEL" "$XARGS" "$EMPTY" "$LOOP"; do d_allow "OFF $c" "$(bashjson "$c")"; done
d_allow "OFF mcp trash sheet" "$(mcpjson pondSheet0001)"

echo "-- drive, ON: ALLOW first (harmless look-alikes)"
export ROUNDB_FC_SHEET_FILE_DELETE=on ROUNDB_FC_DRIVE_BULK_DELETE=on
d_allow "list"                 "$(bashjson "$LIST")"
d_allow "delete ONE non-sheet" "$(bashjson "$NOTE_DEL")"
d_allow "mention in text"      "$(bashjson "$MENTION")"
d_allow "rm scratch file"      "$(bashjson "$RMSCR")"
d_allow "tab delete (other guard's job)" "$(bashjson "$TABDEL")"
d_allow "confirmed with marker" "$(bashjson "$CONFIRMED")"
d_allow "unrelated tool"       '{"tool_name":"Read","tool_input":{"file_path":"/tmp/x"}}'
d_allow "mcp trash non-sheet"  "$(mcpjson pondNote0001)"
d_allow "unreadable payload"   'not json'
echo "-- drive, ON: ASK"
d_ask "sheet file delete"      "$(bashjson "$SHEET_DEL")"
d_ask "sheet via bash -c"      "$(bashjson "$BASHC")"
d_ask "unknown file"           "$(bashjson "$UNK_DEL")"
d_ask "xargs bulk"             "$(bashjson "$XARGS")"
d_ask "for-loop bulk"          "$(bashjson "$LOOP")"
d_ask "empty trash"            "$(bashjson "$EMPTY")"
d_ask "two deletes"            "$(bashjson "$TWO")"
d_ask "query delete"           "$(bashjson "$QUERY")"
d_mcp_ask "$(mcpjson pondSheet0001)" "mcp trash sheet"
d_mcp_ask "$(mcpjson mystery0001)" "mcp trash unknown"
touch "$S/marks/knownSheetIdXYZ"
d_ask "marker-known sheet"     "$(bashjson "$(mk gws drive files delete --params "'{\"fileId\":\"knownSheetIdXYZ\"}'")")"
echo "-- drive, one switch at a time"
export ROUNDB_FC_SHEET_FILE_DELETE=off ROUNDB_FC_DRIVE_BULK_DELETE=on
d_allow "bulk-only: sheet delete passes" "$(bashjson "$SHEET_DEL")"; d_ask "bulk-only: xargs asks" "$(bashjson "$XARGS")"
export ROUNDB_FC_SHEET_FILE_DELETE=on ROUNDB_FC_DRIVE_BULK_DELETE=off
d_ask "sheet-only: sheet asks" "$(bashjson "$SHEET_DEL")"; d_allow "sheet-only: xargs passes" "$(bashjson "$XARGS")"
unset ROUNDB_FC_SHEET_FILE_DELETE ROUNDB_FC_DRIVE_BULK_DELETE

# ── Push
git_q() { git -C "$1" -c user.email=t@example.invalid -c user.name=t "${@:2}" >/dev/null 2>&1; }
newrepo() {  # newrepo <dir> <remote-url-or-empty> ; one commit on main, origin/main = HEAD, tracking set
  mkdir -p "$1"; git init -q -b main "$1"; echo a > "$1/a.txt"; git_q "$1" add .; git_q "$1" commit -m init
  if [ -n "$2" ]; then git -C "$1" remote add origin "$2"; git -C "$1" update-ref refs/remotes/origin/main HEAD
    git -C "$1" config branch.main.remote origin; git -C "$1" config branch.main.merge refs/heads/main; fi
}
newrepo "$S/priv" "https://github.com/fictional-org/pond-notes.git"
newrepo "$S/pub" "https://github.com/LifehackMethod/lifehack-brain.git"
newrepo "$S/local" "$S/bare.git"
newrepo "$S/none" ""
newrepo "$S/leaky" "https://github.com/fictional-org/pond-open.git"
echo "fictional-secret-term-pond" > "$S/ident.txt"
mkdir -p "$S/leaky/notes"; printf 'see %s/marlowe/Desktop/pond-notes/plan.md\n' "/Us""ers" > "$S/leaky/notes/n.md"  # path assembled so this test file itself passes the scan
git_q "$S/leaky" add .; git_q "$S/leaky" commit -m "add note"
newrepo "$S/behind" "https://github.com/fictional-org/pond-notes.git"
echo b > "$S/behind/b.txt"; git_q "$S/behind" add .; git_q "$S/behind" commit -m two
git -C "$S/behind" update-ref refs/remotes/origin/main HEAD
git -C "$S/behind" reset -q --hard HEAD~1; echo c > "$S/behind/c.txt"; git_q "$S/behind" add .; git_q "$S/behind" commit -m diverge
newrepo "$S/feat" "https://github.com/fictional-org/pond-notes.git"; git -C "$S/feat" checkout -q -b pond-feature

PUSHW="pu""sh"
pc() { mk git "$PUSHW" "$@"; }
n=0
push() {  # push <repo> <env-assignments> <args...>
  local repo="$1" envs="$2"; shift 2; n=$((n+1))
  local cmd; cmd=$(pc "$@")
  ( cd "$repo" && env $envs HOME="$S/h$n" CLAUDE_CODE_SESSION_ID="${SID:-sess$n}" bash "$PUSH" <<<"$(bashjson "$cmd")" >"$OUTF" 2>"$ERRF" ); RC=$?
}
p_pass() { push "$2" "$3" "${@:4}"; if [ $RC -eq 0 ]; then ok; else bad "PASS $1 (rc=$RC $(head -c 160 "$ERRF"))"; fi; }
p_sign() { push "$2" "$3" "${@:4}"; if [ $RC -eq 2 ] && grep -q "PUSH ·" "$ERRF" && ! grep -q "HARD STOP" "$ERRF"; then ok; else bad "SIGNPOST $1 (rc=$RC $(head -c 160 "$ERRF"))"; fi; }
p_hard() { push "$2" "$3" "${@:4}"; if [ $RC -eq 2 ] && grep -q "HARD STOP" "$ERRF" && grep -q "WHY:" "$ERRF" && grep -q "WAY THROUGH:" "$ERRF" && grep -q "RULE:" "$ERRF"; then ok; else bad "HARD $1 (rc=$RC $(head -c 200 "$ERRF"))"; fi; }
for i in $(seq 1 90); do mkdir -p "$S/h$i/.claude"; done
OFF="ROUNDB_FC_FORCE_PUSH=off ROUNDB_FC_PRIVATE_PUSH=off ROUNDB_FC_PLAIN_PUSH_QUIET=off"
FORCE="ROUNDB_FC_FORCE_PUSH=on ROUNDB_FC_PRIVATE_PUSH=off ROUNDB_FC_PLAIN_PUSH_QUIET=off"
PRIV="ROUNDB_FC_FORCE_PUSH=off ROUNDB_FC_PRIVATE_PUSH=on ROUNDB_FC_PLAIN_PUSH_QUIET=off SHIP_IDENTITY=$S/ident.txt"
PRIVX="ROUNDB_FC_FORCE_PUSH=off ROUNDB_FC_PRIVATE_PUSH=on ROUNDB_FC_PLAIN_PUSH_QUIET=off SHIP_IDENTITY=$S/no-such-identity.txt"
QUIET="ROUNDB_FC_FORCE_PUSH=off ROUNDB_FC_PRIVATE_PUSH=off ROUNDB_FC_PLAIN_PUSH_QUIET=on"
ALL="ROUNDB_FC_FORCE_PUSH=on ROUNDB_FC_PRIVATE_PUSH=on ROUNDB_FC_PLAIN_PUSH_QUIET=on SHIP_IDENTITY=$S/ident.txt"

echo "-- push, ALL OFF (= today): force push gets only the signpost, plain push gets the signpost"
p_sign "OFF force"        "$S/priv" "$OFF" --force origin main
p_sign "OFF plain"        "$S/priv" "$OFF" origin main
p_sign "OFF leaky public" "$S/leaky" "$OFF" origin main

echo "-- push, ALL ON: ALLOW / quiet first"
p_pass "plain push origin main (tracked, fast-forward)" "$S/priv" "$ALL" origin main
p_pass "bare push (tracked)"                             "$S/priv" "$ALL"
p_pass "HEAD refspec of tracked branch"                  "$S/priv" "$ALL" origin HEAD
p_pass "tracked push to local-path remote"               "$S/local" "$ALL" origin main
p_sign "new branch, no upstream: signpost stays"         "$S/feat" "$ALL" -u origin pond-feature
p_sign "diverged branch: signpost stays"                 "$S/behind" "$ALL" origin main
p_sign "public Lifehack remote keeps its signpost"       "$S/pub" "$ALL" origin main
p_sign "tags push keeps the signpost"                    "$S/priv" "$ALL" --tags origin
echo "-- push, ON: HARD STOP, and again on retry (no marker)"
for a in "--force origin main" "-f origin HEAD:main" "--force-with-lease origin main" "origin +main" "-fu origin main" "--mirror origin" "--force-if-includes origin main" "origin +HEAD:main"; do
  SID="hs-$RANDOM"; p_hard "force: $a" "$S/priv" "$ALL" $a; p_hard "force again: $a" "$S/priv" "$ALL" $a; unset SID
done
p_hard "force-only switch, public repo" "$S/pub" "$FORCE" --force origin V2
p_hard "force, repo with no remote"     "$S/none" "$FORCE" -f origin main
echo "-- push, ON: private material to a public remote"
p_hard "leaky commit to public URL remote" "$S/leaky" "$PRIV" origin main
p_hard "leaky, scan cannot run (no identity)" "$S/leaky" "$PRIVX" origin main
p_sign "clean commit to public URL: signpost only" "$S/feat" "$PRIV" origin pond-feature
p_sign "private-only switch: tracked clean push is still signposted" "$S/priv" "$PRIV" origin main
p_sign "leaky but fc_private_push OFF: signpost only" "$S/leaky" "$OFF" origin main
mkdir -p "$S/h91/.config/lifehack"; echo "$S/leaky" > "$S/h91/.config/lifehack/personal-code"
( cd "$S/leaky" && env $PRIV HOME="$S/h91" CLAUDE_CODE_SESSION_ID=pers bash "$PUSH" <<<"$(bashjson "$(pc origin main)")" >"$OUTF" 2>"$ERRF" ); RC=$?
if [ $RC -eq 2 ] && grep -q "PUSH ·" "$ERRF" && ! grep -q "HARD STOP" "$ERRF"; then ok; else bad "personal code repo is not scanned (rc=$RC)"; fi
echo "-- push, no remote: silent and cheap"
p_sign "no remote, nothing to leak to (signpost as today)" "$S/none" "$ALL"

# ════════════════════════ Round C gap closure ════════════════════════
echo "-- gap 4: many separate MCP trash calls in one session (fc_drive_bulk_delete)"
export LHB_DRIVE_TRASH_DIR="$S/trash"
mcps() { T="$1" SIDX="$2" UID_="${3:-}" python3 -c 'import os,json; d={"tool_name":"mcp__claude_ai_Google_Drive__trash_file","session_id":os.environ["SIDX"],"tool_input":{"fileId":os.environ["T"]}}
if os.environ.get("UID_"): d["tool_use_id"]=os.environ["UID_"]
print(json.dumps(d))'; }
export ROUNDB_FC_SHEET_FILE_DELETE=on ROUNDB_FC_DRIVE_BULK_DELETE=on
d_allow "1st note trash in session A"            "$(mcps pondNote0001 sessA u1)"
d_allow "same call seen by both registrations"   "$(mcps pondNote0001 sessA u1)"
d_allow "other session is counted separately"    "$(mcps pondNote0005 sessB u5)"
d_mcp_ask "$(mcps pondNote0002 sessA u2)" "2nd different file in session A asks"
d_mcp_ask "$(mcps pondNote0003 sessA u3)" "3rd asks too"
export ROUNDB_FC_DRIVE_BULK_DELETE=off
d_allow "bulk switch OFF: counter silent"        "$(mcps pondNote0004 sessA u4)"
export ROUNDB_FC_DRIVE_BULK_DELETE=on
touch -t 200001010000 "$S/trash/sessOld" 2>/dev/null; printf '%s\tolder\n' "$(( $(date +%s) - 3600 ))" > "$S/trash/sessOld"
d_allow "an hour-old trash does not count"       "$(mcps pondNote0006 sessOld u6)"
unset ROUNDB_FC_SHEET_FILE_DELETE ROUNDB_FC_DRIVE_BULK_DELETE LHB_DRIVE_TRASH_DIR

echo "-- gaps 1-3: wrappers, config and aliases (fc_force_push, fc_private_push)"
n2=0
rawp() {  # rawp <repo> <env-assignments> <literal command>
  local repo="$1" envs="$2" cmd="$3"; n2=$((n2+1))
  ( cd "$repo" && env $envs HOME="$S/h$((50+n2))" CLAUDE_CODE_SESSION_ID="raw$n2" bash "$PUSH" <<<"$(bashjson "$cmd")" >"$OUTF" 2>"$ERRF" ); RC=$?
}
r_pass() { rawp "$2" "$3" "$4"; if [ $RC -eq 0 ]; then ok; else bad "PASS $1 (rc=$RC $(head -c 160 "$ERRF"))"; fi; }
r_hard() { rawp "$2" "$3" "$4"; if [ $RC -eq 2 ] && grep -q "HARD STOP" "$ERRF" && grep -q "WHY:" "$ERRF" && grep -q "WAY THROUGH:" "$ERRF" && grep -q "RULE:" "$ERRF"; then ok; else bad "HARD $1 (rc=$RC $(head -c 200 "$ERRF"))"; fi; }
G="gi""t"; PU="pu""sh"
newrepo "$S/al" "https://github.com/fictional-org/pond-notes.git"
git -C "$S/al" config alias.pf "$PU --force"; git -C "$S/al" config alias.sh "!$G $PU -f"; git -C "$S/al" config alias.st "status -sb"
git -C "$S/al" config alias.up "$PU origin main"; git -C "$S/al" config alias.pf2 "pf"
newrepo "$S/cfgplus" "https://github.com/fictional-org/pond-notes.git"
git -C "$S/cfgplus" config remote.origin.push "+refs/heads/main:refs/heads/main"
newrepo "$S/cfgok" "https://github.com/fictional-org/pond-notes.git"
git -C "$S/cfgok" config remote.origin.push "refs/heads/main:refs/heads/main"
for i in $(seq 51 120); do mkdir -p "$S/h$i/.claude"; done

echo "   OFF (= today): none of these is seen"
for c in "bash -c \"$G $PU -f origin main\"" "eval '$G $PU --force origin main'" "env X=1 $G $PU -f origin main" "$G config remote.origin.push +refs/heads/*:refs/heads/*"; do
  r_pass "OFF: $c" "$S/priv" "$OFF" "$c"; done
r_sign() { rawp "$2" "$3" "$4"; if [ $RC -eq 2 ] && grep -q "PUSH ·" "$ERRF" && ! grep -q "HARD STOP" "$ERRF"; then ok; else bad "SIGNPOST $1 (rc=$RC $(head -c 160 "$ERRF"))"; fi; }
r_pass "OFF: alias force push (alias not read)" "$S/al" "$OFF" "$G pf origin main"

echo "   ON: ALLOW first (look-alikes and ordinary pushes)"
r_pass "shell -c with no push"                    "$S/priv" "$ALL" "bash -c \"echo hello world\""
r_pass "commit message that mentions bash -c push -f" "$S/priv" "$ALL" "$G commit --allow-empty -m \"never run: bash -c '$G $PU -f origin main'\""
r_pass "eval of an unrelated command"             "$S/priv" "$ALL" "eval \"ls -la\""
r_pass "env prefix on a status"                   "$S/priv" "$ALL" "env FOO=1 $G status"
r_pass "config READ of remote push"               "$S/cfgplus" "$ALL" "$G config --get remote.origin.push"
r_pass "config set WITHOUT a plus"                "$S/priv" "$ALL" "$G config remote.origin.push refs/heads/main:refs/heads/main"
r_pass "config set of something else with a plus" "$S/priv" "$ALL" "$G config user.name +pond"
r_pass "alias that is not a push"                 "$S/al" "$ALL" "$G st"
r_pass "unknown git word that is no alias"        "$S/al" "$ALL" "$G frobnicate"
r_pass "wrapped plain tracked push is quiet"      "$S/priv" "$ALL" "bash -c \"$G $PU origin main\""
r_pass "env-prefixed plain tracked push is quiet" "$S/priv" "$ALL" "env X=1 $G $PU origin main"
r_pass "alias of a plain tracked push is quiet"   "$S/al" "$ALL" "$G up"
r_pass "config + refspec but the push NAMES a refspec" "$S/cfgplus" "$ALL" "$G $PU origin main"
r_pass "config refspec without a plus"            "$S/cfgok" "$ALL" "$G $PU origin"
echo "   ON: HARD STOP through wrappers"
for c in "bash -c \"$G $PU -f origin main\"" "sh -c '$G $PU --force origin main'" "eval \"$G $PU --force-with-lease origin main\"" \
         "eval $G $PU -f origin main" "bash -lc \"cd $S/priv && $G $PU -f origin main\"" "env GIT_TRACE=1 $G $PU -f origin main" \
         "GIT_TRACE=1 $G $PU -f origin main" "env -i HOME=/tmp $G $PU origin +main" "command $G $PU -f origin main" "exec $G $PU --mirror origin" \
         "bash -c \"eval '$G $PU -f origin main'\"" "FOO=1 bash -c \"$G $PU origin +HEAD:main\"" "($G $PU -f origin main)" \
         "env FOO=1 bash -c '$G $PU -f origin main'" "nohup $G $PU -f origin main"; do
  r_hard "wrapper: $c" "$S/priv" "$ALL" "$c"; r_hard "wrapper again: $c" "$S/priv" "$ALL" "$c"; done
r_hard "force-only switch sees through bash -c" "$S/priv" "$FORCE" "bash -c \"$G $PU -f origin main\""
echo "   ON: HARD STOP, remote.<n>.push config"
r_hard "bare push with a + refspec in config"      "$S/cfgplus" "$ALL" "$G $PU"
r_hard "push origin with a + refspec in config"    "$S/cfgplus" "$ALL" "$G $PU origin"
r_hard "setting a + refspec in config"             "$S/priv" "$ALL" "$G config remote.origin.push +refs/heads/*:refs/heads/*"
r_hard "setting it with --global --add"            "$S/priv" "$ALL" "$G config --global --add remote.origin.push '+refs/heads/main'"
r_hard "setting it inside bash -c"                 "$S/priv" "$ALL" "bash -c \"$G config remote.origin.push +refs/heads/main\""
r_hard "one-off -c remote push plus"               "$S/priv" "$ALL" "$G -c remote.origin.push=+refs/heads/main $PU origin"
echo "   ON: HARD STOP, aliases"
r_hard "alias to push --force"                     "$S/al" "$ALL" "$G pf origin main"
r_hard "shell alias that force pushes"             "$S/al" "$ALL" "$G sh origin main"
r_hard "alias of an alias"                         "$S/al" "$ALL" "$G pf2 origin main"
r_hard "alias after cd"                            "$S/priv" "$ALL" "cd $S/al && $G pf origin main"
r_hard "alias with -C"                             "$S/priv" "$ALL" "$G -C $S/al pf origin main"
echo "   ON: private material through a wrapper"
r_hard "leaky push inside bash -c"                 "$S/leaky" "$PRIV" "bash -c \"$G $PU origin main\""
r_hard "leaky push behind env"                     "$S/leaky" "$PRIV" "env X=1 $G $PU origin main"

echo "-- gap 5: fc_shell_overwrite through wrappers and more verbs (guard_build_mode.sh)"
BM="$HOOKS/guard_build_mode.sh"; B="$S/bm"; BC="$B/code"; BN="$B/notes"
mkdir -p "$B/hm/.config/lifehack" "$BC/shared" "$BC/system/sops" "$BC/system/hooks" "$BC/system/register" "$BC/hooks" "$BN/system" "$BN/state/demo/canon"
echo "$BC" > "$B/hm/.config/lifehack/code-root"
cp "$HOOKS/../../shared/brain_root.py" "$HOOKS/../tools/utf8_stdio.py" "$BC/shared/" 2>/dev/null
cp "$HOOKS/build_mode_sops.conf" "$HOOKS/placement.conf" "$BC/system/hooks/"
for x in skill-building jobs hook desk-building; do echo "# $x" > "$BC/system/sops/$x-sop.md"; done
echo '{"hooks":{}}' > "$BC/hooks/hooks.json"; : > "$BC/system/register/register.jsonl"
SOPF="$BC/system/sops/skill-building-sop.md"; CANF="$BN/state/demo/canon/current.md"; PLAIN="$BC/system/notes-plain.md"
echo "- line" > "$CANF"; echo "# plain" > "$PLAIN"
bmfire() {  # bmfire <command>
  N="$BN" BMC="$1" python3 -c 'import json,os; print(json.dumps({"session_id":"bm1","cwd":os.environ["N"],"tool_name":"Bash","tool_input":{"command":os.environ["BMC"]}}))' > "$S/bm.json"
  env HOME="$B/hm" LIFEHACK_ROOT="$BN" bash "$BM" < "$S/bm.json" >"$OUTF" 2>"$ERRF"; RC=$?
}
b_allow() { bmfire "$2"; if [ $RC -eq 0 ]; then ok; else bad "BM-ALLOW $1 (rc=$RC $(head -c 160 "$ERRF"))"; fi; }
b_block() { bmfire "$2"; if [ $RC -eq 2 ] && grep -q "WAY THROUGH" "$ERRF" && grep -q "overwrites" "$ERRF"; then ok; else bad "BM-BLOCK $1 (rc=$RC $(head -c 160 "$ERRF"))"; fi; }
export ROUNDB_FC_SHELL_OVERWRITE=off
for c in "bash -c \"echo x > $SOPF\"" "eval \"echo x > $SOPF\"" "dd of=$SOPF if=$PLAIN" "env FOO=1 sh -c 'echo x > $CANF'"; do b_allow "OFF: $c" "$c"; done
export ROUNDB_FC_SHELL_OVERWRITE=on
b_allow "append inside bash -c"            "bash -c \"echo x >> $SOPF\""
b_allow "read inside bash -c"              "bash -c 'cat $SOPF'"
b_allow "read inside eval"                 "eval \"grep -n rule $SOPF\""
b_allow "env prefix on a read"             "env FOO=1 cat $SOPF"
b_allow "dd READING an SOP"                "dd if=$SOPF of=/tmp/lh-gap5-copy.md"
b_allow "dd append"                        "dd if=$PLAIN of=$SOPF oflag=append conv=notrunc"
b_allow "dd onto an ordinary file"         "dd if=$SOPF of=$PLAIN"
b_allow "bash -c onto an ordinary file"    "bash -c \"echo x > $PLAIN\""
b_allow "mention inside a note"            "echo 'bash -c \"echo x > $SOPF\"' >> /tmp/lh-gap5-note.txt"
b_allow "new SOP file via bash -c"         "bash -c \"echo x > $BC/system/sops/brand-new-sop.md\""
for c in "bash -c \"echo x > $SOPF\"" "sh -c 'echo x > $SOPF'" "eval \"echo x > $SOPF\"" "eval echo x '>' $SOPF" "bash -lc \"echo x > $SOPF\"" \
         "env FOO=1 bash -c \"echo x > $SOPF\"" "FOO=1 sh -c 'echo x >| $SOPF'" "bash -c \"eval 'echo x > $SOPF'\"" "bash -c \"echo x > $CANF\"" \
         "echo x >| $SOPF" "truncate -s 0 $SOPF" "bash -c 'truncate -s 0 $SOPF'" "dd of=$SOPF if=$PLAIN" "dd if=/dev/null of=$CANF" \
         "install -m 644 $PLAIN $SOPF" "rsync $PLAIN $SOPF" "bash -c \"cp $PLAIN $SOPF\"" "exec truncate -s 0 $SOPF" "nohup cp $PLAIN $SOPF" \
         "env -i sed -i 's/a/b/' $SOPF" "sudo -n tee $SOPF" "bash -c \"sed -i 's/a/b/' $SOPF\""; do
  b_block "$c" "$c"; done
unset ROUNDB_FC_SHELL_OVERWRITE

echo
echo "fine-china guards: $P passed, $F failed"
[ "$F" -eq 0 ]
