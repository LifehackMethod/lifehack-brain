#!/bin/bash
# test_push_scan_warn.sh -- fc_private_push_mode=block|warn (Enver's ruling 2026-11-02, push-scan middle ground).
#   guard_git_push_signpost.sh + lib/push_facts.py + lib/push_warn.py   (PreToolUse: allow + warn + log, or the old hard stop)
#   end_of_turn_checks.sh + lib/push_warn.py eot                         (Stop: the forced report, cleared once reported)
# Both ways: a planted private name going to a public remote in warn mode is ALLOWED, LOGGED and its report FORCED, and the
# force clears once reported; a clean push logs nothing and forces nothing; block mode is the old hard stop; an unwritable
# log blocks; a scan that cannot run stops in both modes; a private-repo push stays unscanned; a force push stays a hard stop.
# Fictional names only. No network, no real remote: the guard only reads local git state. Notes root = a temp folder
# (LIFEHACK_ROOT), HOME = a temp folder, so neither the real notes nor ~/.claude is touched.
# GIT-WORD HYGIENE: payload commands are assembled from fragments so a live guard never sees a literal push.
# Run: bash system/hooks/tests/test_push_scan_warn.sh   (exit 0 = all pass)
HERE="$(cd "$(dirname "$0")" && pwd)"; HOOKS="$(cd "$HERE/.." && pwd)"
PUSH="$HOOKS/guard_git_push_signpost.sh"; EOT="$HOOKS/end_of_turn_checks.sh"; CONF="$HOOKS/roundB.conf"
for h in "$PUSH" "$EOT" "$CONF" "$HOOKS/lib/push_warn.py"; do [ -f "$h" ] || { echo "CANNOT RUN: $h"; exit 1; }; done
S="$(cd "$(mktemp -d "${TMPDIR:-/tmp}/psw.XXXXXX")" && pwd -P)"
trap 'chmod -R u+w "$S" 2>/dev/null; rm -rf "$S"' EXIT
P=0; F=0; ERRF="$S/err"; OUTF="$S/out"
ok()  { P=$((P+1)); printf '   ok   %s\n' "$1"; }
bad() { F=$((F+1)); printf '  FAIL  %s\n' "$1"; }

NOTES="$S/notes"; mkdir -p "$NOTES/state" "$S/hm/.claude"
LOG="$NOTES/state/push-warnings.log"; TW="$S/tw"
export LIFEHACK_ROOT="$NOTES" LHB_TURN_WRITES_DIR="$TW" LIFEHACK_WATCH=0
printf 'Quillfeather\n' > "$S/ident.txt"

echo "-- the mode is a REAL line in roundB.conf"
if grep -qxE 'fc_private_push_mode=(warn|block)' "$CONF"; then ok "roundB.conf has a real fc_private_push_mode=warn|block line"; else bad "no real fc_private_push_mode line in roundB.conf"; fi
LINE="$(sed -n 's/^fc_private_push_mode=//p' "$CONF" | tail -1)"
GOT="$(unset ROUNDB_FC_PRIVATE_PUSH_MODE; . "$HOOKS/lib/roundb.sh"; roundb_val fc_private_push_mode)"
[ -n "$LINE" ] && [ "$GOT" = "$LINE" ] && ok "roundb_val reads that line ($GOT)" || bad "roundb_val read '$GOT', line says '$LINE'"
[ "$LINE" = warn ] && ok "the committed mode is warn (the ruling)" || bad "the committed mode is '$LINE', not warn"

git_q() { git -C "$1" -c user.email=t@example.invalid -c user.name=t "${@:2}" >/dev/null 2>&1; }
newrepo() {  # newrepo <dir> <remote-url> ; one commit on main, origin/main = HEAD, tracking set
  mkdir -p "$1"; git init -q -b main "$1"; echo a > "$1/a.txt"; git_q "$1" add .; git_q "$1" commit -m init
  git -C "$1" remote add origin "$2"; git -C "$1" update-ref refs/remotes/origin/main HEAD
  git -C "$1" config branch.main.remote origin; git -C "$1" config branch.main.merge refs/heads/main
}
newrepo "$S/leaky" "https://github.com/fictional-org/pond-open.git"
printf 'my working folder\nWritten up by Quillfeather\n' > "$S/leaky/README.md"   # the planted private name
git_q "$S/leaky" add .; git_q "$S/leaky" commit -m "add contact line"
LEAKSHA="$(git -C "$S/leaky" rev-parse HEAD)"
newrepo "$S/clean" "https://github.com/fictional-org/pond-open.git"
echo "nothing private here" > "$S/clean/b.txt"; git_q "$S/clean" add .; git_q "$S/clean" commit -m "clean change"

