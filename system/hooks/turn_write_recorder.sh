#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "turn_write_recorder.sh" "${_trw_event:-PostToolUse}" "Write|Edit|NotebookEdit|Bash" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: v2 plan 3b.3 piece 1 (the back door). A student never runs `git commit`, so the commit checks never see what
#      they build, and the front door (guard_build_mode) fired in only 2 of 12 live sessions. This records WHICH FILES
#      a session wrote so end_of_turn_checks.sh (Stop) can run the existing checks on exactly those files.
# GUARDS: nothing -- OBSERVE (PostToolUse, always exit 0, no output). Switches: roundB.conf `back_door` / `own_list`;
#      all three switches (back_door, own_list, own_list_unhomed) OFF = records nothing, exactly today's behaviour. One line per file, appended to
#      ${LHB_TURN_WRITES_DIR:-~/.claude/run/turn-writes}/<session_id>.list :
#          <prompt_id> TAB <new|edit> TAB <absolute path>
#      Write/Edit/NotebookEdit: the payload's file_path / notebook_path (a Write whose tool_response.type is "create"
#      is `new`; everything else is `edit`). Bash: whatever trw_bash_targets returns (below), kept only if the file
#      exists afterwards, and `new` only if its birth time is within the last 120 s.
#      Stated loss: Bash writes through $VARs it cannot resolve, `python -c`, scripts and `sed -i` are not seen.
#      No filesystem "what changed" sweep, on purpose: it can blame one window for another window's files.
#      switch `record_failed_writes` (exam D-B06, 2026-11-02): a tool call that ended non-zero fires PostToolUseFailure, never PostToolUse,
#          so a heredoc that wrote a tool and then returned exit 1 was invisible. The same hook is registered there. Real payload (2.1.317):
#          tool_input, prompt_id, error, is_interrupt, duration_ms, and no tool_response. A failed call may have written nothing, so a target
#          is kept only if it changed since the command started (now - duration_ms - 2 s; 120 s when the payload has no duration_ms), and is
#          `new` only if it was also born then. OFF = a failure event records nothing. A failed Edit that never ran (old_string not found)
#          fires no event at all.
# REDIRECT: the reader is system/hooks/end_of_turn_checks.sh.
# SIGNPOST: spec = notes record 2026-10-30-roundB-back-door-proposal.md (#8); rule for the Bash half lives in
#      lib/bash_write_door.sh. The Bash-parsing swap point is ONE function, trw_bash_targets.
# FAIL_POSTURE: degrade-safe -- any error exits 0 and records nothing.
# UPDATED: 2026-11-02
# ─────────────────────────────────────────────────────────────────────────────
. "$_lhb_dir/lib/roundb.sh" 2>/dev/null || roundb_on() { return 1; }
roundb_on back_door || roundb_on own_list || roundb_on own_list_unhomed || roundb_on inline_keep_nudge || exit 0
IFS= read -r -d '' P || true
[ -n "$P" ] || exit 0
# Matched on the raw JSON: a command quoting this text has it escaped (\"), so it cannot match.
re_failed='"hook_event_name"[[:space:]]*:[[:space:]]*"PostToolUseFailure"'
FAILED=0; if [[ $P =~ $re_failed ]]; then _trw_event=PostToolUseFailure; roundb_on record_failed_writes || exit 0; FAILED=1; fi

# trw_stamp <bsd-format> <gnu-format> <path> -> the file's time in seconds, or nothing.
trw_stamp() {
  local v
  v="$(stat -f "$1" "$3" 2>/dev/null)" && case "$v" in ""|*[!0-9]*) ;; *) printf '%s' "$v"; return 0 ;; esac
  v="$(stat -c "$2" "$3" 2>/dev/null)" && case "$v" in ""|*[!0-9]*) ;; *) printf '%s' "$v" ;; esac
  return 0
}
# trw_failed_kind <path> -> `new` or `edit` if the failed command changed this file, nothing if it did not.
trw_failed_kind() {
  [ -f "$1" ] || return 0
  local m b
  m="$(trw_stamp %m %Y "$1")"; [ -n "$m" ] && [ "$m" -ge "$SINCE" ] || return 0
  b="$(trw_stamp %B %W "$1")"; case "$b" in ""|0) b="$m" ;; esac
  if [ "$b" -ge "$SINCE" ]; then echo new; else echo edit; fi
}

