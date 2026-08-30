#!/usr/bin/env bash
# gws-audit.sh — one-command health read of the whole gws credential plane.
#
# WHY: gws auto-deletes its own credentials.enc when it runs while the macOS login keychain can't be
# unlocked, killing Google auth for every window (root-caused 2026-06-01, recurred 2026-07-26/27 —
# records/log/2026-07-27-gws-auth-loss-desk-launcher-gap.md). The isolation fix is spread across
# launchers, settings.json, and the cron library; this proves ALL of it at once instead of one piece.
#
# RUN IT: bash system/tools/gws-audit.sh          (read-only — changes nothing, ever)
#
# DESIGN NOTE: every auth check here makes a REAL API call. `gws auth status` reporting healthy is
# exactly what produced a false "OK" on 2026-07-26 while three calendar writes silently failed.

set -uo pipefail
CLONE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
LAUNCHERS="$CLONE/system/desktop-launchers"
SETTINGS="$CLONE/system/reference/settings.json"
ISO_VARS=(GOOGLE_WORKSPACE_CLI_CONFIG_DIR GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND)
# Isolated creds store moved ~/.config/claudeops -> ~/.config/lifehack (this repo's established
# machine-local config home, per gws-auth.lib.sh's gws_creds_path()); the writer (gws-reauth.sh)
# and every live reader now agree on the new path, so the audit checks the same one.
GCREDS="${LIFEHACK_GWS_CREDS_FILE:-$HOME/.config/lifehack/gws-credentials.json}"
PASS=0; FAIL=0; WARN=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; WARN=$((WARN+1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$*"; }

head_ "1. LIVE AUTH — real API calls, not auth status"
if gws calendar calendarList list --params '{"maxResults":1}' >/dev/null 2>&1; then
  ok "current session can reach Google"; else bad "current session CANNOT reach Google — run: bash system/tools/gws-reauth.sh"; fi
if env GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/gws-cron" \
       GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE="$GCREDS" \
       GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND=file \
       gws calendar calendarList list --params '{"maxResults":1}' >/dev/null 2>&1; then
  ok "ISOLATED path works (what desks + cron use)"; else bad "ISOLATED path BROKEN — desks and cron cannot reach Google"; fi
if env -u GOOGLE_WORKSPACE_CLI_CONFIG_DIR -u GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE -u GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND \
       gws calendar calendarList list --params '{"maxResults":1}' >/dev/null 2>&1; then
  ok "INTERACTIVE (keychain) path works"; else warn "interactive keychain path not working — only matters for a fresh re-auth"; fi

head_ "2. CREDENTIAL FRESHNESS"
if [ -f "$GCREDS" ]; then
  AGE=$(( ( $(date +%s) - $(stat -c %Y "$GCREDS" 2>/dev/null || stat -f %m "$GCREDS" 2>/dev/null) ) / 86400 ))
  MODE=$(stat -c %a "$GCREDS" 2>/dev/null || stat -f %Lp "$GCREDS" 2>/dev/null)
  [ "$MODE" = "600" ] && ok "isolated creds mode 600" || bad "isolated creds mode $MODE — should be 600"
  if   [ "$AGE" -gt 60 ]; then bad  "isolated creds ${AGE}d old — ROTATE (bash system/tools/gws-reauth.sh)"
  elif [ "$AGE" -gt 30 ]; then warn "isolated creds ${AGE}d old — rotate soon"
  else ok "isolated creds ${AGE}d old"; fi
  grep -q '"cloud-platform"' "$GCREDS" 2>/dev/null && warn "creds carry cloud-platform scope (GCP project control) — narrow on next re-auth"
else bad "isolated creds MISSING at $GCREDS — cron and desks will fail"; fi

head_ "3. THE 7 DESK LAUNCHERS"
# COUNCIL-CAUGHT DEFECT (2026-07-27): the first version of this loop had an unconditional `break` —
# it tested ONLY ISO_VARS[0] and reported "all 3" green. A fixture launcher carrying just var 1
# passed. Rule = 3 vars; assertion = 1 var. Now: every var is tested, and the match requires a real
# `export VAR=` line — a comment or mere mention of the var name cannot satisfy it.
MISS=""
for f in "$LAUNCHERS"/*.command; do
  grep -qE '^claude |"\$CLAUDE"' "$f" 2>/dev/null || continue          # session launchers only
  for v in "${ISO_VARS[@]}"; do
    grep -qE "^[[:space:]]*export[[:space:]]+$v=" "$f" || MISS="$MISS $(basename "$f"):$v"
  done
done
[ -z "$MISS" ] && ok "every session launcher exports all 3 isolation vars (real export lines)" \
               || bad "launchers MISSING isolation exports:$MISS"
PF=$(grep -l "gws PRE-FLIGHT" "$LAUNCHERS"/*.command 2>/dev/null | wc -l | tr -d ' ')
[ "$PF" -ge 7 ] && ok "$PF launchers carry the loud pre-flight" || warn "only $PF launchers have the pre-flight"

head_ "4. SESSION-WIDE ENV (settings.json)"
if python3 -c "import json,sys; d=json.load(open('$SETTINGS')); sys.exit(0 if all(k in d.get('env',{}) for k in ['${ISO_VARS[0]}','${ISO_VARS[1]}','${ISO_VARS[2]}']) else 1)" 2>/dev/null; then
  ok "settings.json env block carries all 3 vars"; else bad "settings.json env block is MISSING isolation vars"; fi
# settings.json was DELIBERATELY converted from a symlink into a real file: writing through the
# symlink wrote the git-TRACKED repo copy, which publishes to a public upstream. A real file is now
# the healthy state; a symlink is the defect (it would mean an edit here leaks to the public repo).
if [ -L "$HOME/.claude/settings.json" ]; then
  bad "~/.claude/settings.json IS a symlink — edits here would write through to the tracked repo copy (public upstream risk)"
elif [ -f "$HOME/.claude/settings.json" ]; then
  ok "~/.claude/settings.json is a real file (not a symlink into the tracked repo)"
else
  bad "~/.claude/settings.json is MISSING"
fi

head_ "5. RE-AUTH SCRIPT IMMUNITY"
R="$CLONE/system/tools/gws-reauth.sh"
if [ -f "$R" ]; then
  bash -n "$R" 2>/dev/null && ok "gws-reauth.sh parses clean" || bad "gws-reauth.sh has a SYNTAX ERROR"
  grep -q 'NOISO=' "$R" && ok "gws-reauth.sh strips ambient isolation vars (no false VERIFIED)" \
                        || bad "gws-reauth.sh is NOT ambient-immune — it would rotate the wrong store and lie"
  # Match an actual INVOCATION, not the string anywhere — the first version of this check flagged the
  # explanatory COMMENT about DUMMY=1 and produced a confident wrong RED on its very first run.
  # A checker that greps a bare token will eventually grade a comment. (Caught 2026-07-27.)
  grep -qE '^[[:space:]]*verify[[:space:]].*DUMMY=1' "$R" && bad "gws-reauth.sh still CALLS the DUMMY=1 fake verify" \
                                                          || ok "no live DUMMY=1 fake-verify call"
else bad "gws-reauth.sh MISSING — no sanctioned re-auth path"; fi

head_ "6. UNISOLATED gws CALLERS (heuristic — see note)"
U=""
for f in "$CLONE"/system/tools/*.sh "$CLONE"/shared/tools/*.py "$CLONE"/system/tools/*.py; do
  [ -f "$f" ] || continue
  grep -q "gws " "$f" 2>/dev/null || continue
  grep -qE "ingest_load_gws|ingest_load_auth|GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND" "$f" 2>/dev/null || U="$U\n      $(basename "$f")"
done
if [ -z "$U" ]; then ok "no tool script calls gws without isolation"
else warn "scripts naming gws without their own isolation (many are CHILDREN of isolated runners and inherit it — verify before acting):$(printf "$U")"; fi

head_ "7. POSTURE CHECK"
# ⛔ The exit code MUST be captured before the pipe. Piping straight into grep|sed threw it
# away entirely, so a posture-scan CONFIG ERROR (its sys.exit(3)) read as a clean check and
# never reached the PASS/WARN/FAIL tally below. Capture first, display second.
_posture_out="$(bash "$CLONE/system/tools/security-posture-scan.sh" 2>/dev/null)"; _posture_rc=$?
printf '%s\n' "$_posture_out" | grep -i "gws-cred-isolation" | sed 's/^/  /'
[ "$_posture_rc" -ne 0 ] && warn "security-posture-scan.sh exited $_posture_rc — its verdict was NOT a clean pass"

printf '\n\033[1m=== %s pass · %s warn · %s FAIL ===\033[0m\n' "$PASS" "$WARN" "$FAIL"
[ "$FAIL" -gt 0 ] && { echo "  RED — fix the ✗ items above."; exit 1; }
[ "$WARN" -gt 0 ] && { echo "  AMBER — working, with the notes above."; exit 0; }
echo "  GREEN."; exit 0
