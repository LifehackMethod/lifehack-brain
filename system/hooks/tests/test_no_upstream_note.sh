#!/bin/bash
# test_no_upstream_note.sh -- guard_no_upstream_commit_signpost.sh with switch no_upstream_note ON.
#
# THE MISS (exam D-P06, 2026-11-02): the person asked "commit and git push", the session ran one command that committed
# AND pushed with -u, and this guard denied it (exit 2) because the branch had no upstream YET. Its message named no way
# through; the real one was to repeat the command, which only the hook's header said. A helper on an ordinary local work
# branch was stopped the same way.
#
# ON = the commit is never stopped. Silent when this same command pushes that branch, or the repo has no remote at all.
# Otherwise one note to Claude (additionalContext, exit 0), once per session/repo/branch, naming the one route: say it in
# the final message. OFF = the old deny-once, pinned at the end.
#
# Section 5 runs every PreToolUse hook registered in hooks/hooks.json, because a route that passes this hook and fails the
# next one is no route. Real git fixtures, a scratch HOME, payloads through the registered entry point.
#
# Git-word hygiene: this suite may run inside a live session whose guards read commands as text, so the verbs are built
# from fragments here and nothing in this file is executed as one literal top-level command.

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
GUARD="$REPO_ROOT/system/hooks/guard_no_upstream_commit_signpost.sh"
CONF="$REPO_ROOT/system/hooks/roundB.conf"

G=git; C=commit; P=push
pass=0; fail=0
T=$(mktemp -d "${TMPDIR:-/tmp}/no-upstream-note.XXXXXX") || exit 1
trap 'rm -rf "$T"' EXIT

ok()  { pass=$((pass+1)); printf '   ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }

quiet_git() { "$G" "$@" >/dev/null 2>&1; }

# new_repo <name>: bare origin + clone, `main` pushed and tracked, checked out on a local `work` with NO upstream and a
# changed website/index.html: the D-P06 fixture. Prints the clone path.
new_repo() {
  local b="$T/$1"
  mkdir -p "$b"
  quiet_git init --bare "$b/origin.git"
  quiet_git init "$b/work"
  quiet_git -C "$b/work" config user.email test@example.com
  quiet_git -C "$b/work" config user.name Test
  quiet_git -C "$b/work" checkout -b main
  quiet_git -C "$b/work" remote add origin "$b/origin.git"
  mkdir -p "$b/work/website"
  echo '<h1>site</h1>' > "$b/work/website/index.html"
  quiet_git -C "$b/work" add .
  "$G" -C "$b/work" "$C" -q -m init >/dev/null 2>&1
  "$G" -C "$b/work" "$P" -q -u origin main >/dev/null 2>&1
  quiet_git -C "$b/work" checkout -b work
  echo '<h1>site</h1><p>fixed</p>' > "$b/work/website/index.html"
  printf '%s' "$b/work"
}

# new_local_repo <name>: an ordinary repo with no remote at all.
new_local_repo() {
  local d="$T/$1"
  quiet_git init "$d"
  quiet_git -C "$d" config user.email test@example.com
  quiet_git -C "$d" config user.name Test
  echo hi > "$d/f.txt"
  quiet_git -C "$d" add .
  "$G" -C "$d" "$C" -q -m init >/dev/null 2>&1
  printf '%s' "$d"
}

payload() { T_CMD="$1" T_SID="$2" /usr/bin/python3 -c 'import json,os; print(json.dumps({"tool_name":"Bash","session_id":os.environ["T_SID"],"tool_input":{"command":os.environ["T_CMD"]}}))'; }

# run <cwd> <home> <sid> <command> [switch]: sets OUT ERR RC
run() {
  local dir="$1" home="$2" sid="$3" cmd="$4" sw="${5:-on}"
  mkdir -p "$home/.claude"
  OUT=$(cd "$dir" && payload "$cmd" "$sid" | HOME="$home" CLAUDE_CODE_SESSION_ID="$sid" ROUNDB_NO_UPSTREAM_NOTE="$sw" bash "$GUARD" 2>"$T/err"); RC=$?
  ERR=$(cat "$T/err")
}

note_text() { printf '%s' "$OUT" | /usr/bin/python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: raise SystemExit
print((d.get("hookSpecificOutput") or {}).get("additionalContext",""))'; }

silent() { # silent <label> <cwd> <cmd>
  local h; h=$(mktemp -d "$T/home.XXXXXX")
  run "$2" "$h" "s-$RANDOM" "$3"
  if [ "$RC" -eq 0 ] && [ -z "$OUT" ] && [ -z "$ERR" ]; then ok "silent: $1"
  else bad "silent: $1 (rc=$RC out=[${OUT:0:160}] err=[${ERR:0:160}])"; fi
}

speaks() { # speaks <label> <cwd> <cmd> <branch>
  local h txt; h=$(mktemp -d "$T/home.XXXXXX")
  run "$2" "$h" "s-$RANDOM" "$3"
  txt=$(note_text)
  if [ "$RC" -ne 0 ]; then bad "speaks: $1 (rc=$RC, the commit was stopped: ${ERR:0:160})"; return; fi
  case "$txt" in
    *"$4"*"final message"*) ok "speaks: $1" ;;
    *) bad "speaks: $1 (no street sign: out=[${OUT:0:200}] err=[${ERR:0:120}])"; return ;;
  esac
  if printf '%s' "$txt" | grep -qiE 'retry|re-run|rerun|run it again|try again|again|repeat|second attempt'; then
    bad "speaks: $1 (implies a repeat works: $txt)"
  fi
}

