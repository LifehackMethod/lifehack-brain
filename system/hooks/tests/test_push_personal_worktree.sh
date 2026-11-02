#!/bin/bash
# test_push_personal_worktree.sh -- the personal code repo is recognised by its git COMMON dir, so a linked
# worktree of it is PRIVATE too (push_facts.py is_personal_repo + the label in guard_git_push_signpost.sh).
# Fixed 2026-11-01: the old test compared --show-toplevel to the personal-code pointer, so a worktree of the
# private repo was scanned as if it were public (false HARD STOP).
# Fictional names only. No network, no real remote, nothing is ever pushed: the guard only reads local git state.
# GIT-WORD HYGIENE: payload commands are assembled from fragments so a live guard never sees a literal push.
# Run: bash system/hooks/tests/test_push_personal_worktree.sh   (exit 0 = all pass)
HERE="$(cd "$(dirname "$0")" && pwd)"; HOOKS="$(cd "$HERE/.." && pwd)"
PUSH="$HOOKS/guard_git_push_signpost.sh"; PF="$HOOKS/lib/push_facts.py"; SHARED="$(cd "$HOOKS/../../shared" && pwd)"
[ -f "$PUSH" ] && [ -f "$PF" ] || { echo "CANNOT RUN: $PUSH / $PF"; exit 1; }
S="$(cd "$(mktemp -d "${TMPDIR:-/tmp}/ppw.XXXXXX")" && pwd -P)"; trap 'rm -rf "$S"' EXIT
P=0; F=0; ERRF="$S/err"; OUTF="$S/out"
ok() { P=$((P+1)); }
bad() { F=$((F+1)); echo "FAIL: $1"; }
git_q() { git -C "$1" -c user.email=t@example.invalid -c user.name=t "${@:2}" >/dev/null 2>&1; }
bashjson() { T="$1" python3 -c 'import os,json; print(json.dumps({"tool_name":"Bash","tool_input":{"command":os.environ["T"]}}))'; }
PUSHW="pu""sh"
# fc_private_push_mode pinned to block: g1/g5 assert the leaky-push HARD STOP (warn mode: test_push_scan_warn.sh)
ENVS="ROUNDB_FC_FORCE_PUSH=on ROUNDB_FC_PRIVATE_PUSH=on ROUNDB_FC_PRIVATE_PUSH_MODE=block ROUNDB_FC_PLAIN_PUSH_QUIET=on ROUNDB_FC_LOCAL_PUSH_QUIET=on SHIP_IDENTITY=$S/ident.txt"
echo "fictional-secret-term-pond" > "$S/ident.txt"
PRIV_URL="https://github.com/fictional-org/pond-private.git"
PUB_URL="https://github.com/LifehackMethod/lifehack-brain.git"

# newrepo <dir> <url> <leaky:0|1> : one commit on main = origin/main; leaky adds a second, unpushed commit that the scan flags
newrepo() {
  mkdir -p "$1"; git init -q -b main "$1"; echo a > "$1/a.txt"; git_q "$1" add .; git_q "$1" commit -m init
  git -C "$1" remote add origin "$2"; git -C "$1" update-ref refs/remotes/origin/main HEAD
  git -C "$1" config branch.main.remote origin; git -C "$1" config branch.main.merge refs/heads/main
  if [ "$3" = "1" ]; then
    mkdir -p "$1/notes"; printf 'see %s/marlowe/Desktop/pond-notes/plan.md\n' "/Us""ers" > "$1/notes/n.md"
    git_q "$1" add .; git_q "$1" commit -m "add note"
  fi
}
newrepo "$S/personal" "$PRIV_URL" 1
git -C "$S/personal" worktree add -q -b wt "$S/wt-personal" >/dev/null 2>&1
newrepo "$S/other" "$PRIV_URL" 1
git -C "$S/other" worktree add -q -b wt "$S/wt-other" >/dev/null 2>&1
newrepo "$S/pubclone" "$PUB_URL" 1
git -C "$S/pubclone" worktree add -q -b wt "$S/wt-pub" >/dev/null 2>&1
newrepo "$S/clean-personal" "$PRIV_URL" 0
git -C "$S/clean-personal" worktree add -q -b wt "$S/wt-clean-personal" >/dev/null 2>&1
newrepo "$S/clean-other" "$PRIV_URL" 0
git -C "$S/clean-other" worktree add -q -b wt "$S/wt-clean-other" >/dev/null 2>&1
mkdir -p "$S/personal/sub" && echo x > "$S/personal/sub/x.txt"
ln -s "$S/personal" "$S/link-personal"
git -C "$S/personal" worktree add -q -b wtl "$S/wt-linked-via-symlink" >/dev/null 2>&1

