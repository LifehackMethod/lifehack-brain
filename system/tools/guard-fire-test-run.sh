#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: the guard fire-test engine (organism/label_checker.py + organism/label_manifest.yaml)
#      EXISTS and is CORRECT (verified this port: `python3 system/tools/organism/label_checker.py
#      check` runs clean against this repo's real settings.json and hooks), but nothing runs it
#      on a schedule and nothing reads its result. A guard silently downgraded from LIVE to
#      PARTIAL — registration drift, a violation slipping through, an allow-case wrongly
#      blocked — would be invisible until a human happened to run the checker by hand. This
#      runner is meant to fire the engine on a schedule and write the verdict into the SAME
#      durable finding store every other Hospital detector in this repo uses, so a downgrade
#      surfaces on the session-start banner (health_line.py).
# GUARDS: nothing — a producer. READ-ONLY except the machine-local fault ledger
#      (~/.config/lifehack/faults.json — never the notes root, so no shared-file race with
#      another machine). Every payload it fires is an INERT synthetic (label_checker.py's own
#      SAFETY note): the guard blocks before anything runs, so firing is side-effect-free.
# REDIRECT: manual run — `bash system/tools/guard-fire-test-run.sh`. Status artifact:
#      ~/.config/lifehack/guard-fire-test/last-run.json. Ledger row: producer
#      `guard-fire-test`.
#
# ⛔⛔⛔ PORTED 2026-08-14 FROM claudeops-config's system/tools/guard-fire-test-run.sh, AND
# SHIPPED UNDER CONSTRUCTION — READ THIS BEFORE TRUSTING A CLEAN RUN.
#   1. `verify-hooks.sh` — the donor's own combined fire-test + 2 native regression-suite
#      runner this script calls below — DOES NOT EXIST in this repo (confirmed absent; it is
#      not on this port's file list and belongs to a different category). Calling a script
#      that does not exist returns rc=127, which THIS SCRIPT's own `do_work()` already treats
#      correctly as "the tool itself is broken" (see the `[ "$rc" -gt 1 ]` branch below) — it
#      emits an honest ERROR finding rather than crashing or reporting a false GREEN. So this
#      runner is fully callable today and will correctly and loudly report itself broken until
#      `verify-hooks.sh` (or an equivalent that wraps `organism/label_checker.py check`) lands.
#   2. The donor's PRIMARY-MACHINE gate (`require_primary`, sourced from `machine-token.sh`) is
#      DROPPED, not translated — this product is one machine by design (see
#      `system/tools/ingest-run.lib.sh`'s own header for the identical drop, and
#      `shared/brain_root.py`'s residency rule). Port the FUNCTION; drop the machine-gate.
#   3. `notify-send.sh` moved from `system/tools/notify-send.sh` (donor path) to
#      `shared/notify/notify-send.sh` (this repo's real path, confirmed by listing `shared/`).
#   4. Machine-token derivation (`system/tools/machine-token.sh`) is excluded from this port —
#      this product is one machine by design. `MACHINE="local"` is the fixed constant every
#      other ported store in this repo already uses (`emit_finding.py`, `fault_ledger.py`, ...).
#   5. `OUT_DIR` moved from `~/.local/share/claudeops/${SUBSYSTEM_NAME}` to
#      `~/.config/lifehack/${SUBSYSTEM_NAME}` — this repo's already-established machine-local
#      config/state home (see `fault_ledger.py`'s own port note for the same move).
# ⚠ NOTHING SCHEDULES THIS YET. This repo has no cron/launchd wiring. Running it is a manual
# `bash system/tools/guard-fire-test-run.sh` until a scheduler exists to give it a cadence.
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail

SUBSYSTEM_NAME="guard-fire-test"
STALE_AFTER_HOURS="192"                            # weekly cadence (168h) + 24h slack
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$HOME/.config/lifehack/${SUBSYSTEM_NAME}"   # machine-local, OUTSIDE the notes root
STATUS_ARTIFACT="$OUT_DIR/last-run.json"
mkdir -p "$OUT_DIR" 2>/dev/null || true

LOCKDIR="/tmp/lifehack-${SUBSYSTEM_NAME}.lock"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -d "$LOCKDIR" ] && [ "$(( $(date +%s) - $(stat -f %m "$LOCKDIR" 2>/dev/null || echo 0) ))" -gt 900 ]; then
    rm -rf "$LOCKDIR"; mkdir "$LOCKDIR" 2>/dev/null || exit 0
  else
    echo "[$SUBSYSTEM_NAME] another run in progress — skip."; exit 0
  fi
fi

RC=1   # pessimistic: die before do_work returns -> rc stays non-zero (honest)
_on_exit() {
  printf '{"subsystem":"%s","rc":%s,"ts":"%s","stale_after_h":%s}\n' \
    "$SUBSYSTEM_NAME" "$RC" "$(date -u +%FT%TZ)" "$STALE_AFTER_HOURS" > "$STATUS_ARTIFACT" 2>/dev/null || true
  rm -rf "$LOCKDIR" 2>/dev/null || true
}
trap _on_exit EXIT INT TERM

