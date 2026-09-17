#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: K6-DESIGN-SPEC.md §3 — the checkin->save chain needs a session-scoped carrier for "checkin
#      just confirmed this project" that save can read without re-deriving it, WITHOUT that read ever
#      being able to block save (R9/R34: advisory/informational only, never a hard block). A hook
#      cannot do this safely (see guard_step_gate.sh's own v1-SCOPE note on why a needs/returns-driven
#      hook wired to save would risk exactly that hard block) — this is a plain CLI shim over the
#      shared flag.sh library instead, the same shape as pm_flag.sh/skill_anchor.sh: called directly
#      from a skill's own markdown-embedded shell (LAW 1 — code owns the mechanical perimeter, not
#      prose the model must remember, skill-building-sop.md F11), never a hook, never wired into
#      settings.json/hooks.json, so it structurally cannot deny anything.
# GUARDS: nothing — a receipt writer/reader. `write` always exits 0 (nothing to guard against).
#      `read` exits 0 only when a receipt exists, is unexpired, AND every requested field is
#      non-empty; it exits 1 (never denies a tool call — its caller decides what a non-zero exit
#      means) on ABSENT / EXPIRED / INVALID (a corrupt or partially-written receipt), printing which
#      on stdout so a caller can tell the three apart without parsing stderr.
# REDIRECT: the caller (a skill's own phase file) decides what a non-zero `read` means — for the
#      checkin->save seam specifically, K6 §3's ruling is "save's existing ask-fallback runs
#      unchanged", never a block.
# SIGNPOST: K6-DESIGN-SPEC.md §3 (this seam's design) · system/hooks/lib/flag.sh (the shared
#      mechanic — key derivation, TTL expiry) · .claude/skills/checkin/phases/3-propose.md (the one
#      producer in v1) · .claude/skills/save/phases/session-close.md SC-0 (the one consumer in v1) ·
#      system/hooks/tests/test_checkin_save_seam.sh (the seam test, incl. the proven-fail case).
# UPDATED: 2026-09-17 (new — K6, enforcement-layer Phase 2.)
# ─────────────────────────────────────────────────────────────────────────────
#   step_receipt.sh write <prefix> field=value [field=value ...]   # producer: record a receipt
#   step_receipt.sh read  <prefix> <field> [<field> ...]           # consumer: read it back, or fail
# Prefix is the producer's own name (K6 §3: checkin writes prefix "checkin") — NOT the same axis as
# guard_step_gate.sh's convention of keying a receipt by the NEED's name; this script only ever
# implements the direct producer/consumer pair a skill's own phase file names explicitly, never a
# register lookup.
# exit 0 = ok · 1 = usage/arg error, or (read) ABSENT/EXPIRED/INVALID · 2 = unknown verb
# ─────────────────────────────────────────────────────────────────────────────

set +e

_SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
_LIB="$_SELF_DIR/lib/flag.sh"
if [ ! -f "$_LIB" ]; then
  echo "step_receipt.sh: FATAL — shared library missing at $_LIB (cannot write/read a receipt)" >&2
  exit 1
fi
# shellcheck source=lib/flag.sh
. "$_LIB" || { echo "step_receipt.sh: FATAL — shared library at $_LIB failed to load" >&2; exit 1; }
for _fn in flag_init flag_write flag_get flag_ttl_expired; do
  command -v "$_fn" >/dev/null 2>&1 || { echo "step_receipt.sh: FATAL — shared library at $_LIB is missing $_fn() (corrupt)" >&2; exit 1; }
done

TTL_HOURS="${STEP_RECEIPT_TTL_HOURS:-12}"

case "$1" in
  write)
    if [ -z "$2" ]; then echo "write: <prefix> required" >&2; exit 1; fi
    PREFIX="$2"; shift 2
    flag_init step-receipts "$PREFIX"
    flag_write "$@" "armed_at=$NOW" "session=$CLAUDE_CODE_SESSION_ID"
    echo "RECEIPT WRITTEN: $PREFIX (session ${CLAUDE_CODE_SESSION_ID:-none})"
    ;;
  read)
    if [ -z "$2" ]; then echo "read: <prefix> required" >&2; exit 1; fi
    PREFIX="$2"; shift 2
    flag_init step-receipts "$PREFIX"
    if [ ! -f "$FLAG" ]; then
      echo "ABSENT"
      exit 1
    fi
    if flag_ttl_expired $(( TTL_HOURS * 3600 )); then
      echo "EXPIRED"
      exit 1
    fi
    MISSING=0
    for f in "$@"; do
      v="$(flag_get "$f")"
      [ -n "$v" ] || MISSING=1
    done
    if [ "$MISSING" -eq 1 ]; then
      echo "INVALID"
      exit 1
    fi
    for f in "$@"; do
      printf '%s=%s\n' "$f" "$(flag_get "$f")"
    done
    exit 0
    ;;
  *)
    echo "usage: step_receipt.sh write <prefix> field=value... | read <prefix> field..." >&2
    exit 2
    ;;
esac
