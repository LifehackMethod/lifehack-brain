#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# fault-proposer-run.sh — the runner for `fault_proposer.py`.
#
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: `fault_proposer.py` is the first machine reader of this repo's failure signals — it
#      grades open faults INSTANCE / SUBSYSTEM / ORGANISM, cites the evidence that chose the
#      altitude, and refuses to propose anything it cannot cite. A tool nothing calls is
#      exactly as useful as a tool that does not exist — this wrapper is what calls it.
# GUARDS: nothing. It is a PRODUCER and a READ-ONLY one — `fault_proposer.py` writes nothing,
#      ever, by design ("it PROPOSES; the human gate is the product"). This wrapper must never
#      gain a remediation step. Hospital DETECTS and RANKS; it never REMEDIATES.
# REDIRECT: proposal text -> $OUT_DIR/last-proposal.txt (machine-local, survives reboot,
#      unlike /tmp) · status tile -> <brain>/state/status/fault-proposer-<machine>.json (when a
#      notes root is configured; see item 3 below for what happens when it is not).
#
# ⛔⛔⛔ PORTED 2026-08-14 FROM claudeops-config's system/tools/fault-proposer-run.sh, AND
# GENERALISED — READ THIS BEFORE CHANGING A PATH OR A RETURN.
#   1. The donor's machine-token derivation (`system/tools/machine-token.sh`) is excluded from
#      this port — one machine by design. `MACHINE="local"`, the fixed constant every other
#      ported store in this repo already uses.
#   2. `notify-send.sh` moved from `system/tools/notify-send.sh` (donor path) to
#      `shared/notify/notify-send.sh` (this repo's real path).
#   3. The status tile write moved from the donor's `emit_status.py` CLI (confirmed absent from
#      this repo — no emit_status.py, no Hospital status-tile writer ported here as of this
#      task) to a MINIMAL inline JSON writer, matching the same "no shared emit_status.py yet"
#      posture `backlog-health.py` (already shipped in this repo) documents for its own tile
#      write. The tile lands under the resolved brain root (`shared/brain_root.py`); with no
#      root configured, the tile write is skipped (not guessed at) and only the machine-local
#      artifacts (`$OUT_DIR/last-run.json`, `last-proposal.txt`) are written — this script still
#      runs the proposer and records the verdict either way.
#   4. `DRIVE`/`TILE` moved off a hardcoded personal cloud-drive path onto the resolved brain
#      root, same resolver every other ported store in this repo uses.
#   5. The donor's PRIMARY-MACHINE gate never existed on this script (it had none to drop) —
#      confirmed by re-reading the donor file; noted here only so a future editor does not
#      "restore" one that was never there.
#
# ⚠ NOTHING SCHEDULES THIS YET. This repo has no cron/launchd wiring. Running it is a manual
# `bash system/tools/fault-proposer-run.sh` until a scheduler exists to give it a cadence.
#
# ⚖ THE EXIT-CODE CONTRACT — STATED, NOT INFERRED. Read this before changing a return.
#      exit 0 — THE PROPOSER RAN. This covers ALL THREE of: proposals were emitted · there
#               were no open faults · the proposer REFUSED for want of citable evidence.
#               **A refusal is a CORRECT outcome, not a failure** — refusing to emit an
#               uncited proposal is the behaviour the tool exists to have.
#      exit 1 — THE PROPOSER ITSELF BROKE: crash, import error, unreadable ledger.
#
#    ⚠ The proposer's OWN rc is preserved separately in the tile as `proposer_rc`, so
#    collapsing three outcomes into one exit does NOT lose the distinction — the tile's
#    `verdict` field says which of the three happened. Never re-encode that in the exit code.
#
#    ⚠ VERIFIED AGAINST THE ACTUAL PORTED CODE (do not trust a docstring over the code —
#    the donor's own fault_proposer.py docstring claimed "prints a refusal and exits 2"; it
#    does not, `main()` returns 0 unconditionally, confirmed by reading this port's own
#    fault_proposer.py). This wrapper treats ANY non-zero from the proposer as a genuine
#    break, and does not special-case 2.
# ─────────────────────────────────────────────────────────────────────────────
set -eo pipefail

SUBSYSTEM_NAME="fault-proposer"
STALE_AFTER_HOURS="30"                             # daily cadence + 6h slack before it alarms
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$HOME/.config/lifehack/${SUBSYSTEM_NAME}"
PROPOSAL_TXT="$OUT_DIR/last-proposal.txt"
STATUS_ARTIFACT="$OUT_DIR/last-run.json"
mkdir -p "$OUT_DIR" 2>/dev/null || true

MACHINE="local"   # this product is one machine by design — see the header's item 1.