bashjson() { T="$1" SID_="$2" python3 -c 'import os,json; print(json.dumps({"session_id":os.environ["SID_"],"tool_name":"Bash","tool_input":{"command":os.environ["T"]}}))'; }
PUSHW="pu""sh"
push() {  # push <repo> <session> <env-assignments> <args...>
  local repo="$1" sid="$2" envs="$3"; shift 3
  local cmd; cmd="git $PUSHW $*"
  ( cd "$repo" && env $envs HOME="$S/hm" CLAUDE_CODE_SESSION_ID="$sid" bash "$PUSH" <<<"$(bashjson "$cmd" "$sid")" >"$OUTF" 2>"$ERRF" ); RC=$?
}
stop() {  # stop <session> <last message> [active]
  python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"prompt_id":sys.argv[4],"hook_event_name":"Stop","stop_hook_active":sys.argv[3]=="true","last_assistant_message":sys.argv[2]}))' "$1" "$2" "${3:-false}" "${PROMPT:-p1}" \
    | HOME="$S/hm" bash "$EOT" >"$OUTF" 2>"$ERRF"; RC=$?
}
loglines() { [ -f "$LOG" ] && grep -c . "$LOG" || echo 0; }
WARN="ROUNDB_FC_FORCE_PUSH=on ROUNDB_FC_PRIVATE_PUSH=on ROUNDB_FC_PRIVATE_PUSH_MODE=warn ROUNDB_FC_PLAIN_PUSH_QUIET=off SHIP_IDENTITY=$S/ident.txt"
WARNQ="ROUNDB_FC_FORCE_PUSH=on ROUNDB_FC_PRIVATE_PUSH=on ROUNDB_FC_PRIVATE_PUSH_MODE=warn ROUNDB_FC_PLAIN_PUSH_QUIET=on SHIP_IDENTITY=$S/ident.txt"
BLOCK="ROUNDB_FC_FORCE_PUSH=on ROUNDB_FC_PRIVATE_PUSH=on ROUNDB_FC_PRIVATE_PUSH_MODE=block ROUNDB_FC_PLAIN_PUSH_QUIET=off SHIP_IDENTITY=$S/ident.txt"
BOGUS="ROUNDB_FC_FORCE_PUSH=on ROUNDB_FC_PRIVATE_PUSH=on ROUNDB_FC_PRIVATE_PUSH_MODE=maybe ROUNDB_FC_PLAIN_PUSH_QUIET=off SHIP_IDENTITY=$S/ident.txt"
WARNX="ROUNDB_FC_FORCE_PUSH=on ROUNDB_FC_PRIVATE_PUSH=on ROUNDB_FC_PRIVATE_PUSH_MODE=warn ROUNDB_FC_PLAIN_PUSH_QUIET=off SHIP_IDENTITY=$S/no-such-identity.txt"

echo "-- ALLOW first: a clean push in warn mode logs nothing and forces nothing"
push "$S/clean" clean1 "$WARN" origin main
[ $RC -eq 2 ] && grep -q "PUSH ·" "$ERRF" && ! grep -q "LEAKAGE SCAN" "$ERRF" && ! grep -q "HARD STOP" "$ERRF" && ok "clean: first sight = the ordinary signpost" || bad "clean first sight (rc=$RC $(head -c 200 "$ERRF"))"
push "$S/clean" clean1 "$WARN" origin main
[ $RC -eq 0 ] && [ ! -s "$OUTF" ] && ok "clean: repeat is allowed, no warning text" || bad "clean repeat (rc=$RC out=$(head -c 200 "$OUTF"))"
[ "$(loglines)" = 0 ] && ok "clean: nothing logged" || bad "clean: log has $(loglines) line(s)"
[ ! -e "$TW/clean1.pushwarn" ] && ok "clean: no end-of-turn marker" || bad "clean: marker written"
stop clean1 "done"; [ $RC -eq 0 ] && ! grep -q '"block"' "$OUTF" && ok "clean: end of turn not forced" || bad "clean: end of turn blocked ($(head -c 200 "$OUTF"))"

