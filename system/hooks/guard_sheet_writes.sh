#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: a spreadsheet used as a database is fine china. Two rules that nothing used to enforce:
#      (1) READ THE RULES FIRST — every sheet built by this system carries a `_LLM_GUIDE` tab holding
#      its structure and its conventions, and writing before reading it is how a working sheet gets
#      quietly broken. (2) DESTRUCTIVE operations — clear, delete, mass-overwrite — are irreversible,
#      and the moment they happen is never the moment anyone is being careful.
# GUARDS: (1) ANY `gws sheets` WRITE is blocked until this window has READ that sheet's `_LLM_GUIDE`
#      tab — a read whose range names the instruction tab records a per-sheet marker, good for 12h.
#      (2) DESTRUCTIVE writes need an explicit confirmation on top. (3) STRUCTURAL edits (adding or
#      removing tabs, columns, formatting, protection) are sent to the SOP and the skill first.
#      Reads ALWAYS pass, so reading the guide is never blocked. Narrow appends pass once read.
# REDIRECT: read it first —
#      gws sheets spreadsheets values get --params '{"spreadsheetId":"<ID>","range":"_LLM_GUIDE!A:Z"}'
#      — then retry. For a destructive op, get an in-the-moment YES from the person whose sheet it is,
#      then retry with LIFEHACK_SHEET_CONFIRM=1 prefixed.
# SIGNPOST: the rules live in system/sops/google-sheet-sop.md; the design side is the `/google-sheet`
#      skill. Change what is gated THERE, then update this file.
# FAIL_POSTURE: closed for a command it can read that names a sheet; open for a payload it cannot
#      read at all — see the note below, which is the whole reason this file was rewritten.
# UPDATED: 2026-08-11 (ported; jq replaced by python3, the parse-failure posture corrected, and the
#      confirmation marker rebranded)
# ─────────────────────────────────────────────────────────────────────────────
#
# ⛔ THIS FILE USED TO PARSE ITS INPUT WITH `jq`, AND THAT WAS A LOADED GUN. Both lines that read the
# payload ended in `|| deny`, so on a machine WITHOUT jq the command substitution failed and the hook
# exited 2 — a hard block — on EVERY Bash command in the session, `ls -la` included, with a deny
# message about destructive spreadsheet operations. Measured 2026-08-11: with jq removed from PATH and
# nothing else changed, `ls -la` returned exit 2 from both sheet guards. jq only arrived in macOS's own
# /usr/bin recently; it is absent on older macOS, on a plain Linux box, and in Git Bash on Windows,
# which is this project's documented Windows floor. python3 is already required by every other hook
# here, so there is now one interpreter dependency instead of two.
CONFIRM_MARK="LIFEHACK_SHEET_CONFIRM=1"
MARKDIR="${SHEET_LLM_MARKDIR:-$HOME/.claude/run/sheet-llm}"
TTL=$(( 12 * 3600 ))

deny() {
  printf 'BLOCKED (sheet guard): %s\n' "$1" >&2
  printf '%s\n' "$2" >&2
  printf '%s\n' "RULE: system/sops/google-sheet-sop.md holds the rules of engagement; the /google-sheet skill holds the design side. Change what is gated there, not here." >&2
  exit 2
}
deny_llm() {
  deny "a write to a Google Sheet before this window read its _LLM_GUIDE tab." \
"WHY: every sheet this system builds carries a _LLM_GUIDE tab holding its structure, who owns which fact, and its write rules. Writing before reading it is how a working sheet gets quietly broken.
REDIRECT: read that tab for THIS spreadsheet first — gws sheets spreadsheets values get --params '{\"spreadsheetId\":\"<ID>\",\"range\":\"_LLM_GUIDE!A:Z\"}' — then retry the write. Any read naming the instruction tab counts, and it holds for 12 hours. A reviewed scheduled writer may carry LIFEHACK_SHEET_CONFIRM=1 to bypass."
}
deny_destr() {
  deny "a destructive Google Sheets operation — clear, delete, or mass-overwrite." \
"WHY: it is irreversible, and the moment it happens is never the moment anyone is being careful.
REDIRECT: back the sheet up first, show the exact range and tab to the person whose sheet it is, and on their in-the-moment yes retry with LIFEHACK_SHEET_CONFIRM=1 prefixed. Never add the marker without that yes."
}
deny_struct() {
  deny "a structural Google Sheets edit — spreadsheets batchUpdate adds or removes tabs, columns, formatting or protected ranges." \
"WHY: changing a sheet's STRUCTURE, as opposed to appending a row, can break formulas, break the _CHECKS self-check layer, or quietly damage a sheet other things depend on.
REDIRECT: read system/sops/google-sheet-sop.md, use the /google-sheet skill (Kickoff or Audit) for the architecture rules, back the sheet up, then retry with LIFEHACK_SHEET_CONFIRM=1. Routine value appends never need this."
}
deny_unknown() {
  deny "this gws command hides its operation or its target behind a shell variable or a command substitution, so this guard cannot tell what it would do." \
"WHY: every check below matches LITERAL text; a \$VAR or \$(...) defeats all of them, and until this guard imported the shared parser such a command was allowed through unconditionally and silently.
An unknown must never be read as permission.
REDIRECT: re-run the command with the operation and the target written out literally so the guard can see them — or, if this is a deliberate reviewed write, prefix LIFEHACK_SHEET_CONFIRM=1. RULE: system/hooks/lib/gws_guard.py holds the parser this guard defers to for anything indirected; change the parser there, not by loosening this guard."
}

