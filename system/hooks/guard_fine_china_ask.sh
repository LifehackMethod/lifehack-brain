#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "guard_fine_china_ask.sh" "PreToolUse" "Bash|Write|Edit|MultiEdit" 2>/dev/null || true' EXIT
. "$_lhb_dir/lib/watch_gate.sh" 2>/dev/null && watch_gate guard_fine_china_ask.sh  # Round D B.5: watch-only mode (no-op unless mode=watch / LIFEHACK_WATCH=1)
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Round D rulings A.1 + A.6 (Enver, 2026-10-31): deleting a local database, deleting a whole folder, and changing the
#      person's OWN SOP files are fine china (Round C misses F08, F09, F11). The protection is an ASK, never a block.
#      The user's override file ~/.config/lifehack/placement.conf may only be changed with a real human Yes.
# GUARDS: PreToolUse Bash|Write|Edit|MultiEdit. Four pieces, each behind its own switch in system/hooks/roundB.conf (OFF = does nothing):
#      fc_db_delete_ask, fc_folder_delete_ask, fc_user_sop_ask, fc_placement_conf_ask. Engine and exact rules: lib/fine_china_ask.py header.
#      Throwaway folders (node_modules, build, dist, .venv, __pycache__, temp, scratchpads, git-ignored, empty) never ask.
# REDIRECT: it is an ASK (harness permissionDecision "ask"); nobody is stuck. Headless runs turn it into a refusal: stop and tell the person.
# WHO-COULD-THIS-BREAK: a session or script that cleans a real folder, drops a table, or rewrites a person's SOP; a headless run has nobody to answer.
#      WAY-THROUGH: the person answers Yes, or turns the switch off. No user-level off switch exists (placement.conf is never read here).
# SIGNPOST: logic in lib/fine_china_ask.py; tests in tests/test_fine_china_ask.sh.
# LIMITS: Bash is matched as text; a delete built from a $VARIABLE, a script run by name, or `git clean` is not seen.
# FAIL_POSTURE: open on any internal error (stderr line), because it sits in front of every Bash command.
# UPDATED: 2026-10-31
# ─────────────────────────────────────────────────────────────────────────────
. "$_lhb_dir/lib/roundb.sh" 2>/dev/null || exit 0
roundb_on fc_db_delete_ask || roundb_on fc_folder_delete_ask || roundb_on fc_user_sop_ask || roundb_on fc_placement_conf_ask || exit 0
IFS= read -r -d '' PAYLOAD || true
[ -n "$PAYLOAD" ] || exit 0
printf '%s' "$PAYLOAD" | python3 "$_lhb_dir/lib/fine_china_ask.py" || echo "guard_fine_china_ask: engine failed; allowing" >&2
exit 0