echo "-- private-repo push stays unscanned (warn mode)"
mkdir -p "$S/hpers/.claude" "$S/hpers/.config/lifehack"; echo "$S/leaky" > "$S/hpers/.config/lifehack/personal-code"
( cd "$S/leaky" && env $WARN HOME="$S/hpers" CLAUDE_CODE_SESSION_ID=pers bash "$PUSH" <<<"$(bashjson "git $PUSHW origin main" pers)" >"$OUTF" 2>"$ERRF" ); RC=$?
[ $RC -eq 2 ] && grep -q "PUSH ·" "$ERRF" && ! grep -q "LEAKAGE SCAN\|HARD STOP" "$ERRF" && ok "personal code repo: signpost only, no scan" || bad "personal repo (rc=$RC $(head -c 200 "$ERRF"))"
[ "$(loglines)" = 0 ] && ok "personal code repo: nothing logged" || bad "personal repo logged"

echo "-- warn mode: a planted private name to a public remote"
push "$S/leaky" leak1 "$WARN" origin main
[ $RC -eq 2 ] && grep -q "PUSH ·" "$ERRF" && grep -q "LEAKAGE SCAN (warn mode)" "$ERRF" && ! grep -q "HARD STOP" "$ERRF" && ok "first sight: the signpost, carrying the findings (not a hard stop)" || bad "warn first sight (rc=$RC $(head -c 300 "$ERRF"))"
push "$S/leaky" leak1 "$WARN" origin main
[ $RC -eq 0 ] && ok "repeat: the push is ALLOWED" || bad "warn repeat not allowed (rc=$RC $(head -c 300 "$ERRF"))"
python3 -c 'import json,sys; h=json.load(open(sys.argv[1]))["hookSpecificOutput"]; assert h["hookEventName"]=="PreToolUse" and "PUSH SCAN WARNING" in h["additionalContext"] and "permissionDecision" not in h' "$OUTF" 2>/dev/null \
  && ok "the finding reaches Claude as additionalContext (no permission decision)" || bad "no additionalContext warning ($(head -c 300 "$OUTF"))"
N1="$(loglines)"; [ "$N1" -ge 1 ] && ok "logged: $N1 line(s) in <notes>/state/push-warnings.log" || bad "nothing logged"
python3 - "$LOG" "$LEAKSHA" <<'PY' && ok "each log line: time, repo, remote, range, commit SHAs, finding, session" || bad "log line fields wrong: $(head -c 400 "$LOG")"
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
for r in rows:
    assert r["time"] and r["repo"].endswith("/leaky") and r["remote"] == "origin" and "github.com" in r["url"], r
    assert r["range"] == "origin/main..main" and sys.argv[2] in r["commits"] and r["session"] == "leak1" and r["finding"], r
assert any("Quillfeather" in r["finding"] or "identity" in r["finding"].lower() for r in rows), rows
PY
push "$S/leaky" leak1 "$WARN" origin main
[ $RC -eq 0 ] && [ "$(loglines)" = "$N1" ] && ok "the same push again (the guard's twin registration): not logged twice" || bad "duplicate log lines ($(loglines) vs $N1)"
[ -s "$TW/leak1.pushwarn" ] && ok "end-of-turn marker written for this session" || bad "no marker"
IDS="$(python3 -c 'import json,sys; print(" ".join(json.loads(l)["id"] for l in open(sys.argv[1]) if l.strip()))' "$TW/leak1.pushwarn")"