# ── THE WORK ─────────────────────────────────────────────────────────────────
# The rule, applied: a FOUND-RESULT is SUCCESS; non-zero means THE TOOL BROKE.
#   verify-hooks rc=0   -> GREEN             -> found-result, return 0
#   verify-hooks rc=1   -> RED (a downgrade) -> found-result, return 0, Hospital carries the verdict
#   verify-hooks rc>1   -> the engine failed to run (incl. rc=127, "not found") -> return
#                          non-zero (broken tool) — see item 1 above; this is the live case today.
#   ledger write fails  -> return non-zero (a verdict nobody can read is no verdict)
# Why a RED does NOT exit non-zero: a future scheduler's breaker (once one exists) would
# auto-disable the very job that watches for downgrades if a RED counted as a crash, so the
# alarm would go dark exactly when it matters. The RED signal lives in Hospital
# (state/findings/guard-fire-test.<machine>.jsonl), which health_line.py's session-start
# banner reads.
do_work() {
  local out rc err_line guard_n scanned_n status_val
  set +e
  out="$(bash "$CODE_ROOT/system/tools/verify-hooks.sh" 2>&1)"; rc=$?
  set -e
  printf '%s\n' "$out"

  if [ "$rc" -gt 1 ]; then
    echo "[$SUBSYSTEM_NAME] verify-hooks itself FAILED to run (rc=$rc) — broken tool, not a finding." >&2
    echo "[$SUBSYSTEM_NAME] NOTE: verify-hooks.sh is not ported to this repo yet (see this script's" >&2
    echo "  own header, item 1) — this is the expected, honest result until it (or an equivalent" >&2
    echo "  wrapping organism/label_checker.py check) lands." >&2
    # Even a broken TOOL is Hospital-worthy: we could not verify guard health AT ALL this run,
    # which is strictly worse than a clean RED. scanned_n=0 is allowed here ONLY because
    # status=ERROR, never OK (emit_finding.py refuses scanned_n=0 paired with status=OK).
    # Best-effort: a notes-root hiccup on THIS call must not turn a real "broken tool" exit
    # into a hang or a second, different failure.
    python3 "$CODE_ROOT/system/tools/emit_finding.py" \
      --producer guard-fire-test --status ERROR --scanned-n 0 \
      --label job=guard-fire-test --label check=guard-integrity \
      --summary "verify-hooks.sh itself failed to run (rc=$rc) — guard health could not be verified this run" \
      --rc "$rc" >/dev/null 2>&1 || echo "[$SUBSYSTEM_NAME] emit_finding (broken-tool path) failed to write" >&2
    return "$rc"
  fi

  err_line=""
  [ "$rc" -ne 0 ] && err_line="$(printf '%s\n' "$out" | grep -E 'DOWNGRADE|FAIL|RESULT: RED' | tail -1)"

  # ── THE shell/CLI-emitted Hospital finding ──────────────────────────────────
  # Proof the CLI is real *reference* propagation, not decoration: this detector is bash, never
  # imports emit_finding.py, and goes through its OWN argparse CLI. `labels={job, check}` is the
  # finding's STABLE identity: one finding per DETECTOR (guard-fire-test's overall
  # guard-integrity result), never one per run, so the SAME condition fingerprints identically
  # run over run and a recurring downgrade is trackable. Per-run detail (which guard, the raw
  # verify-hooks tail) lives in `summary`, never in `labels`.
  guard_n="$(printf '%s\n' "$out" | grep -oE '[0-9]+ guard' | head -1 | grep -oE '[0-9]+')"
  scanned_n=$(( ${guard_n:-0} + 2 ))
  if [ "$rc" -eq 0 ]; then status_val=OK; else status_val=ERROR; fi
  python3 "$CODE_ROOT/system/tools/emit_finding.py" \
    --producer guard-fire-test --status "$status_val" --scanned-n "$scanned_n" \
    --label job=guard-fire-test --label check=guard-integrity \
    --summary "${err_line:-all guards + regression suites GREEN}" \
    --rc "$rc" >/dev/null 2>&1 || echo "[$SUBSYSTEM_NAME] emit_finding failed to write" >&2

  # Producer-liveness only — the verdict above is Hospital's job; this call takes no rc/err.
  python3 "$CODE_ROOT/system/tools/guard_fire_test_record.py"
  return $?
}

do_work && RC=0 || RC=$?

# Active failure-buzz: fires ONLY when the TOOL broke (RC!=0) — never for a RED guard, which
# is a found-result carried by the ledger + banner. No new ping channel added.
if [ "$RC" -ne 0 ]; then
  bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags warning --priority critical \
    --title "⚠️ ${SUBSYSTEM_NAME} failed" \
    --message "${SUBSYSTEM_NAME} could not run (rc=$RC). Guard fire-testing is DARK. Check $STATUS_ARTIFACT." 2>/dev/null || true
fi

echo "[$SUBSYSTEM_NAME] done (rc=$RC)."
exit "$RC"
