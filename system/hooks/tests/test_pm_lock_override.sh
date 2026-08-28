#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the two halves of the owner's project-lock ruling, watched rather than asserted.
#      (1) arming a project LOCKS the window — a re-arm onto a different project is REFUSED;
#      (2) exactly two things change it: a new window, or THE HUMAN'S OWN WORDS in their own
#      prompt, which buys ONE change and is then burned. Plus the flag TTL, which sat inert in
#      these two files for a month across two separate "fixes".
# GUARDS: sandbox only. HOME is redirected under /tmp; nothing here touches the live store.
# REDIRECT: subjects are system/hooks/pm_flag.sh + system/hooks/pm_persist.sh.
# SIGNPOST: the rule and the incident behind it live in pm_flag.sh's own header.
# FAIL_POSTURE: N/A (a test). Non-zero exit = at least one case failed.
# UPDATED: 2026-08-15 (new — verify-hooks.sh recorded these two hooks as UNTESTED in this tree)
# ─────────────────────────────────────────────────────────────────────────────
#   bash system/hooks/tests/test_pm_lock_override.sh
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
PMF="$HOOKS/pm_flag.sh"
PMP="$HOOKS/pm_persist.sh"
SB=/tmp/pm-lock-test.$$
STORE="$SB/.claude/run/pm"
mkdir -p "$STORE"
A="$SB/alpha-brief.md"; B="$SB/beta-brief.md"; C="$SB/gamma-brief.md"
printf '# Alpha\n## CURRENT STATE\nalpha is where we are\n' > "$A"
printf '# Beta\n## CURRENT STATE\nbeta is where we are\n'   > "$B"
printf '# Gamma\n' > "$C"
# pm_flag.sh derives KEY="sess-$CLAUDE_CODE_SESSION_ID" — so the id must NOT carry that prefix
SESS=lock-test
KEY="sess-$SESS"
PASS=0; FAIL=0
ok(){   PASS=$((PASS+1)); printf '  ✅ %s\n' "$1"; }
bad(){  FAIL=$((FAIL+1)); printf '  ❌ %s\n     got: %s\n' "$1" "$2"; }
arm(){  env HOME="$SB" CLAUDE_CODE_SESSION_ID="$SESS" bash "$PMF" arm "$@"; }
pmf(){  env HOME="$SB" CLAUDE_CODE_SESSION_ID="$SESS" bash "$PMF" "$@"; }
# one human turn. $1 = what the person typed.
turn(){ printf '{"cwd":"%s","prompt":%s}' "$SB" "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1")" \
        | env HOME="$SB" CLAUDE_CODE_SESSION_ID="$SESS" bash "$PMP" 2>&1; }
lockslug(){ grep '^lock_slug=' "$STORE/lock-$KEY.project" 2>/dev/null | cut -d= -f2-; }

echo "── 1. the lock ───────────────────────────────────────────────────────────"
OUT="$(arm "$A" alpha root 2>&1)"; RC=$?
[ "$RC" = 0 ] && case "$OUT" in *ARMED:*alpha*) ok "first arm succeeds (exit 0)";; *) bad "first arm" "$OUT";; esac
[ "$RC" = 0 ] || bad "first arm exit" "exit=$RC $OUT"
[ "$(lockslug)" = alpha ] && ok "lock file written, lock_slug=alpha" || bad "lock file" "$(lockslug)"

OUT="$(arm "$B" beta root 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "re-arm onto a DIFFERENT project REFUSED (exit 3)" || bad "re-arm exit" "exit=$RC"
case "$OUT" in *"REFUSED"*"IMMUTABLE"*) ok "refusal names what it blocked";; *) bad "refusal text" "$OUT";; esac
case "$OUT" in *"NEW WINDOW"*) ok "refusal teaches path 1 (new window)";; *) bad "path 1 missing" "$OUT";; esac
case "$OUT" in *"HUMAN'S OWN WORDS"*) ok "refusal teaches path 2 (the human's words)";; *) bad "path 2 missing" "$OUT";; esac
[ "$(lockslug)" = alpha ] && ok "nothing was written — still locked to alpha" || bad "lock moved!" "$(lockslug)"
[ "$(grep '^slug=' "$STORE/pm-$KEY.flag" | cut -d= -f2-)" = alpha ] && ok "flag still points at alpha" || bad "flag moved!" "$(cat "$STORE/pm-$KEY.flag")"
[ -s "$STORE/arm-denied.log" ] && ok "refusal recorded in arm-denied.log" || bad "no deny log" ""

