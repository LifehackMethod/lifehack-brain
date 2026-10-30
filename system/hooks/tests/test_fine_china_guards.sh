#!/bin/bash
# test_fine_china_guards.sh -- Round C fine-china guards, ALLOW cases first, every switch OFF then ON.
#   guard_drive_destructive.sh   fc_sheet_file_delete, fc_drive_bulk_delete   (ask first; exit 2 / permissionDecision ask)
#   guard_git_push_signpost.sh   fc_force_push, fc_private_push (hard stops), fc_plain_push_quiet
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
echo
echo "fine-china guards: $P passed, $F failed"
[ "$F" -eq 0 ]
