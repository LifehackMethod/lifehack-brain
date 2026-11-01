#!/bin/bash
# receipt.sh — the long-gate RECEIPT of the skill-tester-rig (plan rule "long gates prove themselves by receipt",
# 2026-10-31; first user: card TR1.6). bash 3.2 + BSD tools.
#
# A gate run that takes minutes (bite.sh --rung N, later ladder.sh) cannot be re-run inside plan_retire's 120 s
# Verify timeout. So the run leaves a receipt, and the card's Verify checks the receipt fast against the CURRENT
# committed rig. A receipt from older code, or from a dirty tree, never passes.
#
#   receipt.sh write <gate> <result-line>
#       writes <RECEIPTS>/<gate>.receipt atomically, exactly 4 lines:
#         1  the result line, verbatim
#         2  `git rev-parse HEAD:<rig path>`, the rig folder's COMMITTED tree hash (or UNKNOWN-TREE <why>)
#         3  CLEAN-TREE if `git status --porcelain -- <rig path>` is empty, else DIRTY
#         4  an ISO-8601 UTC timestamp
#       A previous receipt is KEPT: hard-linked to <gate>.receipt.<UTC stamp> before the new one is renamed over
#       it (no moment without a receipt, never a silent overwrite). exit 0 written and read back · 1 not written.
#       ONLY bite.sh --rung N (later ladder.sh) calls this, from its UNGUARDED orchestrator, after the whole run.
#   receipt.sh write <gate> <result-line> --note <line>
#       the same, plus <RECEIPTS>/<gate>.note (one line, atomic; TR2.0b: actor-guard's gate caveat). `check` never
#       reads the note.
#   receipt.sh check <gate> <expected-line>
#       stdout is ALWAYS one line, `1` or `0` (never empty: plan_retire reads an empty stdout as the exit code).
#       `1` only if the receipt exists and is readable, has exactly 4 lines, line 1 == <expected-line> exactly,
#       line 2 == the CURRENT `rev-parse HEAD:<rig path>`, line 3 == CLEAN-TREE, AND the current rig tree is clean.
#       Otherwise `0` with the reason on stderr. exit 0 on `1`, 3 on `0`, 2 on usage (stdout still `0`).
#   receipt.sh dir [default]
#       print the receipts folder (realpath; `default` ignores the env override). guard.sh denies both.
#   receipt.sh --selftest
#       hermetic: a throwaway git repo + env overrides under ~/lifehack-scratch/skill-tester-rig/selftest-receipt/.
#       Last line 'SELFTEST receipt OK'.
#
# WHERE: ~/lifehack-scratch/skill-tester-rig-receipts/ — a SIBLING of the scratch root, never inside it. The write
# guard (guard.sh) allows the scratch root wholesale to every guarded run and the actor; this folder lies outside
# that allowance AND is explicitly denied after it, so no guarded process can mint or alter a receipt.
# Env (tests only): SKILL_TESTER_RECEIPTS (the folder), SKILL_TESTER_RECEIPT_RIG (the rig folder whose tree is
# hashed; default: this script's own folder). bite.sh --rung refuses to start with either set.
set -u

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_RECEIPTS="$HOME/lifehack-scratch/skill-tester-rig-receipts"
RECEIPTS="${SKILL_TESTER_RECEIPTS:-$DEFAULT_RECEIPTS}"
RIGDIR="${SKILL_TESTER_RECEIPT_RIG:-$SELF_DIR}"