RC=1                                               # pessimistic: a death before do_work stays a failure
VERDICT="did-not-run"
PROPOSER_RC=-1
FAULT_COUNT=0

# ── The status trap: fires on EVERY exit path, not just the happy one ────────
# A FUNCTION trap, never a single-quoted string trap — a string trap's `local` refs are out
# of scope when it fires and die under `set -u`, so cleanup silently never runs.
_on_exit() {
  local rc=$?
  local st="OK"
  [ "$rc" -ne 0 ] && st="ERROR"
  printf '{"rc":%s,"proposer_rc":%s,"verdict":"%s","faults":%s,"ts":"%s"}\n' \
    "$rc" "$PROPOSER_RC" "$VERDICT" "$FAULT_COUNT" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    > "$STATUS_ARTIFACT" 2>/dev/null || true
  # The notes-root tile — best-effort, minimal, matching backlog-health.py's own "no shared
  # emit_status.py yet" posture (see header item 3). Skipped entirely (never guessed at) when
  # no brain root is configured; the machine-local artifact above still landed either way.
  python3 - "$CODE_ROOT" "$st" "$rc" "$VERDICT" "$FAULT_COUNT" "$PROPOSER_RC" "$SUBSYSTEM_NAME" "$STALE_AFTER_HOURS" "$MACHINE" <<'PYEOF' 2>/dev/null || true
import sys, os, json, time
code_root, status, rc, verdict, faults, proposer_rc, name, stale_h, machine = sys.argv[1:10]
sys.path.insert(0, os.path.join(code_root, "shared"))
try:
    from brain_root import resolve_brain_root
    _src, root = resolve_brain_root()
except Exception:
    root = None
if not root:
    sys.exit(0)
lt = time.localtime(); off = time.strftime("%z", lt)
off = (off[:3] + ":" + off[3:]) if off else "+00:00"
last_run = time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off
tile = {
    "schema_version": 1, "pulse_job": name, "emit_mode": "manual",
    "stale_after_s": int(stale_h) * 3600, "last_run": last_run, "rc": int(rc), "status": status,
    "summary": f"{verdict} ({faults} open fault(s); proposer rc={proposer_rc})",
    "proposer_rc": int(proposer_rc), "verdict": verdict, "faults": int(faults),
}
out_path = os.path.join(root, "state", "status", f"{name}-{machine}.json")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
tmp = out_path + ".tmp"
json.dump(tile, open(tmp, "w"), indent=2)
os.replace(tmp, out_path)
PYEOF
  exit "$rc"
}
trap _on_exit EXIT INT TERM

do_work() {
  local out prc
  # `|| prc=$?` keeps set -e quiet and captures the real code.
  out="$(/usr/bin/python3 "$CODE_ROOT/system/tools/fault_proposer.py" 2>&1)" && prc=0 || prc=$?
  PROPOSER_RC=$prc
  printf '%s\n' "$out" > "$PROPOSAL_TXT" 2>/dev/null || true

  if [ "$prc" -ne 0 ]; then
    VERDICT="proposer-BROKE"
    echo "[$SUBSYSTEM_NAME] fault_proposer.py exited $prc — this is a real break, not a refusal." >&2
    printf '%s\n' "$out" >&2
    return 1
  fi

  # Classify what actually came back. These three are all exit 0 — see the contract above.
  if printf '%s' "$out" | grep -q "^No open faults"; then
    VERDICT="no-open-faults"
  elif printf '%s' "$out" | grep -q "REFUSED"; then
    VERDICT="refused-no-citable-evidence"
  else
    VERDICT="proposals-emitted"
  fi
  FAULT_COUNT="$(printf '%s' "$out" | sed -n 's/^\([0-9][0-9]*\) open fault(s).*/\1/p' | head -1)"
  [ -z "$FAULT_COUNT" ] && FAULT_COUNT=0

  echo "[$SUBSYSTEM_NAME] $VERDICT — $FAULT_COUNT open fault(s). Proposal text: $PROPOSAL_TXT"
  return 0
}

do_work && RC=0 || RC=$?

# Active failure-buzz: a hard break pages now rather than waiting for a future breaker.
# ⚠ Deliberately NOT fired for a refusal or for a fault count — those are the tool WORKING.
# Hospital ranks; it does not nag. The tile + the session-start line are the routine surface.
if [ "$RC" -ne 0 ]; then
  bash "$CODE_ROOT/shared/notify/notify-send.sh" --source "$SUBSYSTEM_NAME" --tags warning --priority critical \
    --title "⚠️ fault-proposer failed" \
    --message "fault_proposer.py itself broke (rc=$PROPOSER_RC). The system's fault reader is down. Check $PROPOSAL_TXT." 2>/dev/null || true
fi

echo "[$SUBSYSTEM_NAME] done (rc=$RC)."
exit "$RC"
