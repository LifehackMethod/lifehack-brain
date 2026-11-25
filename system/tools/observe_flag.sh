#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: OBSERVE MODE (round 2, brief 2.1): a person uses a skill while a background reviewer reads each turn
#      against the skill's design. Something must remember, per window, WHICH skill is being watched, where its
#      SKILL.md is, where the person's notes for it go, and how far into the transcript the reviewer has read.
# GUARDS: none — a tiny state writer over the shared switch library system/hooks/lib/flag.sh. Session-scoped and
#      machine-local (CLAUDE_CODE_SESSION_ID; refuses to arm without it, because the Stop and prompt hooks find the
#      switch by the session id in their payload). TTL 8h (OBSERVE_TTL_HOURS).
# REDIRECT: flag ~/.claude/run/observe/observe-sess-<id>.flag. Writers: the observe prompt hook (arm/clear) and the
#      reviewer (set offset). Readers: end_of_turn_checks.sh (does the file exist), observe_review.sh, observe_ups.sh.
#      Off: `clear`, `/skill-builder-observe off`, or the TTL. Notes live in the PERSON'S notes folder, never the plugin.
# SIGNPOST: key derivation, TTL and sweep live in system/hooks/lib/flag.sh. Design: brief 2.1 (build-skill-v2 project).
# UPDATED: 2026-11-25 (new, 2.1)
# ─────────────────────────────────────────────────────────────────────────────
#   observe_flag.sh arm <skill>     # watch this skill in this window; prints OBSERVE ARMED: <skill>|<notes dir>
#   observe_flag.sh clear           # stop watching (this session)
#   observe_flag.sh status          # print what is watched, or "not observing"
#   observe_flag.sh get <field>     # skill | skill_file | notes_dir | offset | transcript | armed_at (TTL-checked)
#   observe_flag.sh set <field> <v> # change one field, keep the rest
set +e
_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUG="$(cd "$_SELF_DIR/../.." && pwd -P)"
_LIB="$_SELF_DIR/../hooks/lib/flag.sh"
[ -f "$_LIB" ] || { echo "observe_flag.sh: FATAL — shared library missing at $_LIB" >&2; exit 1; }
. "$_LIB" || { echo "observe_flag.sh: FATAL — shared library failed to load" >&2; exit 1; }
for _fn in flag_init flag_write flag_get flag_ttl_expired flag_clear_sweep; do
  command -v "$_fn" >/dev/null 2>&1 || { echo "observe_flag.sh: FATAL — library missing $_fn()" >&2; exit 1; }
done
TTL_HOURS="${OBSERVE_TTL_HOURS:-8}"
flag_init observe observe
FIELDS="skill skill_file notes_dir offset transcript armed_at cwd session"

_live() { [ -f "$FLAG" ] && ! flag_ttl_expired $(( TTL_HOURS * 3600 )); }

case "$1" in
  arm)
    sk="$2"
    case "$sk" in ''|*[!A-Za-z0-9._-]*) echo "OBSERVE NOT ARMED: give one skill name (letters, digits, . _ -), like: /skill-builder-observe skill-builder"; exit 1;; esac
    [ -n "$CLAUDE_CODE_SESSION_ID" ] || { echo "OBSERVE NOT ARMED: this window gave no session id, so the hooks could not find the switch"; exit 1; }
    sf=""
    PCR="$(python3 "$PLUG/shared/personal_code_root.py" --quiet 2>/dev/null | head -1)"
    for c in "$PLUG/.claude/skills/$sk/SKILL.md" "$PLUG/skills/$sk/SKILL.md" "$HOME/.claude/skills/$sk/SKILL.md" ${PCR:+"$PCR/skills/$sk/SKILL.md"}; do
      [ -f "$c" ] && { sf="$c"; break; }
    done
    [ -n "$sf" ] || { echo "OBSERVE NOT ARMED: no skill named '$sk' found (looked in the plugin's skills, ~/.claude/skills and your code folder)"; exit 1; }
    BRAIN="$(python3 "$PLUG/shared/brain_root.py" --quiet 2>/dev/null | head -1)"
    [ -n "$BRAIN" ] && [ -d "$BRAIN" ] || { echo "OBSERVE NOT ARMED: your notes folder is not set, so there is nowhere to keep the notes"; exit 1; }
    if [ "$sk" = "skill-builder" ]; then nd="$BRAIN/state/projects/v2/drafts/build-rebuild/16-skill-builder-packet"
    else nd="$BRAIN/drafts/builds/$sk"; fi
    mkdir -p "$nd" 2>/dev/null && [ -d "$nd" ] || { echo "OBSERVE NOT ARMED: could not create the notes folder $nd"; exit 1; }
    flag_write "skill=$sk" "skill_file=$sf" "notes_dir=$nd" "offset=" "transcript=" "armed_at=$NOW" "cwd=$PWD" "session=$CLAUDE_CODE_SESSION_ID"
    echo "OBSERVE ARMED: $sk|$nd";;
  clear)
    echo "OBSERVE CLEARED ($(flag_clear_sweep observe))";;
  status)
    if _live; then echo "observing: $(flag_get skill) | notes: $(flag_get notes_dir) | skill file: $(flag_get skill_file)"
    else echo "not observing"; fi;;
  get)
    case " $FIELDS " in *" $2 "*) ;; *) echo "get: unknown field '$2'" >&2; exit 2;; esac
    _live && flag_get "$2";;
  set)
    case " $FIELDS " in *" $2 "*) ;; *) echo "set: unknown field '$2'" >&2; exit 2;; esac
    case "$3" in *$'\n'*) echo "set: value may not contain a newline" >&2; exit 2;; esac
    [ -f "$FLAG" ] || exit 1
    args=(); for f in $FIELDS; do
      if [ "$f" = "$2" ]; then v="$3"; else v="$(flag_get "$f")"; fi
      args+=("$f=$v")
    done
    flag_write "${args[@]}";;
  *) echo "usage: observe_flag.sh arm <skill> | clear | status | get <field> | set <field> <value>" >&2; exit 2;;
esac
exit 0
