#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the PLAN half of the owner's ruling, watched rather than asserted. Its project half is
#      covered by test_pm_lock_override.sh; the ruling was always "this other project OR this
#      other plan", and only the project half had been built.
#      (1) firing a plan LOCKS the window — arming a DIFFERENT plan is REFUSED;
#      (2) exactly two things change it: a new window, or THE HUMAN'S OWN WORDS in their own
#      prompt, which buys ONE change and is then burned;
#      (3) ⭐ the grant is the SAME ONE pm_flag.sh consumes — this suite proves plan_flag.sh mints
#      no grant of its own, because a second grant type is a second thing to forge.
# GUARDS: sandbox only. HOME is redirected under /tmp; nothing here touches the live store.
# REDIRECT: subject is system/hooks/plan_flag.sh; the grant issuer is system/hooks/pm_persist.sh.
# SIGNPOST: the rule, the incident and the grant's design live in system/hooks/pm_flag.sh's header.
# FAIL_POSTURE: N/A (a test). Non-zero exit = at least one case failed.
# UPDATED: 2026-08-15 (new — built alongside the plan lock itself)
# ─────────────────────────────────────────────────────────────────────────────
#   bash system/hooks/tests/test_plan_lock_override.sh
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
PLF="$HOOKS/plan_flag.sh"
PMP="$HOOKS/pm_persist.sh"
SB=/tmp/plan-lock-test.$$
PSTORE="$SB/.claude/run/plan"
MSTORE="$SB/.claude/run/pm"
mkdir -p "$PSTORE" "$MSTORE"
A="$SB/alpha.plan.md"; B="$SB/beta.plan.md"; C="$SB/gamma.plan.md"
printf '# Alpha Plan\n## Phase 1\n' > "$A"
printf '# Beta Plan\n## Phase 1\n'  > "$B"
printf '# Gamma Plan\n## Phase 1\n' > "$C"
SESS=plan-lock-test
KEY="sess-$SESS"
GRANTF="$MSTORE/override-$KEY.grant"
PASS=0; FAIL=0
ok(){  PASS=$((PASS+1)); printf '  ✅ %s\n' "$1"; }
bad(){ FAIL=$((FAIL+1)); printf '  ❌ %s\n     got: %s\n' "$1" "$2"; }

# ONE ExitPlanMode event. $1 = the plan file the harness hands us.
rec(){ printf '{"tool_input":{"planFilePath":"%s"}}' "$1" \
       | env HOME="$SB" CLAUDE_CODE_SESSION_ID="$SESS" bash "$PLF" record; }
# the same, with the payload the caller wants (for the fail-open case)
recraw(){ printf '%s' "$1" | env HOME="$SB" CLAUDE_CODE_SESSION_ID="$SESS" bash "$PLF" record; }
plf(){ env HOME="$SB" CLAUDE_CODE_SESSION_ID="$SESS" bash "$PLF" "$@"; }
# one human turn. $1 = what the person typed.
turn(){ printf '{"cwd":"%s","prompt":%s}' "$SB" "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1")" \
        | env HOME="$SB" CLAUDE_CODE_SESSION_ID="$SESS" bash "$PMP" 2>&1; }
lockname(){ grep '^lock_name=' "$PSTORE/lock-$KEY.plan" 2>/dev/null | cut -d= -f2-; }
flagname(){ grep '^name=' "$PSTORE/plan-$KEY.flag" 2>/dev/null | cut -d= -f2-; }

echo "── 1. the lock ───────────────────────────────────────────────────────────"
OUT="$(rec "$A" 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "first plan fires (exit 0)" || bad "first record exit" "exit=$RC $OUT"
[ "$(flagname)" = "Alpha Plan" ] && ok "flag armed to Alpha Plan" || bad "flag" "$(flagname)"
[ "$(lockname)" = "Alpha Plan" ] && ok "lock file written, lock_name=Alpha Plan" || bad "lock file" "$(lockname)"
grep -q '^origin=first-arm' "$PSTORE/lock-$KEY.plan" && ok "lock records origin=first-arm" || bad "origin" ""
[ "$(plf locked)" = "Alpha Plan" ] && ok "the read-only 'locked' verb reports it" || bad "locked verb" "$(plf locked)"

