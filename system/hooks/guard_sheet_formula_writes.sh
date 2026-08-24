#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: a Google Sheet's OWN locks do not stop a write authenticated as the file's OWNER. Proven live
#      on 2026-06-20: a strict dropdown AND a warning-only protected range each let an API write
#      through unchanged. The only place to stop an owner-credential write is HERE, on this machine,
#      before the command reaches Google. Built after a real billing miscount, where a session
#      silently overwrote a summary FORMULA cell and every number downstream of it moved.
# GUARDS: a `gws sheets ... values update` or `values batchUpdate` whose TARGET cells hold a FORMULA
#      (the value starts with "=") or carry the 🔒 lock emoji. Universal — it works on ANY sheet the
#      account can write, with no per-sheet configuration. APPENDS ALWAYS PASS: a new row cannot
#      overwrite a formula. Writes to empty or plain input cells pass. This is the append-only model,
#      enforced rather than requested.
#      ⚠ KNOWN EDGE: a single-cell write into an ARRAYFORMULA *spill* cell reads back blank and is not
#      caught. Mitigated by the append-only rule in the skill, and by marking such column headers with
#      the lock emoji so the header-level catch applies.
# REDIRECT: if changing that formula is genuinely what was asked for, show the exact before and after
#      to the person whose sheet it is, and retry the SAME command with LIFEHACK_SHEET_CONFIRM=1
#      prefixed. Never add the marker without that yes.
# SIGNPOST: system/sops/google-sheet-sop.md holds the rule this enforces; the `/google-sheet` skill
#      holds the 🔒 convention. Change it there.
# FAIL_POSTURE: closed for a write it can see targeting a sheet — if it cannot read back what it is
#      about to overwrite, it denies. OPEN for a payload it cannot parse at all; see the note below.
# UPDATED: 2026-08-11 (ported; jq replaced by python3, the parse-failure posture corrected, the gws
#      lookup de-hardcoded, and the confirmation marker rebranded)
# ─────────────────────────────────────────────────────────────────────────────
#
# ⛔ THIS FILE USED TO PARSE ITS INPUT WITH `jq`, AND THAT WAS A LOADED GUN — the same one described at
# the top of guard_sheet_writes.sh. Every jq call ended in `|| deny`, so on a machine without jq this
# hook exited 2 on EVERY Bash command in the session, `ls -la` included. Measured 2026-08-11. jq is
# absent on older macOS, on a plain Linux box, and in Git Bash on Windows. python3 does the same work
# and is already required by every other hook here.
CONFIRM_MARK="LIFEHACK_SHEET_CONFIRM=1"
GWS="$(command -v gws 2>/dev/null)"

deny() {
  printf 'BLOCKED (sheet formula guard): %s\n' "${1:-this write targets a FORMULA or 🔒 cell on a Google Sheet.}" >&2
  printf '%s\n' "WHY: the sheet computes its own maths, and a script writing as the file's owner can silently overwrite a formula and corrupt every number downstream of it. Google's own locks do NOT stop an owner write — this does." >&2
  printf '%s\n' "REDIRECT: normal work only APPENDS rows and is never blocked. If changing this formula is genuinely what was asked for, show the exact before and after to the person whose sheet it is, and retry the same command with LIFEHACK_SHEET_CONFIRM=1 prefixed. Never add the marker without that yes." >&2
  printf '%s\n' "RULE: system/sops/google-sheet-sop.md, and the 🔒 convention in the /google-sheet skill." >&2
  exit 2
}
deny_unknown() {
  printf 'BLOCKED (sheet formula guard): %s\n' "this gws command hides its operation or its target behind a shell variable or a command substitution, so this guard cannot tell what it would do." >&2
  printf '%s\n' "WHY: every check below matches LITERAL text; a \$VAR or \$(...) defeats all of them, and until this guard imported the shared parser such a command was allowed through unconditionally and silently. An unknown must never be read as permission." >&2
  printf '%s\n' "REDIRECT: re-run the command with the operation and the target written out literally so the guard can see them — or, if this is a deliberate reviewed write, prefix LIFEHACK_SHEET_CONFIRM=1." >&2
  printf '%s\n' "RULE: system/hooks/lib/gws_guard.py holds the parser this guard defers to for anything indirected; change the parser there, not by loosening this guard." >&2
  exit 2
}

INPUT=$(cat 2>/dev/null)
COMMAND=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
try:
    print((json.load(sys.stdin).get("tool_input", {}) or {}).get("command", "") or "")
except Exception:
    print("")
' 2>/dev/null)

