#!/usr/bin/env bash
# Status line — reads the harness's JSON on stdin, prints the bar at the bottom of your window.
#
# ⚠ IT MUST STAY EXECUTABLE (+x / 755). The harness runs it as a bare command, so a `chmod 644`
#   anywhere in an edit strips the bit, the harness gets permission-denied, and the bar renders
#   BLANK on every session with no error anywhere (a real incident, 2026-07-14). If your status bar
#   goes empty, check the mode first: `ls -l system/statusline.sh`, then `chmod +x` it.
#
# Nothing here is required for the system to work -- it is a display. It degrades field by field:
# a marker file that does not exist simply does not render.

# ── hash_key: the fallback session key, and it MUST match everywhere ──────────────────────────────
# When the harness gives us no session id we key on the working directory instead. `shasum` does that
# on macOS and Linux and is ABSENT from Git Bash on Windows, where it produces an EMPTY key — so every
# window on that machine would collide on one flag, silently.
# ⚠ SHA-1 DELIBERATELY, NOT SHA-256: this must equal what `shasum` prints, or a machine that has
# shasum and a machine that does not would key the SAME folder differently. One writer and one reader
# disagreeing about the key is worse than having no key at all.
# ⚠ This snippet is IDENTICAL in every file that needs it (plan_flag, pm_flag, pm_persist, skill_anchor,
# skill_anchor_inject, statusline). Keep it that way — the next platform fix should land in one shape.
# ⚠ DEFINE IT AT THE TOP, never beside its first use: these files branch on whether the harness gave
# us a session id, and a definition placed inside that branch is not defined on the other one.
# TEMPORARY: Git Bash is the documented Windows floor; a real Windows story is still owed.
hash_key() {
  _hk="$(printf '%s' "$1" | shasum 2>/dev/null | cut -c1-12)"
  if [ -z "$_hk" ]; then
    _hk="$(printf '%s' "$1" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-12)"
  fi
  printf '%s' "$_hk"
}

INPUT=$(cat)

MODEL=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); m=d.get('model',{}); print(m.get('display_name','') or m.get('name','') if isinstance(m,dict) else m)" 2>/dev/null)
CTX_PCT=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(int(d.get('context_window',{}).get('used_percentage',0)))" 2>/dev/null)
COST=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('{:.2f}'.format(d.get('cost',{}).get('total_cost_usd',0) or d.get('session_cost_usd',0)))" 2>/dev/null)
PROJECT_DIR=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('workspace',{}).get('project_dir','') or d.get('cwd',''))" 2>/dev/null)

# Desk detection from project dir
DESK="root"
if echo "$PROJECT_DIR" | grep -q "/desks/"; then
  DESK=$(echo "$PROJECT_DIR" | sed 's|.*/desks/\([^/]*\).*|\1|')
fi

# Shorten model name
MODEL_SHORT=$(echo "$MODEL" | sed 's/claude-//' | sed 's/-20[0-9]*//')

# Context bar
BAR_LEN=10
FILLED=$(( CTX_PCT * BAR_LEN / 100 ))
EMPTY=$(( BAR_LEN - FILLED ))
BAR=""
for i in $(seq 1 $FILLED); do BAR="${BAR}█"; done
for i in $(seq 1 $EMPTY); do BAR="${BAR}░"; done

# Color thresholds
if [ "${CTX_PCT:-0}" -ge 80 ]; then
  COLOR="\033[31m"   # red
elif [ "${CTX_PCT:-0}" -ge 60 ]; then
  COLOR="\033[33m"   # yellow
else
  COLOR="\033[32m"   # green
fi
RESET="\033[0m"

# --- custom skill HUD (optional, session-scoped) ---
# A running skill can draw its own line ABOVE this bar via system/tools/skill_hud.sh (set/clear).
# Keyed by session_id so parallel windows don't collide; a 6h freshness guard drops a stale HUD
# a crashed skill left behind.
SID=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null)
HUD_FILE="$HOME/.claude/hud/${SID}.txt"
if [ -n "$SID" ] && [ -f "$HUD_FILE" ] && [ -n "$(find "$HUD_FILE" -mmin -360 2>/dev/null)" ]; then
  printf "\033[36m%s${RESET}\n" "$(cat "$HUD_FILE" 2>/dev/null)"
fi

# --- locked core HUD: project · plan · scratch (session-scoped markers) ---
# Reads small per-session flag files written by their producers (pm_flag.sh / plan_flag.sh /
# scratch_flag.sh). proj/plan are COLORED BY FRESHNESS (green <24h · yellow <7d · red older);
# scratch is on/off. plan shows the plan FILENAME (a stable, searchable handle), not the title.
RUN="$HOME/.claude/run"
if [ -n "$SID" ]; then
  PM_FLAG="$RUN/pm/pm-sess-$SID.flag"
  PLAN_FLAG="$RUN/plan/plan-sess-$SID.flag"
  SCRATCH_FLAG="$RUN/scratch/scratch-sess-$SID.flag"
