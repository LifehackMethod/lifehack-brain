#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "end_of_turn_checks.sh" "Stop" "" 2>/dev/null || true' EXIT
. "$_lhb_dir/lib/watch_gate.sh" 2>/dev/null && watch_gate end_of_turn_checks.sh --shadow-only  # Round D B.5: watch-only mode (no-op unless mode=watch / LIFEHACK_WATCH=1)
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: v2 plan 3b.3 pieces 1+2 (the back door + "your own list"). Students never commit, so the four commit checks
#      never run for them; and a tool built in the personal code folder was "unregistered" in 12 of 12 live sessions.
#      This runs the existing checks at the END of the turn, on only the files turn_write_recorder.sh listed.
# GUARDS: Stop. Silent (exit 0, no output, no python) when the turn created no file. On the files this turn CREATED:
#      switch `back_door`: hides_failure.py (.sh/.py), is_copy.py (any), connected.py (inside the harness folder),
#          each in `--files` mode (no git). safe_to_ship is NOT run (a Write-created file never has +x).
#      switch `own_list`: a new tool/skill in the personal code folder that is not in the person's OWN list
#          (<personal code folder>/register.jsonl) -- the message carries the exact one-line command to add it.
#      switch `own_list_unhomed` (Round C 5A): a NEW .py/.sh/SKILL.md outside EVERY home (plugin, notes, personal code folder;
#          same scratch/.claude/.config exemptions as placement rule code-outside-homes -- own_list_add.py --unhomed calls
#          build_mode.outside_homes_target) is flagged too: "move it to <personal>/tools/<name>, then run <own_list_add cmd>";
#          a folder the person KEPT (a `kept<TAB><folder>` line in ~/.config/lifehack/placement.conf) instead gets
#          "it stays here by your choice; list it: ... --keep <file>", which lists it in the personal folder's own list by
#          absolute path. Silent when no personal code folder resolves. No GitHub needed.
#      All OFF = does nothing. A failure BLOCKS ONCE (JSON decision on stdout, exit 0); stop_hook_active=true never
#      blocks again; at most 3 blocks per session; a file is never asked about twice. Edits to old files are recorded
#      but not checked (it would re-flag their old backlog). No model call, no network.
# REDIRECT: fix the flagged line / run the printed own-list command. Escapes: `# allow-silence: <why>` on the line
#      (hides_failure), `# not-wired-yet: <why>` in the header (connected).
# SIGNPOST: rules live in system/githooks/checks/*.py and system/tools/door_rules.py; own-list rule in
#      shared/tools/own_list_add.py; switches in system/hooks/roundB.conf. Change them there, not here.
# FAIL_POSTURE: degrade-safe -- a check that crashes is skipped with a stderr line; never wedges a turn.
# UPDATED: 2026-10-30
# ─────────────────────────────────────────────────────────────────────────────
. "$_lhb_dir/lib/roundb.sh" 2>/dev/null || roundb_on() { return 1; }
DOOR=0; OWN=0; UNH=0; roundb_on back_door && DOOR=1; roundb_on own_list && OWN=1; roundb_on own_list_unhomed && UNH=1
# Round D A.6: the person may switch the where-to-save list checks off (placement_user_off); fine-china guards have no such switch
PO=0; roundb_on placement_user_off && PO=1
if [ "$PO" = 1 ]; then
  [ "$OWN" = 1 ] && python3 "$_lhb_dir/lib/placement_off.py" off own-list && OWN=0
  [ "$UNH" = 1 ] && python3 "$_lhb_dir/lib/placement_off.py" off unhomed && UNH=0
fi
[ "$DOOR$OWN$UNH" = "000" ] && exit 0
IFS= read -r -d '' P || true
re_sid='"session_id"[[:space:]]*:[[:space:]]*"([A-Za-z0-9_-]+)"'; re_pid='"prompt_id"[[:space:]]*:[[:space:]]*"([A-Za-z0-9_-]+)"'
[[ $P =~ $re_sid ]] || exit 0; SID="${BASH_REMATCH[1]}"
PID=""; [[ $P =~ $re_pid ]] && PID="${BASH_REMATCH[1]}"
DIR="${LHB_TURN_WRITES_DIR:-$HOME/.claude/run/turn-writes}"; LIST="$DIR/$SID.list"
[ -s "$LIST" ] || exit 0
declare -a FILES=(); SEEN=$'\n'     # bash 3.2 (macOS /bin/bash): no associative arrays
while IFS=$'\t' read -r pid kind path; do
  [ "$pid" = "$PID" ] && [ "$kind" = new ] && [ -f "$path" ] && case "$SEEN" in *$'\n'"$path"$'\n'*) ;; *) SEEN+="$path"$'\n'; FILES+=("$path") ;; esac