# ⚠ An unreadable payload names no sheet, so there is nothing here to protect — and this hook sits in
# front of every Bash command, where denying on a parse failure walls the session off from the shell
# entirely. Fail-CLOSED applies below, once we know a sheet write is actually in flight.
[ -n "$COMMAND" ] || exit 0

# CONTINUATION-NORMALISE: the shell removes a backslash-newline before running, so the wrapped and
# joined forms execute identically — but every grep below matches on TEXT, so it must see the joined
# form or it misses entirely. Falls back to the un-joined text if perl is unavailable (already a
# dependency elsewhere in this repo's hooks).
COMMAND=$(printf '%s' "$COMMAND" | perl -0pe 's/\\\n/ /g' 2>/dev/null || printf '%s' "$COMMAND")

# Only act on gws sheets commands; everything else passes untouched.
# ⛔ THE BINARY IS MATCHED AS A TOKEN ANYWHERE, NOT AS THE WORD BESIDE THE SERVICE.
# Measured 2026-08-14 (system/tools/firetest-binary-indirection.sh): the previous line required a
# literal `gws` adjacent to the service word, so
#     V=gws ; $V <service> ... <destructive verb>
# never matched, this gate exited 0, and the command reached NONE of the checks below it. A guard
# that never sees a command has not allowed it on purpose — it has not seen it, which is worse,
# because every presence-based audit still scores it green. Three rounds of hardening that day
# tested VERB and TARGET indirection and never scoped the BINARY NAME.
# Two gates now, both deliberately loose: is a gws binary NAMED anywhere, and is this service named.
# A mere mention costs nothing — the real checks below decide, and they are what should decide.
printf '%s' "$COMMAND" | grep -qE "(^|[^A-Za-z0-9_.-])gws([^A-Za-z0-9_-]|$)|bin/gws" 2>/dev/null || exit 0
printf '%s' "$COMMAND" | grep -qE "(^|[[:space:],'\"\\\\])sheets([[:space:],'\"\\\\]|$)" 2>/dev/null || exit 0
# Explicit human-approved bypass.
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
  --destructive '' \
  --write-verbs update,batchupdate 2>/dev/null
[ $? -eq 7 ] && deny_unknown

# Appends create a NEW row — inherently safe, they never touch a formula. Pass.
printf '%s' "$COMMAND" | grep -qiE "values[[:space:],'\"\\\\]+append" 2>/dev/null && exit 0
# Only inspect value-WRITE ops. (Structural batchUpdate is gated by guard_sheet_writes.sh.)
printf '%s' "$COMMAND" | grep -qiE "values[[:space:],'\"\\\\]+(update|batchupdate)" 2>/dev/null || exit 0

# ── From here down a sheet write IS in flight, and every exit is fail-CLOSED.
[ -n "$GWS" ] || deny "gws is not on PATH, so this write cannot be checked against what it would overwrite. A write that cannot be verified is not allowed through."

SHEET_ID=$(printf '%s' "$COMMAND" | grep -oE '[A-Za-z0-9_-]{40,}' | head -1)
[ -n "$SHEET_ID" ] || deny "no spreadsheet id could be read out of this command, so there is no way to check what it would overwrite."

# Pull every target A1 range named in the command.
RANGES=$(printf '%s' "$COMMAND" | grep -oE '"range"[[:space:]]*:[[:space:]]*"[^"]+"' | sed -E 's/.*"range"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')
[ -n "$RANGES" ] || deny "no target range could be read out of this command, so there is no way to check what it would overwrite."

# For each target range, read it back with FORMULA rendering. If any cell is a formula or carries the
# lock emoji, block.
while IFS= read -r RANGE; do
  [ -n "$RANGE" ] || continue
  PARAMS=$(python3 -c '
import sys, json
print(json.dumps({"spreadsheetId": sys.argv[1], "range": sys.argv[2], "valueRenderOption": "FORMULA"}))
' "$SHEET_ID" "$RANGE" 2>/dev/null) || deny "the read-back request could not be built."
  OUT=$("$GWS" sheets spreadsheets values get --params "$PARAMS" 2>/dev/null) || deny "the target range could not be read back from Google, so there is no way to know whether it holds a formula."
  CELLS=$(printf '%s' "$OUT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
for row in (d.get("values") or []):
    for cell in (row or []):
        print(cell)
' 2>/dev/null) || deny "the read-back could not be parsed, so there is no way to know whether the target holds a formula."
  printf '%s' "$CELLS" | grep -qE '^=' 2>/dev/null && deny
  printf '%s' "$CELLS" | grep -qF $'\xf0\x9f\x94\x92' 2>/dev/null && deny
done <<EOF
$RANGES
EOF

exit 0
