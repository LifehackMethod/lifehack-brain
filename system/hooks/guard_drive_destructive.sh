#!/bin/bash
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="${BASH_SOURCE[0]}"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac; . "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }
trap 'lhb_journal_fire "$?" "guard_drive_destructive.sh" "PreToolUse" "Bash" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: guard_sheet_writes.sh protects a Sheet's tabs and cells, but deleting the whole Sheet FILE from Drive, or
#      deleting many Drive files at once, went through a different door (`gws drive files delete`, the Drive
#      MCP trash tool) that nothing watched. A spreadsheet used as a database is fine china: the file is the
#      database. Round C, fine-china list (plan PHASE 3b.4 item 4).
# GUARDS: two pieces, each behind its own switch in system/hooks/roundB.conf (OFF = this hook does nothing):
#      fc_sheet_file_delete: deleting or trashing ONE Drive file that is a Google Sheet -> ASK the person first.
#      fc_drive_bulk_delete: more than one file in one action, a query/wildcard delete, a loop or xargs of
#      deletes, or emptying the trash -> ASK the person first.
#      Routes read: `gws drive files delete|trash`, `files update` with trashed:true, emptyTrash (through the shared
#      gws parser: bash -c bodies, argv lists, assignment prefixes, xargs/for/while/find -exec), and the Drive MCP
#      tool trash_file. Deleting one NON-sheet file, listing, searching and every other command pass untouched.
#      Round C gap 4: many separate MCP trash_file calls are counted per session (state file keyed by session_id in
#      ${LHB_DRIVE_TRASH_DIR:-~/.claude/run/drive-trash}); the 2nd different file within 10 minutes asks, as does every one after.
#      NOT COVERED: the Drive web UI (not the assistant's act); a delete built by a script file that is run
#      by name (the script's text is never in the command); the Google Sheets API itself deleting a file (it cannot).
# REDIRECT: this is an ASK, so nobody is stuck. Show the person the exact file(s) and what will happen (a Sheet: its
#      name; bulk: the count or query), and on their in-the-moment yes retry the same command with
#      (no marker any more: a token the model can type is not approval). The harness asks
#      the person directly (permissionDecision: ask) - answering yes is the confirmation. Drive trash keeps a file
#      for 30 days; a permanent delete or an emptied trash does not.
# WHO-COULD-THIS-BREAK: an unattended job that deletes its own scratch files in bulk, and any session cleaning up
#      many Drive files, is stopped to ask; with nobody to answer, the run waits. WAY-THROUGH: the person says yes
#      and answers the harness prompt (headless it is a refusal), or
#      the person turns the switch off. One scratch file that is not a Sheet is never asked about.
# SIGNPOST: the Sheet rules live in system/sops/google-sheet-sop.md; what is gated here is set by the two switches
#      and this file. Change the rule here deliberately, never loosen it to fit a refused command.
# FAIL_POSTURE: closed for what it can read (a Drive delete it cannot tell is a Sheet is ASKED about); open for
#      an unreadable payload or a command that names no Drive delete, because it sits in front of every Bash command.
# UPDATED: 2026-10-30
# RULE: system/hook-contract.md (mechanics)
# ─────────────────────────────────────────────────────────────────────────────
. "$_lhb_dir/lib/roundb.sh" 2>/dev/null || exit 0
roundb_on fc_sheet_file_delete && SW_SHEET=1 || SW_SHEET=0
roundb_on fc_drive_bulk_delete && SW_BULK=1 || SW_BULK=0
[ "$SW_SHEET$SW_BULK" = "00" ] && exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("tool_name",""))
except Exception: print("")' 2>/dev/null)
case "$TOOL" in
  Bash) printf '%s' "$INPUT" | grep -qi 'drive' || exit 0
        : ;;   # Round C practice: no model-typed confirm token (LIFEHACK_DRIVE_CONFIRM=1 is gone); the only way through is the person's answer to the harness ask
  mcp__*trash_file) : ;;
  *) exit 0 ;;
esac

LIB="$_lhb_dir/lib/drive_guard.py"
[ -r "$LIB" ] || exit 0
V=$(printf '%s' "$INPUT" | python3 "$LIB" 2>/dev/null)
KIND="${V%%$'\t'*}"; DETAIL="${V#*$'\t'}"

ask() {   # ask <what> <why-line>: the harness asks the PERSON (reaches them even under bypass interactively; headless it is a refusal the session sees)
  R="ASK FIRST (Drive guard): $1 WHY: $2 WAY THROUGH: the person answers yes to the prompt that appears; never retry with a marker or another route. RULE: system/hooks/guard_drive_destructive.sh (fc_sheet_file_delete, fc_drive_bulk_delete)."
  python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":sys.argv[1]}}))' "$R"
  exit 0
}

# Round C gap 4 (fc_drive_bulk_delete): many separate MCP trash_file calls are one bulk delete spread over turns.
# The 2nd different file trashed in this session within 10 minutes asks (and every one after it).
if [ "$TOOL" != Bash ] && [ "$SW_BULK" = 1 ] && [ "$KIND" = SINGLE ]; then
  N=$(printf '%s' "$INPUT" | python3 "$LIB" --count 2>/dev/null)
  case "$N" in ''|*[!0-9]*) N=1 ;; esac
  [ "$N" -ge 2 ] && ask "this is Drive file number $N sent to the trash in this session within 10 minutes." "several separate trash calls add up to a bulk delete that no single call looks like; the person should see the whole list before it grows."
fi

case "$KIND" in
  BULK)
    [ "$SW_BULK" = 1 ] && ask "this deletes more than one Drive file at once ($DETAIL)." "bulk deletes and an emptied trash cannot be undone file by file, and the moment they run is never the moment anyone is checking the list." ;;
  SINGLE)
    [ "$SW_SHEET" = 1 ] || exit 0
    K=$(python3 "$LIB" --kind "$DETAIL" 2>/dev/null); KK="${K%%$'\t'*}"; NAME="${K#*$'\t'}"
    case "$KK" in
      SHEET) ask "this deletes a whole Google Sheet file${NAME:+ ($NAME)}." "a Sheet used as a database is the database; deleting the file takes every tab and every row with it (only a tab delete was guarded before)." ;;
      UNKNOWN) ask "this deletes a Drive file this guard cannot identify (it may be a whole Google Sheet)." "it could not look the file up, and an unknown delete is asked about rather than assumed harmless." ;;
      *) exit 0 ;;
    esac ;;
esac
exit 0