done < "$LIST"
# drop this turn's rows (they are consumed whatever happens next); an emptied list is removed
awk -F'\t' -v p="$PID" '$1 != p' "$LIST" > "$LIST.tmp" 2>/dev/null && mv "$LIST.tmp" "$LIST" 2>/dev/null
[ -s "$LIST" ] || rm -f "$LIST" 2>/dev/null
[[ $P == *'"stop_hook_active":true'* || $P == *'"stop_hook_active": true'* ]] && exit 0   # already asked once this turn
[ "${#FILES[@]}" -gt 0 ] || exit 0
CNT="$DIR/$SID.asked"; N=0; [ -f "$CNT" ] && read -r N < "$CNT"; [ "${N:-0}" -ge 3 ] && exit 0
FLAGGED="$DIR/$SID.flagged"
declare -a ALL=() CODE=()
for f in "${FILES[@]}"; do  # empty-ok: FILES was checked non-empty just above
  grep -qxF "$f" "$FLAGGED" 2>/dev/null && continue
  ALL+=("$f"); case "$f" in *.sh|*.py) CODE+=("$f") ;; esac
done
[ "${#ALL[@]}" -gt 0 ] || exit 0
HAR="$(cd "$_lhb_dir/../.." 2>/dev/null && pwd -P)"; CH="$HAR/system/githooks/checks"; OUT=""
run() { local o rc; o="$(python3 "$CH/$1" --files "${@:2}" 2>&1)"; rc=$?
        if [ "$rc" -eq 1 ]; then OUT+="$(printf '%s\n' "$o" | grep -E 'REFUSED' | grep -v '^FINDING ' | cut -c1-400 | head -6)"$'\n'
        elif [ "$rc" -ne 0 ]; then echo "end_of_turn_checks: $1 crashed (rc $rc); skipped" >&2; fi; }
if [ "$DOOR" = 1 ]; then
  [ "${#CODE[@]}" -gt 0 ] && run hides_failure.py "${CODE[@]}"
  run is_copy.py "${ALL[@]}"
  INSIDE=""; for f in "${ALL[@]}"; do case "$(cd "$(dirname "$f")" 2>/dev/null && pwd -P)/$(basename "$f")" in "$HAR"/*) INSIDE=1 ;; esac; done
  [ -n "$INSIDE" ] && run connected.py "${ALL[@]}"
fi
if [ "$OWN" = 1 ]; then
  o="$(python3 "$HAR/shared/tools/own_list_add.py" --check "${ALL[@]}" 2>/dev/null)"
  [ -n "$o" ] && { OUT+="$(printf '%s\n' "$o" | cut -c1-600 | head -6)"$'\n'; [ "$PO" = 1 ] && OUT+="$(python3 "$_lhb_dir/lib/placement_off.py" stop own-list)"$'\n'; }
fi
if [ "$UNH" = 1 ]; then
  o="$(python3 "$HAR/shared/tools/own_list_add.py" --unhomed "${ALL[@]}" 2>/dev/null)"
  [ -n "$o" ] && { OUT+="$(printf '%s\n' "$o" | cut -c1-700 | head -6)"$'\n'; [ "$PO" = 1 ] && OUT+="$(python3 "$_lhb_dir/lib/placement_off.py" stop unhomed)"$'\n'; }
fi
OUT="$(printf '%s' "$OUT" | grep -v '^$' | head -12)"
[ -n "$OUT" ] || exit 0
printf '%s\n' "${ALL[@]}" >> "$FLAGGED"; mkdir -p "$DIR"; echo $((N + 1)) > "$CNT"
NLINES=$(printf '%s\n' "$OUT" | grep -c .)
if [ "$NLINES" -gt 1 ] && roundb_on eot_do_all; then   # Round C practice: with two findings a session fixed the first and skipped the listing line; number them and say ALL
  OUT="$(printf '%s\n' "$OUT" | awk 'NF{n++; printf "(%d) %s\n", n, $0}')"
  OUT="DO ALL $NLINES OF THESE before you finish (this check will not ask again):"$'\n'"$OUT"
fi
ESC=1; roundb_on eot_escape_scoped && ! printf '%s' "$OUT" | grep -q 'REFUSED' && ESC=0   # Round C practice: a list-only stop must not show the escapes (a session took '# not-wired-yet' instead of listing the file)
{ echo "END-OF-TURN CHECK: a file you created this turn needs fixing before you finish. (Runs once per turn; it will not ask again.)"
  printf '%s\n' "$OUT"
  [ "$ESC" = 1 ] && echo "Escapes, only if intended: '# allow-silence: <why>' on the flagged line; '# not-wired-yet: <why>' in the file header. Rules: system/githooks/checks/*.py, shared/tools/own_list_add.py; switches: system/hooks/roundB.conf."; } \
  | python3 -c 'import json,sys; print(json.dumps({"decision":"block","reason":sys.stdin.read()}))'
exit 0