R=$(new_repo dp06)
L=$(new_local_repo plain)

echo "-- 1. D-P06's exact shape, and the same act in every shell shape: no note, no stop"
EXACT="$G add website/index.html && $G $C -q -m \"Fix broken contact link on website

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\" && $G $P -u origin work 2>&1; $G log --oneline -2"
silent "D-P06 exact command" "$R" "$EXACT"
silent "joined by ;"                 "$R" "$G $C -m x; $G $P -u origin work"
silent "newline separated"           "$R" "$G $C -m x
$G $P -u origin work"
silent "inside if/then"              "$R" "if $G $C -m x; then $G $P -u origin work; else echo no; fi"
silent "subshell"                    "$R" "($G $C -m x && $G $P -u origin work)"
silent "-- before the remote"        "$R" "$G $C -m x && $G $P -u -- origin work"
silent "commit -- pathspec"          "$R" "$G $C -m x -- website/index.html && $G $P -u origin work"
silent "--set-upstream HEAD"         "$R" "$G $C -m x && $G $P --set-upstream origin HEAD"
silent "no -u, names the branch"     "$R" "$G $C -m x && $G $P origin work"
silent "src:dst refspec"             "$R" "$G $C -m x && $G $P -u origin work:work"
silent "piped push"                  "$R" "$G $C -m x && $G $P -u origin work 2>&1 | tail -3"
silent "cd first"                    "$T" "cd $R && $G $C -m x && $G $P -u origin work"
silent "-C on both"                  "$T" "$G -C $R $C -m x && $G -C $R $P -u origin work"
silent "new branch, same command"    "$R" "$G checkout -b newb && $G $C -m x && $G $P -u origin newb"
silent "heredoc message" "$R" "$G $C -m \"\$(cat <<'EOF'
Fix it

It's fine
EOF
)\" && $G $P -u origin work"

echo "-- 2. an ordinary repo with no remote: nothing to mirror, no note, no stop"
silent "no remote, plain commit"     "$L" "$G $C -m x"
silent "no remote, new branch"       "$L" "$G checkout -b scratch && $G $C -m x"

