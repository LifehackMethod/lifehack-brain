#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: on 2026-06-26 a large money error traced back to arithmetic done in the model's head instead
#      of by code. Two obvious fixes were tried and both failed, which is why this one looks the way
#      it does. (1) DETECT the math by regex: 24 of 24 plain-English money questions were missed —
#      "can we afford the new hire?" has no operator and no keyword to match. (2) DETECT it with a
#      cheap model on every turn: ~6 seconds of cold start per turn, which nobody will accept in a
#      synchronous hook. So this does not guess. You DECLARE intent — a subject folder you nominated
#      arms itself, `/calculate` arms anything else — and a deliberately tight regex is a backstop
#      for the obvious cases only, never the main path.
# GUARDS: nothing. It is an INJECT observer: it prints and exits 0, and can never stop a turn. In an
#      un-armed session with no hard math token in the prompt it prints nothing at all.
#      ⚠ It cannot tell a number the model COMPUTED from one it READ — provenance is invisible in
#      text. That is exactly why it re-states a rule rather than gating on an answer; a blocking
#      version of this was designed and rejected for guaranteed false positives.
# REDIRECT: n/a — non-blocking. Arm or disarm with system/hooks/numbers_flag.sh arm|clear, or say
#      `/calculate` and `/calculate off`.
# SIGNPOST: the rule itself lives in the `/calculate` skill (.claude/skills/calculate/SKILL.md).
#      Which subject folders arm themselves is YOUR list, at <notes>/config/numbers-auto-arm — this
#      file ships knowing none of them.
# FAIL_POSTURE: degrade-safe — any error exits 0 silently, and the turn proceeds with nothing added.
# UPDATED: 2026-08-11 (ported; the auto-arm list became the reader's own file, and the two stdin
#      parses became one)
# ─────────────────────────────────────────────────────────────────────────────
set +e

INPUT="$(cat 2>/dev/null)"

# ── ONE parse of the payload, not two. The donor ran python3 twice over the same JSON — once for the
# prompt, once for the cwd — which is two interpreter starts on every single turn of every session
# for one document. A tab-separated single read costs half of that and cannot disagree with itself.
PARSED="$(printf '%s' "$INPUT" | python3 -c 'import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
p = (d.get("prompt") or "").replace("\t", " ").replace("\n", " ")
print(p + "\t" + (d.get("cwd") or ""))' 2>/dev/null)"
PROMPT="${PARSED%%$'\t'*}"
CWD="${PARSED#*$'\t'}"
[ -n "$CWD" ] || CWD="${CLAUDE_PROJECT_DIR:-$PWD}"

# See system/hooks/lib/winpath_fold.sh. Degrade-safe fallback (identity) matches this whole file's
# own posture: "any error exits 0 silently, and the turn proceeds with nothing added."
_ICM_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
. "$_ICM_DIR/lib/winpath_fold.sh" 2>/dev/null || _winfold() { printf '%s' "$1"; }

# The subject folder this window is sitting in, if any. `/ingest` writes <notes>/desks/<subject>/,
# so a window opened inside one has a name here and every other window has an empty string.
# FOLD FOR DETECTION ONLY -- CWD arrives backslash-native on Windows, so the forward-slash test
# below would otherwise never match there. SUBJECT is sliced from the ORIGINAL CWD, below, with a
# slash-or-backslash-tolerant pattern, so a desk's on-disk case is never lowercased by this.
_CWD_C="$(_winfold "$CWD" 2>/dev/null)"; [ -n "$_CWD_C" ] || _CWD_C="$CWD"
case "$_CWD_C" in
  *"/desks/"*) _rest="${CWD#*[/\\]desks[/\\]}"; SUBJECT="${_rest%%[/\\]*}";;
  *) SUBJECT="";;
esac

# ── hash_key: the fallback session key, and it MUST match everywhere ──────────────────────────────
# When the harness gives us no session id we key on the working directory instead. `shasum` does that
# on macOS and Linux and is ABSENT from Git Bash on Windows, where it produces an EMPTY key — so every
# window on that machine would collide on one flag, silently.
# ⚠ SHA-1 DELIBERATELY, NOT SHA-256: this must equal what `shasum` prints, or a machine that has
# shasum and a machine that does not would key the SAME folder differently. One writer and one reader
# disagreeing about the key is worse than having no key at all.
# ⚠ This snippet is IDENTICAL in every file that needs it (plan_flag, pm_flag, pm_persist, skill_anchor,
# skill_anchor_inject, statusline). Keep it that way — the next platform fix should land in one shape.
hash_key() {
  _hk="$(printf '%s' "$1" | shasum 2>/dev/null | cut -c1-12)"
  if [ -z "$_hk" ]; then
    _hk="$(printf '%s' "$1" | python3 -c 'import hashlib,sys; sys.stdout.write(hashlib.sha1(sys.stdin.buffer.read()).hexdigest())' 2>/dev/null | cut -c1-12)"
  fi
  printf '%s' "$_hk"
}