echo "-- end of turn: the report is forced, then clears once given"
stop other "done"; [ $RC -eq 0 ] && ! grep -q '"block"' "$OUTF" && ok "another session is not forced" || bad "other session blocked"
stop leak1 "Pushed it."
[ $RC -eq 0 ] && grep -q '"decision": "block"' "$OUTF" && grep -q "PUSH WARNING pw-" "$OUTF" && ok "unreported: end of turn BLOCKS, listing one line per finding" || bad "not forced ($(head -c 300 "$OUTF"))"
stop leak1 "Pushed it." true
[ $RC -eq 0 ] && grep -q '"decision": "block"' "$OUTF" && ok "still unreported (stop_hook_active): blocks again" || bad "active stop did not block"
MSG="Pushed. Leakage scan warnings:"; for i in $IDS; do MSG="$MSG
PUSH WARNING $i: a private name went to the public remote"; done
stop leak1 "$MSG" true
[ $RC -eq 0 ] && ! grep -q '"block"' "$OUTF" && ok "reported (every id in the final message): the stop clears" || bad "report did not clear ($(head -c 300 "$OUTF"))"
[ ! -e "$TW/leak1.pushwarn" ] && ok "marker removed once reported" || bad "marker still there"
stop leak1 "next turn"; [ $RC -eq 0 ] && ! grep -q '"block"' "$OUTF" && ok "next turn: nothing owed" || bad "next turn blocked"
[ "$(loglines)" = "$N1" ] && ok "the log keeps every entry after the report" || bad "log changed by the report"

echo "-- end of turn: partial report keeps only the unreported; never wedges"
push "$S/leaky" leak2 "$WARN" origin main; push "$S/leaky" leak2 "$WARN" origin main
printf '%s\n' '{"id":"pw-fakeextra01","session":"leak2","repo_name":"leaky","remote":"origin","range":"r","finding":"second finding","log":"'"$LOG"'"}' >> "$TW/leak2.pushwarn"
ID1="$(python3 -c 'import json,sys; print(json.loads(open(sys.argv[1]).readline())["id"])' "$TW/leak2.pushwarn")"
stop leak2 "PUSH WARNING $ID1: reported"
grep -q "pw-fakeextra01" "$OUTF" && ! grep -q "$ID1" "$OUTF" && ok "partial report: only the unreported id is still asked for" || bad "partial report ($(head -c 300 "$OUTF"))"
stop leak2 "x" true; stop leak2 "x" true; stop leak2 "x" true
[ $RC -eq 0 ] && ! grep -q '"block"' "$OUTF" && grep -q "still UNREPORTED" "$ERRF" && ok "after 3 asks with nothing reported: stops blocking, says so" || bad "wedge guard ($(head -c 200 "$OUTF") / $(head -c 200 "$ERRF"))"
unrep() { python3 -c 'import json,sys; print(sum(1 for l in open(sys.argv[1]) if l.strip() and json.loads(l).get("session")=="leak2" and json.loads(l).get("status","").startswith("UNREPORTED after 3 asks")))' "$LOG"; }
U1="$(unrep)"; [ "$U1" -ge 1 ] && ok "give-up is RECORDED in push-warnings.log as 'UNREPORTED after 3 asks' ($U1 line(s))" || bad "no UNREPORTED line in the log"
[ -s "$TW/leak2.pushwarn" ] && grep -q "pw-fakeextra01" "$TW/leak2.pushwarn" && ok "give-up keeps the marker: the findings are not dropped" || bad "marker dropped on give-up"
stop leak2 "x" true; [ "$(unrep)" = "$U1" ] && ok "same turn again: no duplicate UNREPORTED line" || bad "UNREPORTED line duplicated in the same turn"
PROMPT=p2 stop leak2 "next turn, unrelated"
[ $RC -eq 0 ] && grep -q '"decision": "block"' "$OUTF" && grep -q "pw-fakeextra01" "$OUTF" && ok "NEXT turn: asks again (one more nudge)" || bad "next turn did not ask again ($(head -c 200 "$OUTF"))"
PROMPT=p2 stop leak2 "still nothing" true
[ $RC -eq 0 ] && ! grep -q '"block"' "$OUTF" && [ "$(unrep)" -gt "$U1" ] && ok "next turn: ONE nudge only, then the give-up is logged again" || bad "next turn nudge budget ($(head -c 200 "$OUTF"))"
PROMPT=p3 stop leak2 "PUSH WARNING pw-fakeextra01: a second finding was flagged"
[ $RC -eq 0 ] && ! grep -q '"block"' "$OUTF" && [ ! -e "$TW/leak2.pushwarn" ] && ok "a later turn that reports it: clears, marker removed" || bad "late report did not clear"

