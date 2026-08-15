#!/usr/bin/env bash
# email_summary_run.sh — watchdog runner for email_summary_sync.py (3.1 dead-man's tile)
#
# Wraps the janitor in an outer timeout; on timeout OR non-zero exit stamps a DEGRADED tile
# via `--emit-degraded --rc N`. The janitor itself writes UP on success — this runner only
# handles the FAILURE path (so success needs no extra tile write here).
#
# macOS note: `timeout` is a GNU coreutil absent on stock macOS; we prefer `gtimeout` (from
# `brew install coreutils`) if present, else fall back to a pure-bash watchdog that gives the
# SAME rc=124 semantics: janitor runs in the background, a killer subshell fires after
# TIMEOUT_SECS, and rc-based detection (wait() reports 128+signal → normalised to 124)
# distinguishes a watchdog kill from a clean exit. This ensures
# the janitor is ALWAYS bounded — no unbounded runs on stock macOS.
#
# Cron-safe: resolves all binaries by absolute path where possible. Minimal PATH assumption.
# Pass-through: all args forwarded to the janitor so a supervised run can pass --force etc.
#
# ⚖ PORT NOTE: donor's single-writer machine gate (a two-machine "designated writer only"
# arbitration via machine-token.sh) is DELETED, not translated — a student has one computer, so the
# concept this gate arbitrated between does not exist here. (The donor labelled this gate after one
# of its own machines by name; that is the same primary-machine election the other runners' port
# notes describe, stated here by ROLE because no machine is named in this repo.) The rest of this runner (timeout handling, tile
# stamping) is unchanged. ⚠ CORRECTED 2026-08-15 (T9.7d): this used to deny that DEST had any
# scheduler or cron scaffold — that's false, `system/tools/pulse.sh` is the live daemon and
# `system/tools/install-schedulers.sh` installs its entry. What's still true, and now for a
# different reason: this specific runner (the older v1-shaped watchdog wrapper) has no caller and
# is DELIBERATELY not in `system/pulse-config.md` — see that file's own "NOT ADDED" note beside
# `email-summary-write-run.sh`, which supersedes this file. Not an oversight; not wired on purpose.
#
# Usage (cron-safe, no args):
#   /path/to/email_summary_run.sh
# Usage (supervised / forced):
#   /path/to/email_summary_run.sh --force --verbose
# Usage (custom timeout):
#   TIMEOUT_SECS=600 /path/to/email_summary_run.sh

set -uo pipefail

# ── Timeout configuration ────────────────────────────────────────────────────
# 900s = 15 min; should be well above any single janitor run. Override via env.
TIMEOUT_SECS="${TIMEOUT_SECS:-900}"

# ── Resolve the repo/clone root from this script's own location ─────────────
# Resolves symlinks robustly: SCRIPT_DIR → shared/tools/ → ../../ = repo root.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
JANITOR="${REPO_ROOT}/shared/tools/email_summary_sync.py"

if [[ ! -f "${JANITOR}" ]]; then
    echo "[email-summary-run] ERROR: janitor not found at ${JANITOR}" >&2
    exit 2
fi

# ── Resolve Python — mirrors janitor's binary resolution pattern (1.1e) ─────
PYTHON="$(command -v python3 2>/dev/null \
    || echo /usr/bin/python3)"
# Prefer the versioned installer location that cron's minimal PATH misses
for _py in \
    "${HOME}/.local/bin/python3" \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    /usr/bin/python3; do
    if [[ -x "${_py}" ]]; then
        PYTHON="${_py}"
        break
    fi
done

# ── Resolve timeout binary (gtimeout preferred; plain timeout fallback) ──────
TIMEOUT_BIN=""
for _t in \
    /opt/homebrew/bin/gtimeout \
    /usr/local/bin/gtimeout \
    "$(command -v gtimeout 2>/dev/null || true)" \
    "$(command -v timeout 2>/dev/null || true)"; do
    if [[ -n "${_t}" && -x "${_t}" ]]; then
        TIMEOUT_BIN="${_t}"
        break
    fi