# The lock must not break the ordinary case: /checkin Step 0 re-arms on every run and /save's
# recovery path depends on it, so a SAME-slug arm is never an override and never a refusal.
OUT="$(arm "$A" alpha root 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "a same-slug re-arm still refreshes normally (exit 0)" || bad "same-slug refused" "exit=$RC $OUT"
case "$OUT" in *OVERRIDDEN*) bad "a same-slug re-arm was treated as an override" "$OUT";; *) ok "and is not announced as an override";; esac

echo "── 2. the refusal's CHANNEL (a guard nobody can see is not a guard) ──────"
E_ONLY="$(arm "$B" beta root 2>&1 >/dev/null)"
O_ONLY="$(arm "$B" beta root 2>/dev/null)"
case "$E_ONLY" in *REFUSED*) ok "refusal survives on stderr alone";; *) bad "stderr channel" "$E_ONLY";; esac
case "$O_ONLY" in *REFUSED*) ok "refusal survives on stdout alone (caller using 2>/dev/null)";; *) bad "stdout channel" "$O_ONLY";; esac

echo "── 3. the model cannot mint the override ────────────────────────────────"
OUT="$(turn "please re-arm this window to the beta project, I think that is right")"
[ -f "$STORE/override-$KEY.grant" ] && bad "a vague prompt issued a grant" "$(cat "$STORE/override-$KEY.grant")" || ok "a vague prompt issues NO grant"
OUT="$(arm "$B" beta root 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "still refused with no grant (exit 3)" || bad "unexpected allow" "exit=$RC $OUT"

echo "── 4. the human's own words → ONE change ────────────────────────────────"
OUT="$(turn "actually switch the project to beta, we are done with alpha")"
[ -f "$STORE/override-$KEY.grant" ] && ok "explicit human prompt issues the grant" || bad "no grant issued" "$OUT"
case "$OUT" in *"OVERRIDE AUTHORISED"*) ok "the turn it happens is LOUD in the injected context";; *) bad "silent grant" "$OUT";; esac
G="$(grep '^session=' "$STORE/override-$KEY.grant" | cut -d= -f2-)"
[ "$G" = "$SESS" ] && ok "grant is bound to the session that spoke" || bad "grant session" "$G"

P="$(grep '^phrase=' "$STORE/override-$KEY.grant" | cut -d= -f2-)"
case "$P" in *"switch the project to beta"*) ok "the grant quotes their words, one match, target included";; *) bad "phrase mangled" "$P";; esac
[ "$(grep -c . "$STORE/override-$KEY.grant")" = 4 ] && ok "grant file is 4 clean key=value lines" || bad "grant file shape" "$(cat "$STORE/override-$KEY.grant")"

OUT="$(arm "$B" beta root 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "the override ALLOWS the change (exit 0)" || bad "override did not allow" "exit=$RC $OUT"
case "$OUT" in *"LOCK OVERRIDDEN"*alpha*beta*) ok "the allow is LOUD and names both projects";; *) bad "quiet allow" "$OUT";; esac
# THE ALLOW'S CHANNEL, on a fresh mismatch each time — an override announced only on stderr is
# invisible to `... 2>/dev/null`, which is the same PASS-and-protect-nothing failure as a refusal
# printed on the wrong channel. (A same-slug re-arm is never an override, so each half needs its
# own authorisation and its own unarmed target.)
turn "switch the project to alpha" >/dev/null
A_OUT="$(arm "$A" alpha root 2>/dev/null)"
case "$A_OUT" in *"LOCK OVERRIDDEN"*) ok "the override banner survives on stdout alone";; *) bad "announce stdout channel" "$A_OUT";; esac
turn "switch the project to beta" >/dev/null
A_ERR="$(arm "$B" beta root 2>&1 >/dev/null)"
case "$A_ERR" in *"LOCK OVERRIDDEN"*) ok "the override banner survives on stderr alone";; *) bad "announce stderr channel" "$A_ERR";; esac
[ "$(lockslug)" = beta ] && ok "lock rewritten to beta" || bad "lock not rewritten" "$(lockslug)"
grep -q '^origin=human-override' "$STORE/lock-$KEY.project" && ok "lock records origin=human-override" || bad "no origin" "$(cat "$STORE/lock-$KEY.project")"
grep -q '^previous_slug=alpha' "$STORE/lock-$KEY.project" && ok "lock records the project it moved OFF" || bad "no previous_slug" ""
grep -q 'arm-override' "$STORE/arm-events.log" && ok "arm-events.log carries the arm-override artifact" || bad "no artifact" ""
[ -f "$STORE/override-$KEY.grant" ] && bad "grant NOT burned" "still present" || ok "grant burned on use"