else
  H=$(hash_key "$PWD")
  PM_FLAG="$RUN/pm/pm-cwd-$H.flag"
  PLAN_FLAG="$RUN/plan/plan-cwd-$H.flag"
  SCRATCH_FLAG="$RUN/scratch/scratch-cwd-$H.flag"
fi
NOW=$(date +%s 2>/dev/null)
fresh_field() {  # $1=flagfile $2=key $3=max-age-min ; echoes value only when the flag is fresh
  [ -f "$1" ] && [ -n "$(find "$1" -mmin "-$3" 2>/dev/null)" ] && grep "^$2=" "$1" 2>/dev/null | cut -d= -f2-
}
flag_field() {   # $1=flagfile $2=key ; echoes value regardless of age (empty if missing)
  [ -f "$1" ] && grep "^$2=" "$1" 2>/dev/null | cut -d= -f2-
}
age_color() {    # $1=flagfile ; emits a LITERAL ANSI color by armed_at age (printf %b renders it later)
  _at=$(flag_field "$1" armed_at)
  if [ -z "$_at" ] || [ -z "$NOW" ]; then return; fi
  _age=$(( NOW - _at ))
  if   [ "$_age" -lt 86400 ];  then printf '%s' '\033[32m'   # <24h  green (fresh)
  elif [ "$_age" -lt 604800 ]; then printf '%s' '\033[33m'   # <7d   yellow (aging)
  else                              printf '%s' '\033[31m'   # older red (stale — re-check)
  fi
}

# bottom-bar project slug — UNCHANGED behaviour (36h fresh); consumed only by the bottom bar below
SLUG=$(fresh_field "$PM_FLAG" slug 2160)

# HUD fields — generous 14-day window so freshness-color can age green→yellow→red before hiding
H_PROJ=$(fresh_field "$PM_FLAG" slug 20160)
H_PLAN=$(basename "$(fresh_field "$PLAN_FLAG" plan_file 20160)" .md 2>/dev/null); [ "$H_PLAN" = "." ] && H_PLAN=""
# KISS width fix: cap each field so the line can never run off the screen
[ "${#H_PROJ}" -gt 24 ] && H_PROJ="${H_PROJ:0:23}…"
[ "${#H_PLAN}" -gt 24 ] && H_PLAN="${H_PLAN:0:23}…"
# scratch — ephemeral on/off (30-min freshness); age isn't meaningful, so always green when on
SCRATCH_ON=""
[ -f "$SCRATCH_FLAG" ] && [ -n "$(find "$SCRATCH_FLAG" -mmin -30 2>/dev/null)" ] && SCRATCH_ON="on"

# assemble the HUD line — each field wrapped in its own freshness color; prints only when non-empty
if [ -n "${H_PROJ}${H_PLAN}${SCRATCH_ON}" ]; then
  L=""
  [ -n "$H_PROJ" ]     && L="$(age_color "$PM_FLAG")proj: ${H_PROJ}${RESET}"
  [ -n "$H_PLAN" ]     && L="${L:+$L · }$(age_color "$PLAN_FLAG")plan: ${H_PLAN}${RESET}"
  [ -n "$SCRATCH_ON" ] && L="${L:+$L · }\033[32mscratch: on${RESET}"
  printf '%b\n' "$L"
fi

# bottom bar — the "desk:" field ALWAYS shows the session's REAL desk, NEVER a project slug.
# TRUTH CONTRACT (load-bearing — the user steers by this across many windows): this field must
# equal the actual desk. Source, in priority: (1) the session PM flag's own desk= field
# (authoritative — written when the project was armed via pm_flag.sh), (2) cwd /desks/<name>/
# detection, (3) root. The armed PROJECT is shown on the "proj:" HUD line above and MUST NEVER
# appear here. History: a 2026-07-13 change set this to "${SLUG:-$DESK}", which made the field
# display the project slug — a broken truth contract, and hard to spot because it still looked
# plausible. Do NOT repoint this at $SLUG.
FLAG_DESK=$(flag_field "$PM_FLAG" desk)
WHERE="${FLAG_DESK:-$DESK}"
printf "${COLOR}[%s]  ctx %s %d%%  \$%s  desk: %s${RESET}" \
  "$MODEL_SHORT" "$BAR" "${CTX_PCT:-0}" "${COST:-0.00}" "$WHERE"