done

if [[ -z "${TIMEOUT_BIN}" ]]; then
    echo "[email-summary-run] WARNING: no timeout/gtimeout binary found;" \
         "using pure-bash watchdog (install coreutils via brew for the preferred path)" >&2
fi

# ── Run the janitor ──────────────────────────────────────────────────────────
JANITOR_RC=0

if [[ -n "${TIMEOUT_BIN}" ]]; then
    # Preferred path: GNU timeout/gtimeout — rc=124 on wall-clock kill.
    "${TIMEOUT_BIN}" "${TIMEOUT_SECS}" \
        "${PYTHON}" "${JANITOR}" "$@"
    JANITOR_RC=$?
else
    # Pure-bash watchdog fallback — same rc=124 semantics as GNU timeout.
    # Detection is rc-based: bash reports wait() rc as 128+signal when the process is killed,
    # so SIGTERM (15) → 143 and SIGKILL (9) → 137. Our killer subshell is the ONLY thing that
    # sends TERM/KILL to the janitor PID, so those rc values unambiguously mean watchdog fired.

    # Start the janitor in the background.
    "${PYTHON}" "${JANITOR}" "$@" &
    _janitor_pid=$!

    # Killer subshell: sleep, then terminate the janitor if still running.
    (
        /bin/sleep "${TIMEOUT_SECS}"
        if /bin/kill -0 "${_janitor_pid}" 2>/dev/null; then
            /bin/kill -TERM "${_janitor_pid}" 2>/dev/null || true
            # 5-second grace before escalating to SIGKILL.
            /bin/sleep 5
            /bin/kill -KILL "${_janitor_pid}" 2>/dev/null || true
        fi
    ) &
    _killer_pid=$!

    # Wait for the janitor; capture its real exit code.
    wait "${_janitor_pid}"
    JANITOR_RC=$?

    # rc 143 = killed by SIGTERM (128+15); rc 137 = killed by SIGKILL (128+9).
    # Both mean the watchdog fired — normalise to 124 to match GNU timeout semantics.
    if [[ "${JANITOR_RC}" -eq 143 || "${JANITOR_RC}" -eq 137 ]]; then
        JANITOR_RC=124
    fi

    # Reap the killer subshell if the janitor finished before the timeout fired.
    # Use disown before kill so bash removes it from its job table and wait(1) never
    # blocks on it — the killer's child sleep may still be running, which would cause
    # wait to hang even after the subshell itself receives SIGTERM.
    if /bin/kill -0 "${_killer_pid}" 2>/dev/null; then
        disown "${_killer_pid}" 2>/dev/null || true
        /bin/kill "${_killer_pid}" 2>/dev/null || true
    fi
fi

# ── FAILURE PATH: stamp DEGRADED tile ────────────────────────────────────────
# 3.1: on timeout (rc=124) or any non-zero exit, the runner calls --emit-degraded.
# The janitor writes UP on success — we never stomp a successful tile here.
if [[ "${JANITOR_RC}" -ne 0 ]]; then
    if [[ "${JANITOR_RC}" -eq 124 ]]; then
        REASON="timeout"
    else
        REASON="non-zero-exit"
    fi
    echo "[email-summary-run] janitor exited with rc=${JANITOR_RC} (${REASON})" \
         "— stamping DEGRADED tile via --emit-degraded" >&2
    # Best-effort tile write; if the Python call itself fails, we still propagate the original rc
    "${PYTHON}" "${JANITOR}" --emit-degraded --rc "${JANITOR_RC}" --reason "${REASON}" \
        2>&1 || echo "[email-summary-run] WARNING: --emit-degraded itself failed" >&2
fi

# ── Exit plumbing ─────────────────────────────────────────────────────────────
# Pulse-breaker-safe: exit 0 on clean success, non-zero only on real failure.
# rc=124 (timeout) is a real failure — surface it.
exit "${JANITOR_RC}"
