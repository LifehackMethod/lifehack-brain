#!/bin/bash
# test_archive_before_cut.sh -- Round C 4, switch fc_archive_before_cut: a cut from an SOP/canon file needs a verbatim history-log receipt.
#   Edit/Write/MultiEdit go through guard_canon_write.sh -> lib/cut_receipt.py ; a Bash overwrite goes through guard_build_mode.sh.
#   ALLOW cases first, then refusals; every refusal also run with the switch OFF (must allow). Fictional pond-themed text only.
# Run: bash system/hooks/tests/test_archive_before_cut.sh   (exit 0 = all pass)
HERE="$(cd "$(dirname "$0")" && pwd)"; HOOKS="$(cd "$HERE/.." && pwd)"; CODE_REAL="$(cd "$HOOKS/../.." && pwd)"
CW="$HOOKS/guard_canon_write.sh"; BM="$HOOKS/guard_build_mode.sh"; PAD="$CODE_REAL/system/tools/save/pad_archive.py"
for h in "$CW" "$BM" "$HOOKS/lib/cut_receipt.py" "$PAD"; do [ -f "$h" ] || { echo "CANNOT RUN: $h"; exit 1; }; done
S="$(mktemp -d "${TMPDIR:-/tmp}/abc.XXXXXX")"; trap 'rm -rf "$S"' EXIT
P=0; F=0; OUTF="$S/out"; ERRF="$S/err"
CODE="$S/code"; SOPS="$CODE/system/sops"; DESK="$S/notes/desks/pond/canon"
mkdir -p "$SOPS" "$DESK" "$S/home" "$S/notes/records"
ok() { P=$((P+1)); }; bad() { F=$((F+1)); echo "FAIL: $1"; }

LONG1="The heron stands on the east bank of the pond every morning, and the rule is that nobody feeds it before the bell."
LONG2="Frogs are counted twice a week, once at dusk and once before dawn, and the two counts are written in the green ledger."
LONG3="If the lily pads cover more than half of the water, the keeper clears a third of them and logs the date."
mk_sop() { printf '# Pond SOP\n\n%s\n\n%s\n\n%s\n\nEnd.\n' "$LONG1" "$LONG2" "$LONG3" > "$SOPS/pond-sop.md"; rm -f "$SOPS/pond-sop.history.md"; }
mk_canon() { printf '%s\n\n%s\n' "$LONG1" "$LONG2" > "$DESK/current.md"; rm -f "$DESK/current.history.md"; }

json() { python3 - "$@" <<'PY'
import json, sys
tool, path = sys.argv[1], sys.argv[2]
a = sys.argv[3] if len(sys.argv) > 3 else ""; b = sys.argv[4] if len(sys.argv) > 4 else ""
if tool == "Write": ti = {"file_path": path, "content": a}
elif tool == "Edit": ti = {"file_path": path, "old_string": a, "new_string": b}
elif tool == "MultiEdit": ti = {"file_path": path, "edits": [{"old_string": a, "new_string": b}]}
else: ti = {"command": a}
print(json.dumps({"tool_name": tool, "tool_input": ti, "cwd": "/"}))
PY
}
run_cw() { HOME="$S/home" CLAUDE_PLUGIN_ROOT="$CODE" ROUNDB_FC_ARCHIVE_BEFORE_CUT="$1" bash "$CW" <<<"$2" >"$OUTF" 2>"$ERRF"; RC=$?; }
run_bm() { HOME="$S/home" CLAUDE_PLUGIN_ROOT="$CODE" ROUNDB_FC_ARCHIVE_BEFORE_CUT="$1" bash "$BM" <<<"$2" >"$OUTF" 2>"$ERRF"; RC=$?; }
allow() { # name payload [bm]   (switch ON)
  if [ "$3" = bm ]; then run_bm on "$2"; else run_cw on "$2"; fi
  if [ $RC -eq 0 ]; then ok; else bad "ALLOW $1 [on] rc=$RC $(head -c 200 "$ERRF")"; fi; }
refuse() { # name payload [bm]  -> ON must refuse with the way through; OFF must allow
  if [ "$3" = bm ]; then run_bm on "$2"; else run_cw on "$2"; fi
  if [ $RC -eq 2 ] && grep -q "archive before cut" "$ERRF" && grep -q "WAY THROUGH" "$ERRF" && grep -q "cutlog" "$ERRF" && grep -q "RULE:" "$ERRF"; then ok; else bad "REFUSE $1 [on] rc=$RC $(head -c 200 "$ERRF")"; fi
  if [ "$3" = bm ]; then run_bm off "$2"; else run_cw off "$2"; fi
  if [ $RC -eq 0 ]; then ok; else bad "OFF-ALLOW $1 [off] rc=$RC $(head -c 200 "$ERRF")"; fi; }