n=0
mkhome() { n=$((n+1)); H="$S/h$n"; mkdir -p "$H/.claude" "$H/.config/lifehack"; [ -n "$1" ] && printf '%s\n' "$1" > "$H/.config/lifehack/personal-code"; }
# run <pointer-or-empty> <folder> <extra-env> <push args...>
run() {
  local ptr="$1" dir="$2" extra="$3"; shift 3
  mkhome "$ptr"
  local cmd; cmd=$(python3 -c 'import sys; print(" ".join(sys.argv[1:]))' git "$PUSHW" "$@")
  ( cd "$dir" && env $ENVS $extra HOME="$H" CLAUDE_CODE_SESSION_ID="s$n" bash "$PUSH" <<<"$(bashjson "$cmd")" >"$OUTF" 2>"$ERRF" ); RC=$?
}
is_private() { [ $RC -eq 2 ] && grep -q "PUSH ·" "$ERRF" && grep -q "PRIVATE — students never see this" "$ERRF" && ! grep -q "HARD STOP" "$ERRF"; }
is_hard()    { [ $RC -eq 2 ] && grep -q "HARD STOP" "$ERRF"; }
is_unknown() { [ $RC -eq 2 ] && grep -q "PUSH ·" "$ERRF" && grep -q "UNKNOWN" "$ERRF" && ! grep -q "HARD STOP" "$ERRF"; }
t_private() { local name="$1"; shift; run "$@"; if is_private; then ok; else bad "PRIVATE $name (rc=$RC $(head -c 220 "$ERRF"))"; fi; }
t_hard()    { local name="$1"; shift; run "$@"; if is_hard; then ok; else bad "HARD $name (rc=$RC $(head -c 220 "$ERRF"))"; fi; }
t_unknown() { local name="$1"; shift; run "$@"; if is_unknown; then ok; else bad "UNKNOWN $name (rc=$RC $(head -c 220 "$ERRF"))"; fi; }

echo "-- 1/2: the personal repo, main checkout and linked worktree, flaggable content, networked URL"
t_private "2 main checkout of the personal repo"        "$S/personal" "$S/personal" "" origin main:pond-feature
t_private "1 linked worktree of the personal repo"      "$S/personal" "$S/wt-personal" "" origin wt
mkdir -p "$S/wt-personal/deep/er"
t_private "1c worktree, nested subfolder"               "$S/personal" "$S/wt-personal/deep/er" "" origin wt
echo "-- 3: a worktree of some OTHER repo is still scanned"
t_hard "3 worktree of a repo that is not the pointer"   "$S/personal" "$S/wt-other" "" origin wt
t_hard "3b main checkout of a repo that is not the pointer" "$S/personal" "$S/other" "" origin main:pond-feature
echo "-- 4: clone / worktree of the public Lifehack repo stays public and scanned"
t_hard "4 worktree of the public clone (pointer elsewhere)" "$S/personal" "$S/wt-pub" "" origin wt
t_hard "4b pointer set to the public clone: public URL vetoes the exemption" "$S/pubclone" "$S/wt-pub" "" origin wt
t_hard "4c pointer set to the public clone, main checkout" "$S/pubclone" "$S/pubclone" "" origin main:pond-feature
echo "-- 5: unknown pointer fails closed"
t_hard "5a no pointer file"                              "" "$S/wt-personal" "" origin wt
t_hard "5b pointer names a folder that is gone"          "$S/does-not-exist" "$S/wt-personal" "" origin wt
t_hard "5c pointer line is blank"                        " " "$S/wt-personal" "" origin wt
echo "-- 6: common dir cannot be resolved"
mkdir -p "$S/notarepo"
t_unknown "6a push from a folder that is not a repo is never PRIVATE" "$S/personal" "$S/notarepo" "" origin main
# unit-level: is_personal_repo itself
unit() { UH="$S/uh"; mkdir -p "$UH/.config/lifehack"; printf '%s\n' "$2" > "$UH/.config/lifehack/personal-code"
  HOME="$UH" python3 "$PF" --repo "$1" --shared "$SHARED" --is-personal --url "${3:-$PRIV_URL}" 2>/dev/null; }