# THE ORDINARY CASE MUST NOT BREAK: plan mode re-fires on every amendment and /checkin re-arms on
# every run. A same-plan arm is never a change and must never be refused or announced.
OUT="$(rec "$A" 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "re-firing the SAME plan refreshes normally (exit 0)" || bad "same-plan refused" "exit=$RC $OUT"
case "$OUT" in *OVERRIDDEN*|*REFUSED*) bad "a same-plan re-arm was treated as a change" "$OUT";; *) ok "and is neither refused nor announced";; esac
OUT="$(plf set "$A" 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "'set' to the same plan also refreshes (exit 0)" || bad "set same-plan refused" "exit=$RC $OUT"

echo "── 2. a DIFFERENT plan is refused ───────────────────────────────────────"
OUT="$(rec "$B" 2>&1)"; RC=$?
[ "$RC" = 2 ] && ok "record of a DIFFERENT plan REFUSED (exit 2 = harness block)" || bad "record refuse exit" "exit=$RC"
case "$OUT" in *"REFUSED"*"IMMUTABLE"*) ok "refusal names what it blocked";; *) bad "refusal text" "$OUT";; esac
case "$OUT" in *"Alpha Plan"*"Beta Plan"*) ok "refusal names BOTH the armed and the requested plan";; *) bad "names missing" "$OUT";; esac
case "$OUT" in *"NEW WINDOW"*) ok "refusal teaches path 1 (new window)";; *) bad "path 1 missing" "$OUT";; esac
case "$OUT" in *"HUMAN'S OWN WORDS"*) ok "refusal teaches path 2 (the human's words)";; *) bad "path 2 missing" "$OUT";; esac
[ "$(flagname)" = "Alpha Plan" ] && ok "nothing was written — flag still Alpha Plan" || bad "flag moved!" "$(flagname)"
[ "$(lockname)" = "Alpha Plan" ] && ok "lock did not move" || bad "lock moved!" "$(lockname)"
[ -s "$PSTORE/plan-denied.log" ] && ok "refusal recorded in plan-denied.log" || bad "no deny log" ""
OUT="$(plf set "$B" 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "'set' to a different plan REFUSED (exit 3 = the CLI REFUSED code)" || bad "set refuse exit" "exit=$RC"

echo "── 3. the refusal's CHANNEL (a guard nobody can see is not a guard) ──────"
E_ONLY="$(rec "$B" 2>&1 >/dev/null)"
O_ONLY="$(rec "$B" 2>/dev/null)"
case "$E_ONLY" in *REFUSED*) ok "refusal survives 2>&1 >/dev/null (stderr alone)";; *) bad "stderr channel" "$E_ONLY";; esac
case "$O_ONLY" in *REFUSED*) ok "refusal survives 2>/dev/null (stdout alone)";; *) bad "stdout channel" "$O_ONLY";; esac