echo "-- warn mode, a push that would be quiet (tracked remote, fc_plain_push_quiet ON): allowed + logged at once"
N2="$(loglines)"
push "$S/leaky" quiet1 "$WARNQ" origin main
[ $RC -eq 0 ] && grep -q "PUSH SCAN WARNING" "$OUTF" && [ "$(loglines)" -gt "$N2" ] && [ -s "$TW/quiet1.pushwarn" ] && ok "quiet push: allowed, warned, logged, marker" || bad "quiet warn (rc=$RC $(head -c 200 "$OUTF"))"

echo "-- block mode: the old hard stop, unchanged"
N3="$(loglines)"
push "$S/leaky" blk1 "$BLOCK" origin main
[ $RC -eq 2 ] && grep -q "HARD STOP (push guard): this push would publish private material" "$ERRF" && grep -q "WHY:" "$ERRF" && grep -q "WAY THROUGH:" "$ERRF" && grep -q "RULE:" "$ERRF" && ok "block mode: HARD STOP" || bad "block mode (rc=$RC $(head -c 200 "$ERRF"))"
push "$S/leaky" blk1 "$BLOCK" origin main
[ $RC -eq 2 ] && grep -q "HARD STOP" "$ERRF" && ok "block mode: HARD STOP again on retry" || bad "block retry (rc=$RC)"
push "$S/leaky" blk2 "$BOGUS" origin main
[ $RC -eq 2 ] && grep -q "HARD STOP (push guard): this push would publish" "$ERRF" && ok "an unknown mode value = block" || bad "bogus mode (rc=$RC)"
[ "$(loglines)" = "$N3" ] && [ ! -e "$TW/blk1.pushwarn" ] && ok "block mode: nothing logged, no marker" || bad "block mode logged"

echo "-- both modes: a scan that cannot run is a stop; a force push is a hard stop"
push "$S/leaky" cant1 "$WARNX" origin main
[ $RC -eq 2 ] && grep -q "leakage scan could not run" "$ERRF" && ok "warn mode: HARD_PRIVATE_CANNOT still a HARD STOP" || bad "cannot (rc=$RC $(head -c 200 "$ERRF"))"
CC1=$RC; cp "$ERRF" "$S/cant.err"; push "$S/leaky" cant1 "$WARNX" origin main; CC2=$RC
[ "$CC1" = 2 ] && [ "$CC2" = 2 ] && ok "scan cannot run: rc 2 on the first attempt and again on the retry" || bad "cannot attempts: rc $CC1 then $CC2"
grep -qF "the person runs this push themselves, if they mean to, in their own terminal: ! git $PUSHW origin main" "$S/cant.err" && ok "cannot message: names the one route, the person's own ! git $PUSHW" || bad "cannot message lacks the route: $(cat "$S/cant.err")"
grep -q "Do not work around this stop" "$S/cant.err" && ok "cannot message: tells the AI not to work around it" || bad "cannot message lacks the do-not-work-around line"
grep -q "WAY THROUGH: restore" "$S/cant.err" && bad "cannot message still says restore" || ok "cannot message: no 'restore' route"
push "$S/leaky" force1 "$WARN" --force origin main
[ $RC -eq 2 ] && grep -q "HARD STOP (push guard): this is a force push" "$ERRF" && ok "warn mode: force push still a HARD STOP" || bad "force (rc=$RC)"

echo "-- an unwritable log: falls back to BLOCK and says why"
mv "$LOG" "$S/log.saved"; chmod 555 "$NOTES/state"   # no log file, and the folder refuses a new one
push "$S/leaky" unw1 "$WARN" origin main; push "$S/leaky" unw1 "$WARN" origin main
[ $RC -eq 2 ] && grep -q "HARD STOP (push guard, warn mode)" "$ERRF" && grep -q "could not write" "$ERRF" && grep -q "push-warnings.log" "$ERRF" && ok "unwritable log: BLOCK, naming the log" || bad "unwritable log (rc=$RC $(head -c 300 "$ERRF"))"
[ ! -e "$TW/unw1.pushwarn" ] && ok "unwritable log: no marker either" || bad "marker written although log failed"
chmod 755 "$NOTES/state"

echo
echo "push scan warn mode: $P passed, $F failed"
[ "$F" -eq 0 ]