echo "── 5. once means once ───────────────────────────────────────────────────"
OUT="$(arm "$C" gamma root 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "a second change on the same authorisation is REFUSED" || bad "second change allowed!" "exit=$RC"
OUT="$(turn "ok switch the project to gamma")" ; [ -f "$STORE/override-$KEY.grant" ] && ok "re-authorising issues a fresh grant" || bad "no re-grant" ""
OUT="$(turn "actually never mind, what is the weather")"
[ -f "$STORE/override-$KEY.grant" ] && bad "grant survived the next turn" "still present" || ok "an unspent grant dies on their next message"

echo "── 6. a foreign session cannot spend someone else's word ────────────────"
printf 'granted_at=%s\nsession=%s\nphrase=override the project lock\n' "$(date +%s)" other-window > "$STORE/override-$KEY.grant"
OUT="$(arm "$C" gamma root 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "grant from another session is not consumable (exit 3)" || bad "cross-session spend!" "exit=$RC"

echo "── 7. a stale grant is not consumable ───────────────────────────────────"
printf 'granted_at=%s\nsession=%s\nphrase=override the project lock\n' "$(( $(date +%s) - 7200 ))" "$SESS" > "$STORE/override-$KEY.grant"
OUT="$(arm "$C" gamma root 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "a 2h-old grant is expired (exit 3)" || bad "stale grant spent!" "exit=$RC"

echo "── 8. an override may not install a broken identity ─────────────────────"
turn "switch the project to gamma" >/dev/null
OUT="$(arm gamma-not-a-path gamma root 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "malformed arm refused even WITH the human's word" || bad "malformed allowed" "exit=$RC"
case "$OUT" in *MALFORMED*) ok "refusal says WHY it is malformed";; *) bad "no malformed note" "$OUT";; esac
[ -f "$STORE/override-$KEY.grant" ] && ok "the authorisation was NOT spent on the broken command" || bad "grant burned by a typo" ""
OUT="$(arm "$C" gamma root 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "the corrected command then works on the same authorisation" || bad "corrected arm failed" "exit=$RC $OUT"

echo "── 9. clear frees the FLAG, never the LOCK ──────────────────────────────"
OUT="$(pmf clear 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "clear REFUSED while locked (exit 3)" || bad "clear allowed" "exit=$RC $OUT"
[ -f "$STORE/pm-$KEY.flag" ] && ok "flag untouched by the refused clear" || bad "flag deleted" ""
turn "override the project lock" >/dev/null
OUT="$(pmf clear 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "clear ALLOWED by the human's word (exit 0)" || bad "granted clear failed" "exit=$RC $OUT"
[ -f "$STORE/pm-$KEY.flag" ] && bad "flag not cleared" "" || ok "flag deleted"
[ -f "$STORE/lock-$KEY.project" ] && ok "⭐ THE LOCK SURVIVED THE CLEAR" || bad "LOCK DELETED BY CLEAR" "the bypass is open"
[ "$(lockslug)" = gamma ] && ok "lock still names gamma" || bad "lock slug" "$(lockslug)"
OUT="$(arm "$A" alpha root 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "clear+arm-elsewhere is NOT a bypass — still refused" || bad "BYPASS: clear then re-arm" "exit=$RC"