r=$(unit "$S/does-not-exist-at-all" "$S/personal"); if [ -z "$r" ]; then ok; else bad "6b missing folder must not be personal ($r)"; fi
r=$(unit "$S/wt-personal" "$S/personal"); if [ "$r" = "yes" ]; then ok; else bad "6c unit: worktree is personal ($r)"; fi
r=$(unit "$S/wt-personal/deep/er" "$S/personal"); if [ "$r" = "yes" ]; then ok; else bad "6d unit: nested folder of a worktree (relative common dir) ($r)"; fi
r=$(unit "$S/wt-other" "$S/personal"); if [ -z "$r" ]; then ok; else bad "6e unit: other repo is not personal ($r)"; fi
echo "-- 7: symlinks"
t_private "7a pointer is a symlink to the personal repo"   "$S/link-personal" "$S/wt-personal" "" origin wt
t_private "7b worktree reached through a symlinked folder" "$S/personal" "$S/link-personal" "" origin main:pond-feature
echo "-- 8: git -C names the target, not the shell cwd"
# -C goes before the verb, so build that form by hand
mkhome "$S/personal"
cmd="git -C $S/wt-personal $PUSHW origin wt"
( cd "$S/notarepo" && env $ENVS HOME="$H" CLAUDE_CODE_SESSION_ID="c$n" bash "$PUSH" <<<"$(bashjson "$cmd")" >"$OUTF" 2>"$ERRF" ); RC=$?
if is_private; then ok; else bad "8a -C personal worktree from an unrelated cwd (rc=$RC $(head -c 220 "$ERRF"))"; fi
mkhome "$S/personal"
cmd="git -C $S/wt-other $PUSHW origin wt"
( cd "$S/wt-personal" && env $ENVS HOME="$H" CLAUDE_CODE_SESSION_ID="d$n" bash "$PUSH" <<<"$(bashjson "$cmd")" >"$OUTF" 2>"$ERRF" ); RC=$?
if is_hard; then ok; else bad "8b -C other repo from inside the personal worktree is still scanned (rc=$RC $(head -c 220 "$ERRF"))"; fi
echo "-- 9: label parity with push_facts (clean content, so the label is what is tested)"
t_private "9a clean worktree of the personal repo is labelled PRIVATE" "$S/clean-personal" "$S/wt-clean-personal" "" origin wt
t_unknown "9b clean worktree of another repo is labelled UNKNOWN"     "$S/clean-personal" "$S/wt-clean-other" "" origin wt
echo "-- 10: local-path remote stays silent"
git init -q --bare "$S/bare.git"; git -C "$S/wt-clean-personal" remote add lan "$S/bare.git"
run "$S/clean-personal" "$S/wt-clean-personal" "" lan wt
if [ $RC -eq 0 ]; then ok; else bad "10 local-path remote from a personal worktree is quiet (rc=$RC $(head -c 160 "$ERRF"))"; fi
echo "-- gh veto: only ever a public veto"
mkdir -p "$S/bin"
printf '%s\n' '#!/bin/bash' 'echo PUBLIC' > "$S/bin/gh-public"; printf '%s\n' '#!/bin/bash' 'echo PRIVATE' > "$S/bin/gh-private"
printf '%s\n' '#!/bin/bash' 'exit 1' > "$S/bin/gh-broken"; chmod +x "$S/bin/gh-public" "$S/bin/gh-private" "$S/bin/gh-broken"
t_hard    "g1 gh says PUBLIC: the personal worktree loses its exemption"  "$S/personal" "$S/wt-personal" "PUSH_FACTS_GH=$S/bin/gh-public" origin wt
t_private "g2 gh says PRIVATE: exempt"                                     "$S/personal" "$S/wt-personal" "PUSH_FACTS_GH=$S/bin/gh-private" origin wt
t_private "g3 gh fails (offline/no auth): no veto, identity decides"       "$S/personal" "$S/wt-personal" "PUSH_FACTS_GH=$S/bin/gh-broken" origin wt
t_private "g4 gh binary missing: no veto"                                  "$S/personal" "$S/wt-personal" "PUSH_FACTS_GH=$S/bin/no-such-gh" origin wt
t_hard    "g5 gh PRIVATE never EXEMPTS a repo that is not the pointer"     "$S/personal" "$S/wt-other" "PUSH_FACTS_GH=$S/bin/gh-private" origin wt

echo "passed=$P failed=$F"
[ $F -eq 0 ]