echo "-- 3. real no-upstream work: never stopped, one street sign"
speaks "commit only"                 "$R" "$G $C -m x" work
speaks "commit -- pathspec"          "$R" "$G $C -m x -- website/index.html" work
speaks "commit in if/else, no push"  "$R" "if $G $C -m x; then echo ok; else echo no; fi" work
speaks "commit after a newline"      "$R" "$G add .
$G $C -m x" work
speaks "push of another branch"      "$R" "$G $C -m x && $G $P -u origin main" work
speaks "push BEFORE the commit"      "$R" "$G $P -u origin work; $G $C -m x" work
speaks "push only if commit failed"  "$R" "$G $C -m x || $G $P -u origin work" work
speaks "push only in the else arm"   "$R" "if $G $C -m x; then echo ok; else $G $P -u origin work; fi" work
speaks "dry-run push"                "$R" "$G $C -m x && $G $P --dry-run -u origin work" work
speaks "push with no refspec"        "$R" "$G $C -m x && $G $P" work
speaks "HEAD after switching branch" "$R" "$G $C -m x && $G checkout main && $G $P origin HEAD" work
speaks "push of another repo"        "$R" "$G $C -m x && $G -C $L $P -u origin work" work
speaks "new branch, no push"         "$R" "$G checkout -b newc && $G $C -m x" newc

G1=$(new_repo gone)
"$G" -C "$G1" "$P" -q -u origin work >/dev/null 2>&1
"$G" -C "$G1" "$P" -q origin --delete work >/dev/null 2>&1
quiet_git -C "$G1" fetch --prune origin
speaks "upstream deleted on the remote" "$G1" "$G $C -m x" work

echo "-- 4. once per session/repo/branch; other verbs and other branches untouched"
H=$(mktemp -d "$T/home.XXXXXX")
run "$R" "$H" once "$G $C -m x"; a="$RC|$(note_text)"
run "$R" "$H" once "$G $C -m y"; b="$RC|$OUT"
case "$a" in 0\|*work*) ok "first commit speaks" ;; *) bad "first commit should speak ($a)" ;; esac
[ "$b" = "0|" ] && ok "second commit is silent" || bad "second commit should be silent ($b)"
run "$R" "$H" once "$G checkout -b other && $G $C -m z"
case "$(note_text)" in *other*) ok "another branch gets its own note" ;; *) bad "another branch should speak ($OUT)" ;; esac
H=$(mktemp -d "$T/home.XXXXXX")
run "$R" "$H" covered "$G $C -m x && $G $P -u origin work"
run "$R" "$H" covered "$G $C -m y"
case "$(note_text)" in *work*) ok "a covered commit spends no marker: a later bare commit still speaks" ;; *) bad "covered commit must not spend the note ($OUT)" ;; esac
silent "not a commit"                "$R" "$G status"
silent "commit only as a mention"    "$R" "echo \"remember to $G $C this\""
TR=$(new_repo tracked)
"$G" -C "$TR" "$P" -q -u origin work >/dev/null 2>&1
silent "tracked branch"              "$TR" "$G $C -m x"
silent "not a repo"                  "$T" "$G $C -m x"
H=$(mktemp -d "$T/home.XXXXXX"); mkdir -p "$H/.claude"
OUT=$(printf 'not json' | HOME="$H" ROUNDB_NO_UPSTREAM_NOTE=on bash "$GUARD" 2>"$T/err"); RC=$?
{ [ "$RC" -eq 0 ] && [ -z "$OUT" ] && grep -q 'nothing was stopped' "$T/err"; } && ok "malformed payload: exit 0, no note, says so on stderr" || bad "malformed payload (rc=$RC out=$OUT err=$(cat "$T/err"))"