echo "── 10. the TTL, which was inert until 2026-08-15 ────────────────────────"
T="$(bash "$PMF" ttl)"; [ "$T" = 36 ] && ok "ttl verb reports 36" || bad "ttl verb" "$T"
grep -c '^TTL_HOURS=' "$PMF" >/dev/null
[ "$(grep -c 'PM_TTL_HOURS:-36' "$PMF")" = 1 ] && ok "the number is defined exactly once in pm_flag.sh" || bad "duplicate/absent definition" ""
mkfl(){ printf 'doc_path=%s\nslug=alpha\ndesk=root\narmed_at=%s\ncwd=%s\nsession=%s\n' "$A" "$2" "$SB" "$SESS" > "$STORE/pm-$KEY.flag"; }
mkfl x "$(( $(date +%s) - 20*3600 ))"; turn "hello" >/dev/null
[ -f "$STORE/pm-$KEY.flag" ] && ok "a 20h-old flag SURVIVES (would have died at the old 12h)" || bad "20h died" ""
mkfl x "$(( $(date +%s) - 40*3600 ))"; turn "hello" >/dev/null
[ -f "$STORE/pm-$KEY.flag" ] && bad "a 40h-old flag SURVIVED — the TTL is still inert" "" || ok "a 40h-old flag EXPIRES (this is what never fired before)"
mkfl x "$(date +%s)"; for i in 1 2 3; do turn "still working" >/dev/null; done
[ -f "$STORE/pm-$KEY.flag" ] && ok "a live flag survives ordinary turns (no every-turn delete)" || bad "flag deleted mid-session" ""
# single-source proof: a copy of pm_persist run beside a pm_flag.sh whose TTL is 5h
FAKE="$SB/fake"; mkdir -p "$FAKE"
sed 's/PM_TTL_HOURS:-36/PM_TTL_HOURS:-5/' "$PMF" > "$FAKE/pm_flag.sh"; cp "$PMP" "$FAKE/pm_persist.sh"
mkfl x "$(( $(date +%s) - 10*3600 ))"
printf '{"cwd":"%s","prompt":"hi"}' "$SB" | env HOME="$SB" CLAUDE_CODE_SESSION_ID="$SESS" bash "$FAKE/pm_persist.sh" >/dev/null 2>&1
[ -f "$STORE/pm-$KEY.flag" ] && bad "pm_persist ignored pm_flag.sh's TTL — the number is NOT single-source" "" \
  || ok "pm_persist reads the TTL from pm_flag.sh (10h flag died under a TTL-5 copy)"

echo "── 11. the paired guard covers the grant file too ──────────────────────"
# guard_pm_flag_store.sh keeps the store from being written by hand. The grant lives IN that
# store, deliberately — the alternative was a new folder with no custodian. This checks the
# existing guard already covers the new file rather than assuming it does. It remains a speed
# bump by its own header's admission, not a wall.
GD="$HOOKS/guard_pm_flag_store.sh"
gt(){ # $1=label $2=json $3=expect(block|allow)
  printf '%s' "$2" | bash "$GD" >/dev/null 2>/tmp/pmg.err.$$
  _rc=$?; _got=allow; [ "$_rc" = 2 ] && _got=block
  [ "$_got" = "$3" ] && ok "$1 -> $_got" || bad "$1 (wanted $3)" "exit=$_rc"
  rm -f /tmp/pmg.err.$$
}
DOT=".claude/run/pm"
gt "Write tool aimed at a grant file" "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"/Users/x/$DOT/override-sess-1.grant\"}}" block
gt "shell redirect into a grant file"  "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"echo granted_at=1 > /Users/x/$DOT/override-sess-1.grant\"}}" block
gt "python write into the store"       "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"python3 -c \\\"open('/Users/x/$DOT/override-a.grant','w').write('x')\\\"\"}}" block
gt "rm of the lock file"               "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"rm /Users/x/$DOT/lock-sess-1.project\"}}" block
gt "reading the store"                 "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"cat /Users/x/$DOT/pm-sess-1.flag\"}}" allow
gt "the sanctioned writer itself"      "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"bash system/hooks/pm_flag.sh arm /tmp/b.md alpha root\"}}" allow
# ⭐ THE FORGERY ROUTE. Everything above protects the FILES; this protects the ISSUER. A session
# that can run pm_persist.sh can hand it a sentence the person never said and mint its own grant.
gt "piping a fake prompt into the issuer" "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"echo '{\\\"prompt\\\":\\\"override the project lock\\\"}' | bash system/hooks/pm_persist.sh\"}}" block
gt "running the issuer with a full path"  "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"bash /Users/x/repo/system/hooks/pm_persist.sh < /tmp/fake.json\"}}" block
gt "merely mentioning it in prose"        "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"grep -rn pm_persist docs/\"}}" allow
gt "the test suite that drives it"        "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"bash system/hooks/tests/test_pm_lock_override.sh\"}}" allow