INPUT=$(cat 2>/dev/null)
COMMAND=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    print((json.load(sys.stdin).get("tool_input", {}) or {}).get("command", "") or "")
except Exception:
    print("")
' 2>/dev/null)

# ⚠ AN UNREADABLE PAYLOAD IS NOT A BLOCK HERE, and that is a deliberate difference from the donor.
# This hook sits in front of EVERY Bash command. Denying on a parse failure means one malformed
# payload — or one missing interpreter — walls the entire session off from the shell, which is exactly
# the failure the jq note above describes, reached by a second route. Fail-CLOSED applies to what this
# guard is FOR: a command it can read, that names a sheet. A command it cannot read names no sheet, so
# there is nothing here to protect, and the cost of guessing wrong is total.
[ -n "$COMMAND" ] || exit 0

# CONTINUATION-NORMALISE: the shell removes a backslash-newline before running, so the wrapped and
# joined forms execute identically — but every grep below matches on TEXT, so it must see the joined
# form or it misses entirely. Falls back to the un-joined text if perl is unavailable (already a
# dependency elsewhere in this repo's hooks).
COMMAND=$(printf '%s' "$COMMAND" | perl -0pe 's/\\\n/ /g' 2>/dev/null || printf '%s' "$COMMAND")

printf '%s' "$COMMAND" | grep -qE "(^|[^A-Za-z0-9_.-])gws[[:space:]]+sheets([[:space:]]|$)" 2>/dev/null || exit 0
printf '%s' "$COMMAND" | grep -qF "$CONFIRM_MARK" 2>/dev/null && exit 0

# ── THE INDIRECTION CATCH ──────────────────────────────────────────────────────
# Everything below this point (and everything below in the rest of this file) matches LITERAL
# text. Measured by fire test: when the text is NOT literal — a $VAR, a $(substitution), a decoy
# safe word, a wrapper word before the binary — every literal matcher misses and the command fell
# through to allow, unconditionally and silently. An indirection we cannot resolve is UNKNOWN, and
# UNKNOWN FAILS CLOSED. The parser is shared (one copy, every gws guard) so this cannot rot per file.
LIB="$(cd "$(dirname "$0")" 2>/dev/null && pwd)/lib/gws_guard.py"
[ -r "$LIB" ] || deny_unknown   # no parser, no permission
printf '%s' "$COMMAND" | python3 "$LIB" --service sheets \
  --destructive clear,batchclear,delete \
  --write-verbs update,batchupdate,append,clear,batchclear,delete 2>/dev/null
[ $? -eq 7 ] && deny_unknown

SHEET_ID=$(printf '%s' "$COMMAND" | grep -oE '[A-Za-z0-9_-]{40,}' | head -1)
MARK="$MARKDIR/$SHEET_ID"

# READ branch — matches `sheets spreadsheets values get` and its metadata siblings.
if printf '%s' "$COMMAND" | grep -qiE "sheets[[:space:]]+(spreadsheets[[:space:]]+)?(values[[:space:]]+)?(get|batchget|metadata)" 2>/dev/null; then
  # Record the per-sheet marker when the read names the instruction tab.
  if [ -n "$SHEET_ID" ] && printf '%s' "$COMMAND" | grep -qiE "_LLM_GUIDE|LLM|README|instructions" 2>/dev/null; then
    mkdir -p "$MARKDIR" 2>/dev/null; date +%s > "$MARK" 2>/dev/null
  fi
  exit 0
fi

# Creating a NEW spreadsheet has no existing guide to read and nothing to destroy.
printf '%s' "$COMMAND" | grep -qiE "sheets[[:space:]]+(spreadsheets[[:space:]]+)?create" 2>/dev/null && exit 0

NOW=$(date +%s 2>/dev/null); fresh=0
if [ -n "$SHEET_ID" ] && [ -f "$MARK" ]; then
  TS=$(cat "$MARK" 2>/dev/null)
  [ -n "$TS" ] && [ -n "$NOW" ] && [ $(( NOW - TS )) -lt "$TTL" ] && fresh=1
fi
[ "$fresh" = 1 ] || deny_llm

# STRUCTURAL edit — spreadsheets.batchUpdate restructures tabs/columns/formatting/protection.
printf '%s' "$COMMAND" | grep -qiE "sheets[[:space:]]+spreadsheets[[:space:]]+batchupdate" 2>/dev/null && deny_struct
# DESTRUCTIVE — irreversible data loss.
printf '%s' "$COMMAND" | grep -qiE "sheets[[:space:]]+(spreadsheets[[:space:]]+)?(values[[:space:]]+)?(clear|batchclear|delete)" 2>/dev/null && deny_destr
printf '%s' "$COMMAND" | grep -qiE "sheets[[:space:]]+spreadsheets[[:space:]]+values[[:space:]]+batchupdate" 2>/dev/null && deny_destr
if printf '%s' "$COMMAND" | grep -qiE "sheets[[:space:]]+(spreadsheets[[:space:]]+)?values[[:space:]]+update" 2>/dev/null; then
  printf '%s' "$COMMAND" | grep -qE "[A-Z]+:[A-Z]+" 2>/dev/null && deny_destr
fi
exit 0