# trw_bash_targets <command> <cwd> -> prints absolute paths a Bash command appears to write, one per line.
# Reads lib/bash_write_door.sh (bwd_write_targets).
trw_bash_targets() {
  . "$_lhb_dir/lib/bash_write_door.sh" 2>/dev/null || return 0  # allow-silence: observer hook, degrade-safe by design (it must never block or fail a tool call)
  local t
  bwd_write_targets "$1" 2>/dev/null | while IFS= read -r t; do
    case "$t" in ""|__BWD_*) continue ;; "~"*) t="$HOME${t#"~"}" ;; esac
    case "$t" in /*) ;; *) t="$2/$t" ;; esac
    printf '%s\n' "$t"
  done
}

F="$(printf '%s' "$P" | python3 -c '
import sys, json
try:
    d = json.loads(sys.stdin.read()); ti = d.get("tool_input") or {}; tr = d.get("tool_response")
    created = isinstance(tr, dict) and tr.get("type") == "create"
    print(d.get("session_id", "")); print(d.get("prompt_id", "")); print(d.get("tool_name", ""))
    print("new" if created else "edit"); print(ti.get("file_path") or ti.get("notebook_path") or ""); print(d.get("cwd", ""))
    dur = d.get("duration_ms"); print(int(dur) // 1000 + 1 if isinstance(dur, (int, float)) and dur >= 0 else "")
except Exception:
    pass
' 2>/dev/null)"
{ IFS= read -r SID; IFS= read -r PID; IFS= read -r TOOL; IFS= read -r KIND; IFS= read -r FP; IFS= read -r CWD; IFS= read -r RAN; } <<< "$F"
case "$SID" in ""|*[!A-Za-z0-9_-]*) exit 0 ;; esac
PID="${PID//[!A-Za-z0-9_-]/}"
DIR="${LHB_TURN_WRITES_DIR:-$HOME/.claude/run/turn-writes}"; LIST="$DIR/$SID.list"
if [ "$FAILED" = 1 ]; then SINCE=$(( $(date +%s) - ${RAN:-118} - 2 )); fi
case "$TOOL" in
  Write|Edit|MultiEdit|NotebookEdit)
    case "$FP" in /*) ;; *) exit 0 ;; esac
    if [ "$FAILED" = 1 ]; then KIND="$(trw_failed_kind "$FP")"; [ -n "$KIND" ] || exit 0; fi
    mkdir -p "$DIR" 2>/dev/null; printf '%s\t%s\t%s\n' "$PID" "$KIND" "$FP" >> "$LIST" 2>/dev/null ;;  # allow-silence: observer hook, degrade-safe by design (it must never block or fail a tool call)
  Bash)
    case "$P" in *">"*|*tee*|*cp*|*mv*|*install*|*rsync*|*dd*|*touch*) ;; *) exit 0 ;; esac    # no write-shaped word: skip
    CMD="$(printf '%s' "$P" | python3 -c 'import sys,json; print((json.loads(sys.stdin.read()).get("tool_input") or {}).get("command",""), end="")' 2>/dev/null)"
    [ -n "$CMD" ] || exit 0
    NOW="$(date +%s)"
    while IFS= read -r t; do
      [ -f "$t" ] || continue
      if [ "$FAILED" = 1 ]; then
        k="$(trw_failed_kind "$t")"; [ -n "$k" ] || continue
        mkdir -p "$DIR" 2>/dev/null; printf '%s\t%s\t%s\n' "$PID" "$k" "$t" >> "$LIST" 2>/dev/null  # allow-silence: observer hook, degrade-safe by design (it must never block or fail a tool call)
        continue
      fi
      born="$(stat -f %B "$t" 2>/dev/null || stat -c %W "$t" 2>/dev/null)"
      case "$born" in ""|*[!0-9]*|0) born="$(stat -f %m "$t" 2>/dev/null || stat -c %Y "$t" 2>/dev/null)" ;; esac
      k=edit; [ -n "$born" ] && [ $((NOW - born)) -lt 120 ] && k=new
      mkdir -p "$DIR" 2>/dev/null; printf '%s\t%s\t%s\n' "$PID" "$k" "$t" >> "$LIST" 2>/dev/null  # allow-silence: observer hook, degrade-safe by design (it must never block or fail a tool call)
    done < <(trw_bash_targets "$CMD" "${CWD:-$PWD}") ;;
esac
exit 0