# Session key — MUST match numbers_flag.sh's derivation exactly (env id, else cwd hash).
if [ -n "$CLAUDE_CODE_SESSION_ID" ]; then KEY="sess-$CLAUDE_CODE_SESSION_ID"
elif [ -n "$CWD" ]; then KEY="cwd-$(hash_key "$CWD")"
else KEY=""; fi
FLAG="$HOME/.claude/run/numbers/numbers-$KEY.flag"

# ── THE NOTES ROOT. $LIFEHACK_ROOT first, then the persisted ~/.config/lifehack/brain-root. Nothing
# else — no guessing, no cwd, no glob. Mirrors shared/brain_root.py's first two steps.
notes_root() {
  _nr="${LIFEHACK_ROOT:-}"
  [ -n "$_nr" ] || _nr="$(cat "$HOME/.config/lifehack/brain-root" 2>/dev/null)"
  while [ "${_nr%/}" != "$_nr" ]; do _nr="${_nr%/}"; done
  case "$_nr" in
    ""|"/"|"$HOME") return 1 ;;
    # WINDOWS PATH FOLD: `/*` alone is POSIX-only -- a Windows absolute path (`D:\Notes\Brain` or
    # `D:/Notes/Brain`) does not start with `/`, so it fell through this case with no match and no
    # validation at all (a bare `case` has no default arm). `[A-Za-z]:*` catches both spellings.
    /*|[A-Za-z]:*) [ -d "$_nr" ] || return 1 ;;
    *) return 1 ;;
  esac
  printf '%s' "$_nr"
}

REASON=""

# ── ARM 1 — a subject folder that arms itself, named by the person, never by this repo.
# ⛔ THE DONOR HARDCODED TWO NAMES HERE, and they were two people's names — the author's finance and
# billing desks. Shipping that would have meant a stranger's tool quietly deciding that THEIR money
# lives in a folder named after somebody else, and doing nothing at all for the folder where it
# actually lives. The list is now the reader's: one folder name per line at
# <notes>/config/numbers-auto-arm, `#` comments allowed. No file means no auto-arm, which is the
# right default — the other two arms still work on day one, so this ships useful rather than inert.
if [ -n "$SUBJECT" ]; then
  _root="$(notes_root)" && {
    _list="$_root/config/numbers-auto-arm"
    if [ -f "$_list" ]; then
      # Exact whole-line match, comments and blanks skipped, so "cash" never matches "cashflow".
      while IFS= read -r _line || [ -n "$_line" ]; do
        _line="${_line%%#*}"
        _line="$(printf '%s' "$_line" | tr -d '[:space:]')"
        [ -n "$_line" ] || continue
        [ "$_line" = "$SUBJECT" ] && { REASON="auto (the $SUBJECT folder is on your list)"; break; }
      done < "$_list"
    fi
  }
fi

# ── ARM 2 — you said so. numbers_flag.sh owns the TTL; a flag on disk means armed.
[ -z "$REASON" ] && [ -n "$KEY" ] && [ -f "$FLAG" ] && REASON="numbers-mode armed"

# ── ARM 3 — the backstop, and it is deliberately narrow. A currency figure, a percentage, or a digit
# with an operator between it and another digit. Nothing looser: the loose version was measured and
# it is arm 1 and 2 that carry this, not the regex.
if [ -z "$REASON" ] && [ -n "$PROMPT" ]; then
  printf '%s' "$PROMPT" | grep -qE '(\$[0-9]|[0-9][0-9,.]*[[:space:]]*%|[0-9][[:space:]]*[*/+×÷][[:space:]]*[0-9])' 2>/dev/null && REASON="hard math token"
fi
[ -z "$REASON" ] && exit 0

printf '%s\n' "[NUMBERS CHECK (${REASON}) — added by the system, not typed by the person.]"
printf '%s\n' "If this turn involves any calculation, do not do the arithmetic in your head or in prose. Compute it with a tool — a Python snippet via Bash, or the spreadsheet's own formula when the data already lives in a sheet — and show the expression next to the result, so it can be checked."
printf '%s\n' "Never bend an input, round to something tidier, or work backwards from the number you were hoping for. Run it forwards and say so if the answer disagrees with the expectation. (A real money error on 2026-06-26 is why this line exists.)"
exit 0