echo "── 4. the model cannot mint the override ────────────────────────────────"
turn "I think we should really be on the beta plan now, let me re-point it" >/dev/null
[ -f "$GRANTF" ] && bad "a vague prompt issued a grant" "$(cat "$GRANTF")" || ok "a vague prompt issues NO grant"
OUT="$(rec "$B" 2>&1)"; RC=$?
[ "$RC" = 2 ] && ok "still refused with no grant (exit 2)" || bad "unexpected allow" "exit=$RC $OUT"
# ⭐ ONE GRANT TYPE, NOT TWO. plan_flag.sh must consume the pm store's grant and mint nothing itself.
ls "$PSTORE"/*.grant >/dev/null 2>&1 && bad "plan_flag minted a grant of its own" "$(ls "$PSTORE")" \
  || ok "plan_flag.sh mints NO grant of its own — no parallel grant type exists"

echo "── 5. the human's own words → ONE change ────────────────────────────────"
OUT="$(turn "actually switch the plan to beta, alpha is done")"
[ -f "$GRANTF" ] && ok "explicit human prompt issues the grant (in the PM store)" || bad "no grant issued" "$OUT"
case "$OUT" in *"OVERRIDE AUTHORISED"*) ok "the turn it happens is LOUD in the injected context";; *) bad "silent grant" "$OUT";; esac
G="$(grep '^session=' "$GRANTF" | cut -d= -f2-)"
[ "$G" = "$SESS" ] && ok "grant is bound to the session that spoke" || bad "grant session" "$G"
OUT="$(rec "$B" 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "the override ALLOWS the change (exit 0)" || bad "override did not allow" "exit=$RC $OUT"
case "$OUT" in *"PLAN LOCK OVERRIDDEN"*"Alpha Plan"*"Beta Plan"*) ok "the allow is LOUD and names both plans";; *) bad "quiet allow" "$OUT";; esac
[ "$(flagname)" = "Beta Plan" ] && ok "flag moved to Beta Plan" || bad "flag" "$(flagname)"
[ "$(lockname)" = "Beta Plan" ] && ok "lock rewritten to Beta Plan" || bad "lock" "$(lockname)"
grep -q '^origin=human-override' "$PSTORE/lock-$KEY.plan" && ok "lock records origin=human-override" || bad "no origin" ""
grep -q '^previous_plan=Alpha Plan' "$PSTORE/lock-$KEY.plan" && ok "lock records the plan it moved OFF" || bad "no previous_plan" ""
grep -q 'OVERRIDDEN-by-human' "$PSTORE/plan-denied.log" && ok "the override is in the audit log too" || bad "no audit line" ""
[ -f "$GRANTF" ] && bad "grant NOT burned" "still present" || ok "grant burned on use"

# The ALLOW's channel, on a fresh authorisation each time — an override announced only on stderr is
# invisible to `... 2>/dev/null`, the same PASS-and-protect-nothing failure as a misrouted refusal.
turn "switch the plan to alpha" >/dev/null
A_OUT="$(rec "$A" 2>/dev/null)"
case "$A_OUT" in *"PLAN LOCK OVERRIDDEN"*) ok "the override banner survives on stdout alone";; *) bad "announce stdout" "$A_OUT";; esac
turn "switch the plan to beta" >/dev/null
A_ERR="$(rec "$B" 2>&1 >/dev/null)"
case "$A_ERR" in *"PLAN LOCK OVERRIDDEN"*) ok "the override banner survives on stderr alone";; *) bad "announce stderr" "$A_ERR";; esac

echo "── 6. once means once ───────────────────────────────────────────────────"
OUT="$(rec "$C" 2>&1)"; RC=$?
[ "$RC" = 2 ] && ok "a second change on the same authorisation is REFUSED" || bad "second change allowed!" "exit=$RC"
[ "$(lockname)" = "Beta Plan" ] && ok "and the lock did not move" || bad "lock moved" "$(lockname)"
turn "ok switch the plan to gamma" >/dev/null; [ -f "$GRANTF" ] && ok "re-authorising issues a fresh grant" || bad "no re-grant" ""
turn "never mind, what is the weather" >/dev/null
[ -f "$GRANTF" ] && bad "grant survived the next turn" "still present" || ok "an unspent grant dies on their next message"

echo "── 7. a foreign session cannot spend someone else's word ────────────────"
printf 'granted_at=%s\nsession=%s\nphrase=override the plan lock\n' "$(date +%s)" other-window > "$GRANTF"
OUT="$(rec "$C" 2>&1)"; RC=$?
[ "$RC" = 2 ] && ok "grant from another session is not consumable (exit 2)" || bad "cross-session spend!" "exit=$RC"

echo "── 8. a stale grant is not consumable ───────────────────────────────────"
printf 'granted_at=%s\nsession=%s\nphrase=override the plan lock\n' "$(( $(date +%s) - 7200 ))" "$SESS" > "$GRANTF"
OUT="$(rec "$C" 2>&1)"; RC=$?
[ "$RC" = 2 ] && ok "a 2h-old grant is expired (exit 2)" || bad "stale grant spent!" "exit=$RC"
printf 'granted_at=%s\nsession=%s\nphrase=override the plan lock\n' "not-a-number" "$SESS" > "$GRANTF"
OUT="$(rec "$C" 2>&1)"; RC=$?
[ "$RC" = 2 ] && ok "a malformed grant is not consumable (exit 2)" || bad "malformed grant spent!" "exit=$RC"

echo "── 9. clear frees the FLAG, never the LOCK ──────────────────────────────"
OUT="$(plf clear 2>&1)"; RC=$?
[ "$RC" = 3 ] && ok "clear REFUSED while locked (exit 3)" || bad "clear allowed" "exit=$RC $OUT"
[ -f "$PSTORE/plan-$KEY.flag" ] && ok "flag untouched by the refused clear" || bad "flag deleted" ""
turn "override the plan lock" >/dev/null
OUT="$(plf clear 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "clear ALLOWED by the human's word (exit 0)" || bad "granted clear failed" "exit=$RC $OUT"
[ -f "$PSTORE/plan-$KEY.flag" ] && bad "flag not cleared" "" || ok "flag deleted"
[ -f "$PSTORE/lock-$KEY.plan" ] && ok "⭐ THE LOCK SURVIVED THE CLEAR" || bad "LOCK DELETED BY CLEAR" "the bypass is open"
OUT="$(rec "$A" 2>&1)"; RC=$?
[ "$RC" = 2 ] && ok "clear+arm-elsewhere is NOT a bypass — still refused" || bad "BYPASS: clear then re-arm" "exit=$RC"

echo "── 10. the declared fail-open, and the un-lockable key ──────────────────"
OUT="$(recraw 'not json at all' 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "an unreadable payload refuses nothing (exit 0)" || bad "refused on no evidence" "exit=$RC $OUT"
case "$OUT" in *REFUSED*) bad "refused a plan it never identified" "$OUT";; *) ok "and says nothing — we never learned which plan it was";; esac
# No session id -> the cwd-hash key, shared by every window in one folder. A lock there would refuse
# a legitimate second window, so it is deliberately NOT lockable. Same call pm_flag.sh made.
CW="$SB/cwd-case"; mkdir -p "$CW"
o1="$(cd "$CW" && printf '{"tool_input":{"planFilePath":"%s"}}' "$A" | env HOME="$SB" CLAUDE_CODE_SESSION_ID= bash "$PLF" record 2>&1)"
o2="$(cd "$CW" && printf '{"tool_input":{"planFilePath":"%s"}}' "$B" | env HOME="$SB" CLAUDE_CODE_SESSION_ID= bash "$PLF" record 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "the cwd-hash key is NOT lockable (a second window is not refused)" || bad "cwd key locked" "exit=$RC $o2"

echo "── 11. the grant TTL is not a second copy of that number ────────────────"
# A copy of plan_flag.sh run beside a pm_flag.sh whose OVERRIDE_TTL_MIN is 1 must expire a 5-minute
# grant that the real 30-minute default would have accepted. If plan_flag.sh carried its own literal
# this would pass a grant it should refuse — the exact shape of the 12h/36h split that sat dead in
# pm_flag.sh and pm_persist.sh for a month.
FAKE="$SB/fake"; mkdir -p "$FAKE"
sed 's/PM_OVERRIDE_TTL_MIN:-30/PM_OVERRIDE_TTL_MIN:-1/' "$HOOKS/pm_flag.sh" > "$FAKE/pm_flag.sh"
cp "$PLF" "$FAKE/plan_flag.sh"
printf 'granted_at=%s\nsession=%s\nphrase=switch the plan to gamma\n' "$(( $(date +%s) - 300 ))" "$SESS" > "$GRANTF"
printf '{"tool_input":{"planFilePath":"%s"}}' "$C" | env HOME="$SB" CLAUDE_CODE_SESSION_ID="$SESS" bash "$FAKE/plan_flag.sh" record >/dev/null 2>&1
RC=$?
[ "$RC" = 2 ] && ok "plan_flag reads the grant TTL from pm_flag.sh (5m grant died under a TTL-1 copy)" \
  || bad "plan_flag ignored pm_flag.sh's OVERRIDE_TTL_MIN — the number is NOT single-source" "exit=$RC"
# and the real one still accepts a 5-minute-old grant at the real 30-minute default
printf 'granted_at=%s\nsession=%s\nphrase=switch the plan to gamma\n' "$(( $(date +%s) - 300 ))" "$SESS" > "$GRANTF"
OUT="$(rec "$C" 2>&1)"; RC=$?
[ "$RC" = 0 ] && ok "and the real default still accepts a 5m-old grant (exit 0)" || bad "real default rejected it" "exit=$RC $OUT"

echo
echo "═════════  PASS=$PASS  FAIL=$FAIL  ═════════"
rm -rf "$SB"
[ "$FAIL" = 0 ]