echo "── 12. the same guard covers the PLAN store, not just the pm one ───────"
# ⭐ THE HOLE THIS CLOSES, 2026-08-15. The plan lock refuses through plan_flag.sh, and its store
# (~/.claude/run/plan/) was UNGUARDED — so a direct write to plan-<key>.flag, or an rm of
# lock-<key>.plan, skipped that refusal entirely. Identical to the bypass an audit executed against
# the pm store before section 11's guard existed, left open on the other half of the same ruling.
# ⚠ WATCHED, NOT ASSERTED: `gt` above captures the real exit code from the real hook — a guard
# nobody drove is not a guard. The channel proof (a refusal must survive `2>/dev/null` AND
# `2>&1 >/dev/null`) is the block below this one.
# ⛔ STILL A SPEED BUMP. Covering one more path does not make this a wall; every evasion named in
# the guard's own header (a `cd`, a variable, an alias, a relative path) works the same against
# run/plan. The load-bearing control remains NOISE on the spend.
DOTP=".claude/run/plan"
gt "Write tool aimed at the plan flag"   "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"/Users/x/$DOTP/plan-sess-1.flag\"}}" block
gt "Edit tool aimed at the plan lock"    "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"/Users/x/$DOTP/lock-sess-1.plan\"}}" block
gt "shell redirect into the plan flag"   "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"echo plan=b > /Users/x/$DOTP/plan-sess-1.flag\"}}" block
gt "rm of the plan LOCK file"            "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"rm /Users/x/$DOTP/lock-sess-1.plan\"}}" block
gt "python write into the plan store"    "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"python3 -c \\\"open('/Users/x/$DOTP/plan-sess-1.flag','w').write('x')\\\"\"}}" block
gt "reading the plan store"              "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"cat /Users/x/$DOTP/plan-sess-1.flag\"}}" allow
gt "the sanctioned plan writer itself"   "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"bash system/hooks/plan_flag.sh set /tmp/p.md\"}}" allow
# ⛔ THE BOUNDARY, which is why `plan` is an alternative inside the anchor and never a bare prefix.
# Section 11's own note records the pm half of this: run/pm-ack was once swallowed as the store and
# the guard blocked the build of its own successor. A sibling folder must stay writable.
gt "a SIBLING folder, not the store"     "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"rm -rf /Users/x/.claude/run/plans-archive/old\"}}" allow
gt "Write into a sibling folder"         "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"/Users/x/.claude/run/planner/notes.md\"}}" allow

# THE REDIRECT MUST MATCH THE STORE. A plan-store denial that sends the reader to pm_flag.sh is a
# wrong instruction stated with total confidence — worse than none, because it teaches the reader
# the guard does not know what it just blocked.
_pr="$(printf '{"tool_name":"Bash","tool_input":{"command":"rm /Users/x/%s/lock-sess-1.plan"}}' "$DOTP" | bash "$GD" 2>&1 >/dev/null)"
case "$_pr" in *plan_flag.sh*) ok "the plan denial redirects to plan_flag.sh, not pm_flag.sh";; *) bad "plan denial names the wrong writer" "$_pr";; esac
case "$_pr" in *"ONE grant"*|*"one grant"*) ok "and says the one grant covers both locks";; *) bad "plan denial hides that the grant is shared" "$_pr";; esac