echo "-- 5. every registered PreToolUse hook, on the route and on the street-sign shape"
cat > "$T/chain.py" <<'PY'
# argv: repo_root cwd home command. Prints one line per hook that stopped or asked; exit 1 if any did.
import json, os, re, subprocess, sys
root, cwd, home, cmd = sys.argv[1:5]
os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
# The enver setup D-P06 ran in: a resolvable notes root whose ship identity lists the fixture's commit address.
os.makedirs(os.path.join(home, "notes", "config"), exist_ok=True)
open(os.path.join(home, "notes", "config", "ship-identity.md"), "w").write("test@example.com\n")
os.makedirs(os.path.join(home, ".config", "lifehack"), exist_ok=True)
open(os.path.join(home, ".config", "lifehack", "brain-root"), "w").write(os.path.join(home, "notes") + "\n")
hooks = json.load(open(os.path.join(root, "hooks", "hooks.json"), encoding="utf-8"))["hooks"]["PreToolUse"]
payload = json.dumps({"tool_name": "Bash", "session_id": "chain", "cwd": cwd, "hook_event_name": "PreToolUse", "tool_input": {"command": cmd}})
env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "TMPDIR", "SHELL")}
env.update(HOME=home, CLAUDE_PLUGIN_ROOT=root, CLAUDE_PROJECT_DIR=cwd, CLAUDE_CODE_SESSION_ID="chain", ROUNDB_NO_UPSTREAM_NOTE="on")
ran = stopped = 0
for blk in hooks:
    if not (blk.get("matcher", "*") == "*" or re.fullmatch(blk.get("matcher", ""), "Bash")):
        continue
    for h in blk.get("hooks", []):
        ran += 1
        p = subprocess.run(["/bin/bash", "-c", h["command"]], input=payload.encode(), capture_output=True, cwd=cwd, env=env, timeout=120)
        out = p.stdout.decode("utf-8", "replace")
        decided = re.search(r'"(?:permissionDecision|decision)"\s*:\s*"(deny|ask|block)"', out)
        if p.returncode != 0 or decided:
            stopped += 1
            print("STOPPED", h["command"][-60:], "rc=%d" % p.returncode, (p.stderr.decode("utf-8", "replace") + out)[:300].replace("\n", " "))
print("ran=%d stopped=%d" % (ran, stopped))
sys.exit(1 if stopped or not ran else 0)
PY
chain() { # chain <label> <cwd> <cmd>
  local h o; h=$(mktemp -d "$T/chainhome.XXXXXX")
  if o=$(/usr/bin/python3 "$T/chain.py" "$REPO_ROOT" "$2" "$h" "$3" 2>&1); then ok "chain passes: $1 ($(printf '%s' "$o" | tail -1))"
  else bad "chain: $1: $o"; fi
}
chain "D-P06 exact"          "$R" "$EXACT"
chain "chained ;"            "$R" "$G $C -m x; $G $P -u origin work"
chain "inside if/else"       "$R" "if $G $C -m x; then $G $P -u origin work; else echo no; fi"
chain "-- before the remote" "$R" "$G $C -m x && $G $P -u -- origin work"
chain "commit only"          "$R" "$G $C -m x"
chain "commit, if/else"      "$R" "if $G $C -m x -- website/index.html; then echo ok; else echo no; fi"
chain "no remote"            "$L" "$G $C -m x"

echo "-- 6. the switch"
grep -qE '^no_upstream_note=on[[:space:]]*$' "$CONF" && ok "roundB.conf ships no_upstream_note=on" || bad "roundB.conf has no no_upstream_note=on line"
H=$(mktemp -d "$T/home.XXXXXX")
run "$R" "$H" off "$G $C -m x && $G $P -u origin work" off; r1=$RC; e1="$ERR"
run "$R" "$H" off "$G $C -m x && $G $P -u origin work" off; r2=$RC
if [ "$r1" -eq 2 ] && [ "$r2" -eq 0 ]; then ok "OFF: the old deny-once, even with a chained push"
else bad "OFF should deny once then pass (r1=$r1 r2=$r2)"; fi
case "$e1" in *"no upstream"*) ok "OFF: the old deny text" ;; *) bad "OFF: old text missing ($e1)" ;; esac

echo
printf 'RESULT: %d passed, %d failed.\n' "$pass" "$fail"
[ "$fail" -eq 0 ] && { echo "NO-UPSTREAM NOTE GREEN"; exit 0; }
echo "NO-UPSTREAM NOTE RED"; exit 1