realp() { python3 -I -B -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"; }
utc()   { date -u +%Y-%m-%dT%H:%M:%SZ; }

valid_gate() { printf '%s' "$1" | grep -Eqx '[A-Za-z0-9][A-Za-z0-9._-]*'; }

# tree_state: sets TREE (hash or "UNKNOWN-TREE <why>"), CLEAN (CLEAN-TREE|DIRTY), TREE_ERR (empty when both read)
tree_state() {
  local top pfx out rc
  TREE_ERR=""; CLEAN=DIRTY
  top="$(git -C "$RIGDIR" rev-parse --show-toplevel 2>&1)" || { TREE="UNKNOWN-TREE not-a-git-repo"; TREE_ERR="git: $top"; return 1; }
  pfx="$(git -C "$RIGDIR" rev-parse --show-prefix 2>&1)" || { TREE="UNKNOWN-TREE no-prefix"; TREE_ERR="git: $pfx"; return 1; }
  pfx="${pfx%/}"
  [ -n "$pfx" ] || { TREE="UNKNOWN-TREE rig-is-repo-root"; TREE_ERR="the rig folder is the repo root"; return 1; }
  out="$(git -C "$top" rev-parse --verify --quiet "HEAD:$pfx" 2>&1)"; rc=$?
  if [ $rc != 0 ] || [ -z "$out" ]; then TREE="UNKNOWN-TREE not-committed"; TREE_ERR="no committed tree at HEAD:$pfx ($out)"; return 1; fi
  TREE="$out"
  out="$(git -C "$top" status --porcelain -- "$pfx" 2>&1)"; rc=$?
  if [ $rc != 0 ]; then TREE_ERR="git status failed: $out"; return 1; fi
  [ -z "$out" ] && CLEAN=CLEAN-TREE
  DIRTY_LIST="$out"
  return 0
}

do_write() {
  local gate="$1" line="$2" d f tmp bak got
  valid_gate "$gate" || { echo "receipt: bad gate name '$gate'" >&2; return 1; }
  case "$line" in ""|*"
"*) echo "receipt: the result line must be one non-empty line" >&2; return 1 ;; esac
  tree_state || echo "receipt: WARNING $TREE_ERR (the receipt records ${TREE}, it can never check 1)" >&2
  mkdir -p "$RECEIPTS" || { echo "receipt: cannot create $RECEIPTS" >&2; return 1; }
  d="$(realp "$RECEIPTS")" || return 1
  f="$d/$gate.receipt"; tmp="$d/.$gate.receipt.tmp.$$"
  printf '%s\n%s\n%s\n%s\n' "$line" "$TREE" "$CLEAN" "$(utc)" > "$tmp" || { echo "receipt: cannot write $tmp" >&2; rm -f "$tmp"; return 1; }
  if [ -e "$f" ]; then
    bak="$f.$(date -u +%Y%m%dT%H%M%SZ)"
    [ -e "$bak" ] && bak="$bak-$$"
    ln "$f" "$bak" || { echo "receipt: cannot keep the previous receipt as $bak; NOT overwriting" >&2; rm -f "$tmp"; return 1; }
    echo "receipt: previous receipt kept as $bak" >&2
  fi
  mv -f "$tmp" "$f" || { echo "receipt: cannot rename $tmp to $f" >&2; rm -f "$tmp"; return 1; }
  got="$(sed -n 1p "$f")"
  [ "$got" = "$line" ] && [ "$(wc -l < "$f" | tr -d ' ')" = 4 ] || { echo "receipt: read-back of $f failed" >&2; return 1; }
  echo "receipt: wrote $f ($TREE $CLEAN)" >&2
  return 0
}

CHECK_SAID=""
say() { CHECK_SAID=1; echo "$1"; }
no() { say 0; echo "receipt: 0 — $*" >&2; exit 3; }

do_check() {
  local gate="$1" want="$2" f n l1 l2 l3
  valid_gate "$gate" || no "bad gate name '$gate'"
  f="$RECEIPTS/$gate.receipt"
  [ -f "$f" ] || no "no receipt at $f"
  [ -r "$f" ] || no "receipt unreadable: $f"
  n="$(wc -l < "$f" | tr -d ' ')" || no "receipt unreadable: $f"
  [ "$n" = 4 ] || no "receipt has $n lines, not 4: $f"
  l1="$(sed -n 1p "$f")"; l2="$(sed -n 2p "$f")"; l3="$(sed -n 3p "$f")"
  [ "$l1" = "$want" ] || no "result line differs: receipt '$l1' vs expected '$want'"
  tree_state || no "cannot read the current rig tree: $TREE_ERR"
  [ "$l2" = "$TREE" ] || no "stale receipt: it ran tree $l2, the committed rig tree is now $TREE"  # CMP-TREE
  [ "$l3" = CLEAN-TREE ] || no "the receipt's run was on a $l3 tree"                                 # CMP-RUNCLEAN
  [ "$CLEAN" = CLEAN-TREE ] || no "the rig tree is dirty now: $(printf '%s' "$DIRTY_LIST" | tr '\n' ';')"  # CMP-NOWCLEAN
  say 1
  exit 0
}

# ── selftest ────────────────────────────────────────────────────────────────────────────────────────────────
selftest() {
  export PYTHONDONTWRITEBYTECODE=1
  local T R RIG RC bad="" n=0 out
  T="$HOME/lifehack-scratch/skill-tester-rig/selftest-receipt/$(date +%s)-$$"
  R="$T/repo"; RIG="$R/sub/rig"; RC="$T/receipts"
  mkdir -p "$RIG" || { echo "SELFTEST receipt FAILED: cannot create $T"; return 1; }
  g() { git -C "$R" -c core.hooksPath=/dev/null -c commit.gpgsign=false -c user.name=rig-selftest -c user.email= "$@"; }
  g init -q || { echo "SELFTEST receipt FAILED: git init"; return 1; }
  echo one > "$RIG/a.txt"; echo top > "$R/top.txt"
  g add -A && g commit -q -m one || { echo "SELFTEST receipt FAILED: git commit"; return 1; }
  rx() { SKILL_TESTER_RECEIPTS="$RC" SKILL_TESTER_RECEIPT_RIG="$RIG" bash "$1" "${@:2}"; }   # rx <script> args
  me="$SELF_DIR/receipt.sh"
  expect() {  # expect <label> <want 0|1> <script> check <gate> <line>
    local lab="$1" want="$2" got; shift 2
    got="$(rx "$@" 2>"$T/err")"
    n=$((n+1))
    if [ "$got" = "$want" ]; then echo "  ok   $lab → $got ($(tr '\n' ' ' < "$T/err"))"
    else echo "  FAIL $lab → '$got', want $want ($(tr '\n' ' ' < "$T/err"))"; bad="$bad [$lab]"; fi
  }
  L="BITE rungX caught 2/2 fp 0/1 CLEAN"
  rx "$me" write rungX "$L" 2>>"$T/log" || bad="$bad [write-failed]"
  expect "matching receipt"                  1 "$me" check rungX "$L"
  expect "wrong line"                        0 "$me" check rungX "BITE FAILED caught 1/2 fp 0/1"
  expect "missing receipt"                   0 "$me" check rungNONE "$L"
  [ "$(wc -l < "$RC/rungX.receipt" | tr -d ' ')" = 4 ] || bad="$bad [not-4-lines]"
  # a second write keeps the first
  rx "$me" write rungX "$L" 2>>"$T/log" || bad="$bad [rewrite-failed]"
  ls "$RC"/rungX.receipt.2* >/dev/null 2>&1 || bad="$bad [previous-receipt-not-kept]"
  # dirty now (untracked file in the rig)
  echo junk > "$RIG/untracked.txt"
  expect "tree dirty now"                    0 "$me" check rungX "$L"
  # a receipt minted on a dirty tree, tree cleaned afterwards
  rx "$me" write rungD "$L" 2>>"$T/log"
  rm -f "$RIG/untracked.txt"
  [ "$(sed -n 3p "$RC/rungD.receipt")" = DIRTY ] || bad="$bad [dirty-not-recorded]"
  expect "receipt from a dirty run"          0 "$me" check rungD "$L"
  expect "clean again: matching"             1 "$me" check rungX "$L"
  # a change outside the rig does not stale the rig receipt
  echo top2 > "$R/top.txt"; g commit -q -am top2
  expect "commit outside the rig"            1 "$me" check rungX "$L"
  # unreadable / malformed
  cp "$RC/rungX.receipt" "$RC/rungU.receipt"; chmod 000 "$RC/rungU.receipt"
  expect "unreadable receipt"                0 "$me" check rungU "$L"
  chmod 600 "$RC/rungU.receipt"
  head -3 "$RC/rungX.receipt" > "$RC/rungM.receipt"
  expect "3-line receipt"                    0 "$me" check rungM "$L"
  # stale: the rig changes and is committed after the receipt
  echo two > "$RIG/a.txt"; g commit -q -am two
  expect "stale tree hash"                   0 "$me" check rungX "$L"
  # FAIL-FIRST: a broken copy without the tree-hash compare must PASS the stale case (so the case depends on it)
  sed 's/^.*# CMP-TREE$/  :/' "$me" > "$T/broken-receipt.sh"
  grep -q '# CMP-TREE$' "$T/broken-receipt.sh" && bad="$bad [broken-copy-not-made]"
  expect "fail-first: broken copy, stale"    1 "$T/broken-receipt.sh" check rungX "$L"
  sed 's/^.*# CMP-NOWCLEAN$/  :/' "$me" > "$T/broken2-receipt.sh"
  rx "$me" write rungY "$L" 2>>"$T/log"; echo junk > "$RIG/untracked.txt"
  expect "fail-first: no now-clean compare"  1 "$T/broken2-receipt.sh" check rungY "$L"
  expect "  …and the real copy refuses it"   0 "$me" check rungY "$L"
  rm -f "$RIG/untracked.txt"
  # stdout is never empty, even on a usage error
  out="$(bash "$me" check 2>"$T/usage.err")"; [ "$out" = 0 ] || bad="$bad [usage-stdout-'$out']"
  # a GUARDED process cannot write a receipt (guard.sh profile; scratch allowance deliberately covering the folder)
  if bash "$SELF_DIR/guard.sh" available; then
    local P="$T/guard.sb" RCR; RCR="$(realp "$RC")"
    SKILL_TESTER_RECEIPTS="$RCR" bash "$SELF_DIR/guard.sh" profile RCPTST "$(realp "$T")" /x/rig /x/standin > "$P" \
      || bad="$bad [profile-failed]"
    SKILL_TESTER_RECEIPTS="$RCR" SKILL_TESTER_RECEIPT_RIG="$RIG" TMPDIR="$T" \
      /usr/bin/sandbox-exec -f "$P" /bin/bash "$me" write rungG "$L" > "$T/guarded.out" 2>&1
    local grc=$?
    if [ $grc != 0 ] && grep -q "Operation not permitted" "$T/guarded.out" && [ ! -e "$RCR/rungG.receipt" ] && ! ls "$RCR"/.rungG.* >/dev/null 2>&1; then
      echo "  ok   guarded write denied (rc=$grc, no receipt)"
    else echo "  FAIL guarded write landed or succeeded (rc=$grc)"; bad="$bad [guarded-write-not-denied]"; fi
    # control: the same profile lets that process write to scratch beside the folder (the deny is specific)
    /usr/bin/sandbox-exec -f "$P" /bin/bash -c ': > "$1"' _ "$T/guard-control.txt" > "$T/guarded-ctl.out" 2>&1
    [ -f "$T/guard-control.txt" ] && echo "  ok   control: same profile writes scratch" || bad="$bad [guard-control-write-failed]"
    # fail-first: the explicit receipts deny stripped -> the guarded write lands (the deny is what bites)
    grep -v '; receipts-deny$' "$P" > "$T/guard-nodeny.sb"
    SKILL_TESTER_RECEIPTS="$RCR" SKILL_TESTER_RECEIPT_RIG="$RIG" TMPDIR="$T" \
      /usr/bin/sandbox-exec -f "$T/guard-nodeny.sb" /bin/bash "$me" write rungG "$L" > "$T/guarded-nodeny.out" 2>&1
    [ -e "$RCR/rungG.receipt" ] && echo "  ok   fail-first: without the receipts deny the write lands" \
      || bad="$bad [fail-first-nodeny-did-not-land]"
  else
    bad="$bad [sandbox-unavailable]"
  fi
  echo "selftest dir: $T ($n checks)"
  if [ -z "$bad" ]; then rm -rf "$R"; echo "SELFTEST receipt OK"; return 0; fi
  echo "SELFTEST receipt FAILED:$bad"; return 1
}

case "${1:-}" in
  write) if [ $# = 5 ] && [ "$4" = --note ]; then
           # TR2.0b: an optional NOTE beside the receipt (<gate>.note, one line, atomic). The 4-line receipt, and so
           # `check`, are unchanged; the note carries what a reader must know, e.g. actor-guard's gate caveat
           do_write "$2" "$3" || exit 1
           case "$5" in ""|*"
"*) echo "receipt: the note must be one non-empty line" >&2; exit 1 ;; esac
           nd="$(realp "$RECEIPTS")" && printf '%s\n' "$5" > "$nd/.$2.note.tmp.$$" && mv -f "$nd/.$2.note.tmp.$$" "$nd/$2.note" \
             || { echo "receipt: cannot write the note $nd/$2.note" >&2; exit 1; }
           echo "receipt: wrote note $nd/$2.note" >&2; exit 0
         fi
         [ $# = 3 ] || { echo "usage: receipt.sh write <gate> <result-line> [--note <line>]" >&2; exit 2; }
         do_write "$2" "$3"; exit $? ;;
  check) trap '[ -n "$CHECK_SAID" ] || echo 0' EXIT
         [ $# = 3 ] || { say 0; echo "usage: receipt.sh check <gate> <expected-line>" >&2; exit 2; }
         do_check "$2" "$3" ;;
  dir) if [ "${2:-}" = default ]; then realp "$DEFAULT_RECEIPTS"; else realp "$RECEIPTS"; fi ;;
  --selftest) selftest; exit $? ;;
  *) echo "usage: receipt.sh write <gate> <line> | check <gate> <line> | dir [default] | --selftest" >&2; exit 2 ;;
esac