echo "── 13. the new refusal survives BOTH redirection shapes ────────────────"
# ⛔ A GUARD THAT PRINTS ITS REFUSAL ON THE WRONG CHANNEL SCORES PASS AND PROTECTS NOTHING — that
# exact failure is on record in this repo. The refusal is on stderr and the exit code is 2, so:
# under `2>/dev/null` the TEXT is gone but the BLOCK still stands (exit 2 is what stops the tool);
# under `2>&1 >/dev/null` the text is what survives. Both are checked, on the real hook.
PJ="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"echo x > /Users/x/$DOTP/plan-sess-1.flag\"}}"
printf '%s' "$PJ" | bash "$GD" >/dev/null 2>/dev/null; _c1=$?
[ "$_c1" = 2 ] && ok "under 2>/dev/null the BLOCK still stands (exit=2)" || bad "silenced stderr lost the block" "exit=$_c1"
_t2="$(printf '%s' "$PJ" | bash "$GD" 2>&1 >/dev/null)"; _c2=$?
case "$_t2" in *"plan-arming store"*) ok "under 2>&1 >/dev/null the REASON still arrives";; *) bad "refusal text vanished on the wrong channel" "rc=$_c2 out=$_t2";; esac
_t3="$(printf '%s' "$PJ" | bash "$GD" 2>/dev/null)"
[ -z "$_t3" ] && ok "and nothing leaks onto stdout (a block speaks on stderr only)" || bad "refusal printed on stdout" "$_t3"

echo "── 14. a WINDOWS drive-letter doc_path is ABSOLUTE (2026-08-28) ─────────"
# REPRO for the bug this section was written against. `X:\...\brief.md` is absolute and does NOT
# begin with "/", and every absolute-path test in this plane was a bare `${2#/}` compare or a `/*)`
# case — so a native Windows path was classified RELATIVE. Three consequences, each asserted below,
# and all of them SILENT on the day: the arm printed ARMED and exited 0 throughout.
#   (a) NO LOCK WAS WRITTEN. The window stayed UNLOCKED, so everything section 1 verifies — the
#       immutability that is the whole point of this file — did not exist on Windows at all.
#   (b) THE MALFORMED-ARM NOTE FIRED ON A WELL-FORMED PATH. On a locked window that note deliberately
#       pre-empts the grant (section 8), so an override the human HAD authorised could never be
#       spelled in any way that spent it. Section 8's own guarantee inverted: not "a typo cannot burn
#       the authorisation" but "the authorisation cannot be used".
#   (c) THE PERSISTENCE HOOK JOINED IT ONTO THE ARMING CWD, so the live brief was announced as
#       NOT YET CREATED every turn and the doc excerpt was never read.
# ⭐ PORTABLE ON PURPOSE — nothing here stats the file or needs a G: drive to exist. (a) and (b) are
# pure string decisions inside pm_flag.sh; (c) asserts the announced PATH and never the freshness
# word, so a Linux or macOS run exercises the identical logic. Do not "fix" this by gating it on
# uname: the predicate is deliberately not OS-gated, and a test that only runs on one platform is
# how this bug survived in the first place.
WSESS=win-test
WKEY="sess-$WSESS"
WIN='X:\Some Folder\Notes\projects\delta\brief.md'
WIN2='X:\Some Folder\Notes\projects\epsilon\brief.md'
warm(){ env HOME="$SB" CLAUDE_CODE_SESSION_ID="$WSESS" bash "$PMF" arm "$@"; }
wpmf(){ env HOME="$SB" CLAUDE_CODE_SESSION_ID="$WSESS" bash "$PMF" "$@"; }
wturn(){ printf '{"cwd":"%s","prompt":%s}' "$SB" "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1")" \
         | env HOME="$SB" CLAUDE_CODE_SESSION_ID="$WSESS" bash "$PMP" 2>&1; }
