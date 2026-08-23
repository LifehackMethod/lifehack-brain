#!/bin/bash
# read_sop.sh — print an SOP to stdout AND stamp a session receipt proving it was read.
#
# WHY THIS EXISTS (2026-07-28, organism-audit S2.11):
#   "Read the SOP before you build X" was enforced by `inject_sop_before_build.sh`, a
#   UserPromptSubmit hook keyed on BUILD-INTENT LANGUAGE IN THE USER'S PROMPT. It watches what the
#   human types, not what the agent does — so it fires once at the top of a session and is silent
#   at the moment the agent actually edits a hook hours later. That is exactly how a hook got
#   edited on 2026-07-28 with the SOP unread. Its own header pre-authorised this escalation:
#   "a pointer, not a gate (escalate to a block only if this proves skippable in practice)."
#
#   THE RECEIPT IS NOT A CHECKBOX. It is stamped ONLY as a side effect of printing the SOP text to
#   stdout — i.e. into the model's context. You cannot earn the stamp without the rulebook passing
#   through the window, which is the actual goal. This is the `phase_gate` pattern from
#   system/parts/phase_gate.py: the completion stamp only CODE can write.
#
#   Honest limit: a determined agent could call this and not attend to the output. Nothing in a
#   text interface can force attention. What this DOES guarantee is that the text is present rather
#   than absent — which is the difference between a rule and a wish.
#
# Usage:
#   bash system/tools/read_sop.sh hook      # hook-sop.md + hook-contract.md (the mechanics)
#   bash system/tools/read_sop.sh --status  # show current receipts, stamp nothing
#
# PORTED (T9.7b, 2026-08-15) from claudeops-config: CODE_ROOT was a hardcoded
# `$HOME/claudeops-config`; it now resolves from this script's own location (git toplevel,
# falling back to stripping the known `system/tools` suffix), matching the pattern already
# used across this repo's ported hooks (e.g. announce_plan_write.sh) — never a hardcoded home.
set -uo pipefail

_HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
CODE_ROOT="$(cd "$_HERE" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$CODE_ROOT" ] || CODE_ROOT="${_HERE%/system/tools}"
RUN_DIR="$HOME/.claude/run/sop"

# Session key — payload session_id is not available here, so env first, then a cwd hash.
# Matches the convention in scratch_flag.sh / skill_anchor.sh so keys line up across the fleet.
# shasum is NOT guaranteed on PATH (Git Bash on Windows ships without it -- GitHub #82).
# Called bare, it emits "command not found" on every invocation AND `cut` returns an EMPTY
# string, so the receipt key collapses to a constant. The guard then never matches the receipt
# read_sop.sh wrote, and the result is a PERMANENT DENY with no way out.
# ⚠ THIS SNIPPET IS IDENTICAL IN system/tools/read_sop.sh AND system/hooks/guard_hook_sop_read.sh
# AND MUST STAY THAT WAY -- one writes the receipt, the other reads it. If the two ever compute
# the key differently, they disagree on EVERY machine that lacks shasum and the permanent deny
# comes straight back. Same rule as hash_key() elsewhere in this folder.
_hashcwd() {
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$PWD" | shasum | cut -c1-12
  else
    printf '%s' "$PWD" | cksum | tr -s ' ' '-' | cut -c1-12
  fi
}

KEY="${CLAUDE_CODE_SESSION_ID:-cwd-$(_hashcwd)}"

# ── the registry: SOP key -> the docs that must be in context ────────────────────────────
# To add a rung: add a case. The gate (guard_hook_sop_read.sh) reads the SAME key names.
docs_for() {
  case "$1" in
    hook) printf '%s\n' "$CODE_ROOT/system/sops/hook-sop.md" "$CODE_ROOT/system/hook-contract.md" ;;
    *)    return 1 ;;
  esac
}

if [ "${1:-}" = "--status" ]; then
  echo "session key: $KEY"
  if [ -d "$RUN_DIR" ]; then
    found=0
    for f in "$RUN_DIR"/*.receipt; do
      [ -e "$f" ] || continue
      found=1
      printf '  %s  %s\n' "$(basename "$f")" "$(cat "$f" 2>/dev/null)"
    done
    [ "$found" -eq 1 ] || echo "  (no receipts)"
  else
    echo "  (no receipts)"
  fi
  exit 0
fi

SOP="${1:-}"
if [ -z "$SOP" ] || ! docs_for "$SOP" >/dev/null 2>&1; then
  echo "usage: read_sop.sh <sop-key>   (known keys: hook)" >&2
  echo "       read_sop.sh --status" >&2
  exit 2
fi

# ── print every doc for this rung, in full, to STDOUT ────────────────────────────────────
missing=0
while IFS= read -r doc; do
  if [ ! -f "$doc" ]; then
    echo "ERROR: SOP doc missing: $doc" >&2
    missing=1
    continue
  fi
  echo "════════════════════════════════════════════════════════════════════════════════"
  echo "  ${doc#$CODE_ROOT/}"
  echo "════════════════════════════════════════════════════════════════════════════════"
  cat "$doc"
  echo
done < <(docs_for "$SOP")

# FAIL-CLOSED: if any doc could not be printed, do NOT stamp. A receipt must never certify a read
# that did not happen — that would rebuild the exact false-green this whole project exists to kill.
if [ "$missing" -ne 0 ]; then
  echo "REFUSING to stamp a receipt: at least one SOP doc could not be read." >&2
  exit 1
fi

mkdir -p "$RUN_DIR" 2>/dev/null
printf 'read_at=%s key=%s sop=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$KEY" "$SOP" \
  > "$RUN_DIR/$SOP.$KEY.receipt"

echo "────────────────────────────────────────────────────────────────────────────────"
echo "✅ SOP '$SOP' read + receipt stamped for this session ($KEY)."
echo "   Hook edits under system/hooks/ are now unblocked for this session."
echo "   Receipt: $RUN_DIR/$SOP.$KEY.receipt"