hist() { printf '# History log for pond-sop.md\n\n## 2026-10-30 - reason: %s\n\n~~~~\n%s\n~~~~\n' "$1" "$2" > "$SOPS/pond-sop.history.md"; }

SOP="$SOPS/pond-sop.md"; CANON="$DESK/current.md"; NOTE="$S/notes/records/pond-note.md"

# ---------------- ALLOW
mk_sop; allow "pure addition (Edit)" "$(json Edit "$SOP" "End." "End.
Appendix: the pond gate sticks in rain and needs a firm shove.")"
mk_sop; hist "pond tidy" "$LONG2"; allow "Edit whose removed text IS in history.md" "$(json Edit "$SOP" "$LONG2
" "")"
printf '%s %s\n' "$LONG1" "$LONG2" > "$NOTE"
allow "non-SOP file, big cut" "$(json Edit "$NOTE" "$LONG1 $LONG2" "gone")"
mk_sop; allow "tiny edit under 40 chars" "$(json Edit "$SOP" "twice a week" "thrice a week")"
mk_sop; allow "whitespace-only Write" "$(json Write "$SOP" "$(sed 's/^/  /' "$SOP")
")"
mk_sop; allow "re-wrapped paragraph (Edit)" "$(json Edit "$SOP" "$LONG1" "$(printf '%s' "$LONG1" | fold -s -w 40)")"
mk_sop; allow "moved paragraphs inside the file (Write)" "$(json Write "$SOP" "# Pond SOP

$LONG3

$LONG1

$LONG2

End.
")"
rm -f "$SOPS/new-sop.md"; allow "new SOP file (Write)" "$(json Write "$SOPS/new-sop.md" "$LONG1")"
mk_sop; echo "x" > "$SOPS/pond-sop.history.md"; allow "edit to a history.md itself" "$(json Write "$SOPS/pond-sop.history.md" "y")"
mk_sop; printf '## 2026-10-30 - reason: tidy\n\n%s\n\n%s\n' "$LONG1" "$LONG2" > "$SOPS/pond-sop.history.md"
allow "two paragraphs logged in one block" "$(json Edit "$SOP" "$LONG1

$LONG2
" "")"
mk_canon; printf '## 2026-10-30 - reason: canon trim\n\n%s\n' "$LONG1" > "$DESK/current.history.md"; allow "canon cut with history" "$(json Edit "$CANON" "$LONG1
" "")"
mk_sop; python3 "$PAD" cutlog "$SOP" --reason "pond tidy: heron rule retired" --start 3 --end 4 >"$S/cl" 2>&1; grep -q '^RECEIPT ' "$S/cl" && ok || bad "cutlog printed no RECEIPT: $(cat "$S/cl")"
allow "cut after a real pad_archive cutlog (end to end)" "$(json Edit "$SOP" "$LONG1
" "")"
mk_sop; allow "Bash append to SOP (>>)" "$(json Bash "$SOP" "echo more >> $SOP")" bm
mk_sop; allow "Bash write to a non-SOP file" "$(json Bash "$SOP" "echo x > $S/notes/records/z.md")" bm

# P-48 placeholder: a dated, reasoned block holding the private-notes line is a receipt for a private cut
PH="(verbatim original moved to the operator's private notes, 2026-10-30, because it is private)"
mk_sop; printf '# History log\n\n## 2026-10-30 - reason: private pointer removed\n\n%s\n' "$PH" > "$SOPS/pond-sop.history.md"; allow "P-48 placeholder block is a receipt for a cut" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; printf '# History log\n\n## 2026-10-30 - reason: private pointer removed\n\n%s\n' "$PH" > "$SOPS/pond-sop.history.md"; allow "P-48 placeholder, Write drops a section" "$(json Write "$SOP" "# Pond SOP

$LONG1

End.
")"

# ---------------- REFUSE (ON refuses, OFF allows)
mk_sop; printf '# History log\n\n## 2026-10-30\n\n%s\n' "$PH" > "$SOPS/pond-sop.history.md"; refuse "P-48 placeholder but the block has no reason" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; printf '# History log\n\n%s\n' "$PH" > "$SOPS/pond-sop.history.md"; refuse "P-48 placeholder outside any dated block" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; printf '# History log\n\n## 2026-10-30 - reason: x\n\n(verbatim original moved somewhere)\n' > "$SOPS/pond-sop.history.md"; refuse "near-miss placeholder wording" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; refuse "Edit deletes a paragraph, no history file" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; hist "other" "$LONG1"; refuse "history exists but lacks the passage" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; printf '# notes\n\n%s\n' "$LONG2" > "$SOPS/pond-sop.history.md"; refuse "passage present but no dated reason heading" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; printf '## 2026-10-30\n\n%s\n' "$LONG2" > "$SOPS/pond-sop.history.md"; refuse "dated heading but no reason" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; refuse "rewording a rule (old wording not logged)" "$(json Edit "$SOP" "$LONG3" "When lily pads cover most of the water the keeper thins them out and notes the day somewhere.")"
mk_sop; refuse "Write drops a section" "$(json Write "$SOP" "# Pond SOP