wlockslug(){ grep '^lock_slug=' "$STORE/lock-$WKEY.project" 2>/dev/null | cut -d= -f2-; }
wlockdoc(){  grep '^lock_doc='  "$STORE/lock-$WKEY.project" 2>/dev/null | cut -d= -f2-; }

# (a) the lock — the assertion that was FALSE before the fix
OUT="$(warm "$WIN" delta business 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "a drive-letter arm succeeds (exit 0)" || bad "windows arm exit" "exit=$RC $OUT"
[ "$(wlockslug)" = delta ] && ok "⭐ AND IT WRITES A LOCK — the bug was that it did not" || bad "NO LOCK on a windows path: window left UNLOCKED" "lock_slug=$(wlockslug)"
[ "$(wlockdoc)" = "$WIN" ] && ok "lock_doc keeps the native spelling verbatim" || bad "lock_doc mangled" "$(wlockdoc)"
[ "$(wpmf locked 2>/dev/null)" = delta ] && ok "\`locked\` reports delta, not none" || bad "locked verb" "$(wpmf locked 2>&1)"

# and the lock it now writes must actually REFUSE, or it is a file rather than a guard
OUT="$(warm "$WIN2" epsilon business 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "re-arm onto a different project REFUSED (exit 3)" || bad "windows lock does not refuse" "exit=$RC $OUT"
[ "$(wlockslug)" = delta ] && ok "and nothing moved" || bad "lock moved" "$(wlockslug)"

# (b) a WELL-FORMED native path must never be called malformed
# ⚠ THIS TICK IS ONLY LOAD-BEARING ONCE (a) HOLDS, and a future reader will misread it otherwise.
# Against the pre-fix code it passes for an empty reason: with no lock written, the re-arm above
# was never refused at all, so there was no refusal text to carry a MALFORMED note. It becomes a
# real assertion only when a lock exists to do the refusing. Measured 2026-08-28: pre-fix this
# section ran 10 failures with this one green; post-fix, 0 (bar the persistence-hook pair).
case "$OUT" in *MALFORMED*) bad "a well-formed windows path was called MALFORMED — the override can never be spent" "$OUT";; *) ok "⭐ refusal does NOT claim the windows path is malformed";; esac

# ⛔ AND THE FIX MUST NOT BE TOO PERMISSIVE. A genuinely broken arm — the known arg-order slip, a
# bare slug in the doc_path slot — is still malformed, still refused, and still leaves the grant
# unburned. Without this, "accept more shapes" quietly becomes "accept anything".
OUT="$(warm bare-slug-not-a-path epsilon business 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "a REAL malformed arm is still refused (exit 3)" || bad "malformed arm allowed" "exit=$RC $OUT"
case "$OUT" in *MALFORMED*) ok "and is still named as malformed";; *) bad "lost the malformed note" "$OUT";; esac
case "$(warm 'X:no-separator' epsilon business 2>&1)" in *MALFORMED*) ok "a drive letter with NO separator is malformed too";; *) bad "X:no-separator accepted as absolute" "";; esac

# (c) the persistence hook must not join an absolute windows path onto the arming cwd
WOUT="$(wturn "an ordinary sentence that authorises nothing")"
case "$WOUT" in *"doc at $WIN"*) ok "⭐ the injected line names the brief at its real path";; *) bad "doc_path was mangled by the hook" "$WOUT";; esac
# ⛔ MATCH "/X:", NOT "$SB/G:". The hook resolves against $PWD (or the cwd in the event JSON), which
# is the REAL working directory, not this sandbox — so an $SB-prefixed check passes without testing
# anything. A "/" immediately before a drive letter can only be a join; that is the actual defect.
case "$WOUT" in *"/X:"*) bad "the windows path was JOINED onto the arming cwd" "$WOUT";; *) ok "and was NOT joined onto a cwd";; esac

# the POSIX spelling of the same thing must be untouched by all of this
OUT="$(env HOME="$SB" CLAUDE_CODE_SESSION_ID=posix-test bash "$PMF" arm "$A" alpha root 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "a POSIX absolute path still arms exactly as before" || bad "posix arm broke" "exit=$RC $OUT"
[ "$(grep '^lock_slug=' "$STORE/lock-sess-posix-test.project" 2>/dev/null | cut -d= -f2-)" = alpha ] \
  && ok "and still locks exactly as before" || bad "posix lock broke" ""

