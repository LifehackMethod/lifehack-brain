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

LOCKDIR="${LIFEHACK_RUNNER_LOCK_ROOT:-/tmp}/claudeops-${SUBSYSTEM_NAME}.lock"   # LIFEHACK_RUNNER_LOCK_ROOT: TEST-ONLY seam (job-sim.sh)
. "$CODE_ROOT/system/tools/runner-lock.lib.sh" || { echo "FATAL: cannot source runner-lock.lib.sh" >&2; exit 1; }
# 5.9(h): the lock records its owner pid. A dead owner's lock is taken at once; a LIVE owner is a stand-down (75), never a 0;
# a lock that is present but unreadable is refused and named (1).
runner_lock_acquire "$LOCKDIR" 900 "$SUBSYSTEM_NAME" || exit $?

RC=1   # pessimistic: die before do_work returns -> rc stays non-zero (honest)
# 5.9(b): the artifact carries the VERDICT, because the row's check must test the verdict, never the exit code.
#   GREEN = every guard fired as expected · DOWNGRADE = a guard is weaker than it should be, NAMED in "named" (a found-result, rc 0)
#   ERROR = the engine itself did not run (rc != 0). The row's check accepts only GREEN or a named DOWNGRADE.
VERDICT="ERROR"; NAMED="verify-hooks did not complete"
_json_safe() { printf '%s' "$1" | tr -d '"\\' | tr '\n\r\t' '   ' | cut -c1-200; }
_on_exit() {
  printf '{"subsystem":"%s","rc":%s,"verdict":"%s","named":"%s","ts":"%s","stale_after_h":%s}\n' \
    "$SUBSYSTEM_NAME" "$RC" "$VERDICT" "$(_json_safe "$NAMED")" "$(date -u +%FT%TZ)" "$STALE_AFTER_HOURS" > "$STATUS_ARTIFACT" || echo "[$SUBSYSTEM_NAME] FAILED to write the status artifact $STATUS_ARTIFACT" >&2
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
  local out rc err_line
  set +e
  out="$(bash "$CODE_ROOT/system/tools/verify-hooks.sh" 2>&1)"; rc=$?
  set -e
  printf '%s\n' "$out"

  if [ "$rc" -gt 1 ]; then
    echo "[$SUBSYSTEM_NAME] verify-hooks itself FAILED to run (rc=$rc) — broken tool, not a finding." >&2
    echo "[$SUBSYSTEM_NAME] NOTE: verify-hooks.sh is not ported to this repo yet (see this script's" >&2
    echo "  own header, item 1) — this is the expected, honest result until it (or an equivalent" >&2
    echo "  wrapping organism/label_checker.py check) lands." >&2
    # 5.12(a): no findings-store write any more; the non-zero return is the failed run job-run.sh texts.
    return "$rc"
  fi

  err_line=""
  [ "$rc" -ne 0 ] && err_line="$(printf '%s\n' "$out" | grep -E 'DOWNGRADE|FAIL|RESULT: RED' | tail -1)"
  if [ "$rc" -eq 0 ]; then VERDICT="GREEN"; NAMED="all guards + regression suites GREEN"
  else VERDICT="DOWNGRADE"; NAMED="${err_line:-verify-hooks reported RED with no detail line}"; fi

  # 5.12(a): the verdict is no longer written to the retired findings store; the row check reads it from last-run.json.
  # Producer-liveness only — the verdict above is Hospital's job; this call takes no rc/err.
  python3 "$CODE_ROOT/system/tools/guard_fire_test_record.py"
  return $?
}

do_work && RC=0 || RC=$?

# Failure alerting (5.7): the scheduled chain owns it. A non-zero exit (the TOOL broke, never a RED guard) is a failed
# run for job-run.sh, which pushes ONE "Job down" under its two-misses rule, and the finding written above carries the
# verdict to the session line. This runner used to push by itself through notify-send.sh; that was a second,
# ungoverned alert path and a raw-curl call the door (install-schedulers.sh --check-row) refuses inside a job runner.
if [ "$RC" -ne 0 ]; then
  echo "[$SUBSYSTEM_NAME] FAILED (rc=$RC) — guard fire-testing is DARK. Status: $STATUS_ARTIFACT" >&2
fi

echo "[$SUBSYSTEM_NAME] done (rc=$RC)."
exit "$RC"