$LONG1

End.
")"
# normalisations: the log may quote, bullet, emphasise or re-wrap the passage; a reworded line counts as logged when its whole ORIGINAL line is
hist_raw() { printf '# History log for pond-sop.md\n\n## 2026-10-30 - reason: pond tidy\n\n%s\n' "$1" > "$SOPS/pond-sop.history.md"; }
mk_sop; hist_raw "> $LONG2"; allow "history quotes the passage with a > prefix" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; hist_raw "- **$LONG2**"; allow "history has a list marker and bold around the passage" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; hist_raw "$(printf '%s' "$LONG2" | fold -s -w 30 | sed 's/^/> /')"; allow "history re-wrapped and quoted line by line" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; printf '# Pond SOP\n\n*%s*\n\nEnd.\n' "$LONG1" > "$SOP"; hist_raw "$LONG1"; allow "SOP had emphasis the log lacks" "$(json Edit "$SOP" "*$LONG1*
" "")"
mk_sop; hist_raw "$LONG1"; allow "reworded line, whole original line is in history" "$(json Edit "$SOP" "$LONG1" "The heron stands on the west bank at noon, and the bell rule was dropped.")"
mk_sop; printf '# History log for pond-sop.md\n\n## 2026-10-30 - reason: pond tidy\n\n### 2026-10-30 line 3 (before edit)\n\n%s\n' "$LONG2" > "$SOPS/pond-sop.history.md"; allow "dated sub-entry nested under a block that has a reason" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; refuse "Write replaces SOP with a stub" "$(json Write "$SOP" "# gone")"
mk_canon; refuse "canon cut, no history" "$(json Edit "$CANON" "$LONG2
" "")"
mk_sop; refuse "MultiEdit cut" "$(json MultiEdit "$SOP" "$LONG1
" "")"
mk_sop; refuse "Bash redirect overwrite (heredoc content)" "$(json Bash "$SOP" "cat > $SOP <<'EOF'
# tiny
EOF")" bm
mk_sop; refuse "Bash sed -i on an SOP" "$(json Bash "$SOP" "sed -i '' 's/heron/crane/' $SOP")" bm
mk_sop; printf 'x\n' > "$NOTE"; refuse "Bash cp over an SOP" "$(json Bash "$SOP" "cp $NOTE $SOP")" bm

# normalising must not let UNLOGGED text through
mk_sop; hist_raw "> The heron stands on the east bank of the pond every morning."; refuse "only a fragment of the passage is in history (quoted)" "$(json Edit "$SOP" "$LONG1
" "")"
mk_sop; hist_raw "Frogs are counted three times a week, in the blue ledger, and nothing else."; refuse "history holds different text" "$(json Edit "$SOP" "$LONG2
" "")"
mk_sop; hist_raw "The heron stands on the west bank at noon, and the bell rule was dropped."; refuse "reworded line, only the NEW wording is in history" "$(json Edit "$SOP" "$LONG1" "The heron stands on the west bank at noon, and the bell rule was dropped.")"
mk_sop; printf '# History log for pond-sop.md\n\n## 2026-10-30 - tidy\n\n### 2026-10-30 line 3\n\n%s\n' "$LONG2" > "$SOPS/pond-sop.history.md"; refuse "nested entry but no block has a reason" "$(json Edit "$SOP" "$LONG2
" "")"

# the way through, followed literally, lets the same Edit pass
mk_sop; run_cw on "$(json Edit "$SOP" "$LONG2
" "")"
CMD=$(python3 -c 'import json,sys,re; r=json.loads(sys.stdin.read())["reason"]; m=re.search(r"retry the SAME edit: (python3 .*?)  \(it copies", r); print(m.group(1) if m else "")' < "$ERRF")
if [ -n "$CMD" ]; then
  CMD=$(printf '%s' "$CMD" | sed -E "s#python3 \"[^\"]*pad_archive.py\"#python3 \"$PAD\"#")
  eval "${CMD//<why this text is leaving>/pond tidy}" >"$S/cl" 2>&1
  if grep -q '^RECEIPT ' "$S/cl"; then ok; else bad "printed cutlog command failed: $CMD :: $(cat "$S/cl")"; fi
  run_cw on "$(json Edit "$SOP" "$LONG2
" "")"
  if [ $RC -eq 0 ]; then ok; else bad "retry after the printed cutlog still refused rc=$RC $(head -c 200 "$ERRF")"; fi
else bad "no cutlog command found in the deny"; fi

echo "archive-before-cut: $P passed, $F failed"; [ $F -eq 0 ]