echo "── 15. the freshness word is a REAL mtime, not a mount point (2026-08-28) ─"
# `stat -f %m` is BSD-ONLY, and on GNU it does NOT fail — `-f` is --file-system and `%m` is the MOUNT
# POINT, so it returned a 355-char filesystem blob on stdout with EXIT 0. `[ -n "$MT" ]` was therefore
# true, and `D=$(( NOW - MT ))` died on an arithmetic SYNTAX error — which, inside that `if` block, is
# fatal to the whole command list: it aborts before ANY branch runs, so WHEN kept its initial
# "unknown". MEASURED 2026-08-28. The freshness word therefore never worked at all off macOS, for any
# file of any age. ⛔ AN EXIT-CODE FALLBACK ALONE CANNOT CATCH THIS, and that is the lesson worth
# keeping: the old call SUCCEEDED and answered a different question. The integer check is what closes
# it, so anything non-numeric degrades to "unknown" rather than to a confident wrong number.
# ⭐ PORTABLE: this drives the POSIX sandbox brief, so it runs everywhere. On macOS it passed BEFORE
# the fix too — BSD stat is exactly what the old form wanted — and it is Linux and Git Bash that were
# broken. That asymmetry is why the bug survived: the platform the author develops on was the one
# platform where the line was telling the truth.
FSESS=fresh-test
farm(){  env HOME="$SB" CLAUDE_CODE_SESSION_ID="$FSESS" bash "$PMF" arm "$@"; }
fturn(){ printf '{"cwd":"%s","prompt":%s}' "$SB" "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1")" \
         | env HOME="$SB" CLAUDE_CODE_SESSION_ID="$FSESS" bash "$PMP" 2>&1; }

farm "$A" alpha root >/dev/null 2>&1
FOUT="$(fturn "an ordinary sentence that authorises nothing")"
case "$FOUT" in *"last written unknown"*) bad "the mtime could not be read at all" "$FOUT";; *) ok "a readable brief never degrades to 'unknown'";; esac
case "$FOUT" in *"last written just now"*) ok "a file written seconds ago reads 'just now'";; *) bad "fresh file misread" "$FOUT";; esac

# ⭐ BOTH ASSERTIONS ABOVE ALREADY FAIL PRE-FIX (everything read "unknown"), so this one is not what
# catches the ORIGINAL bug — it is what catches the one the original was mistaken for. A `stat` that
# returns something numeric-but-wrong, or a future refactor that lets D default to 0, would sail past
# "fresh file says fresh" and be caught only here. Kept deliberately: the first diagnosis of this bug
# WAS "D collapses to 0, everything reads just now", and it took running it to find that is not what
# happens. This asserts against the plausible-but-wrong story as well as the real one.
# python3 sets the mtime because it is already a dependency of this suite and is the one portable
# spelling: `touch -d '3 days ago'` is GNU-only and `touch -t` needs BSD `date -v`, so either choice
# would re-create the platform split this whole section exists to close.
OLDB="$SB/old-brief.md"
printf '# Old\n## CURRENT STATE\nstale\n' > "$OLDB"
python3 -c "import os,sys,time; os.utime(sys.argv[1], (time.time()-3*86400,)*2)" "$OLDB" 2>/dev/null
farm "$OLDB" alpha root >/dev/null 2>&1
OOUT="$(fturn "another ordinary sentence")"
case "$OOUT" in *"last written 3d ago"*) ok "⭐ a 3-day-old brief reads '3d ago', NOT 'just now'";; *) bad "an old brief was reported as fresh — a numeric-but-WRONG mtime is reaching the arithmetic" "$OOUT";; esac
case "$OOUT" in *"last written just now"*) bad "⛔ every file reads 'just now' — the mtime is not being read at all" "$OOUT";; *) ok "and 'just now' is no longer the universal answer";; esac

echo
echo "═════════  PASS=$PASS  FAIL=$FAIL  ═════════"
rm -rf "$SB"
[ "$FAIL" = 0 ]
