#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: B4.1 (enforcement-layer Phase 2) — the fleet of 50+ guards fires constantly but leaves no
#      durable trace of WHAT fired, WHEN, or WHAT it decided. Nobody can answer "did guard X ever
#      run this week" without re-deriving it from scratch. This is that trace: a single sourced
#      library, called via an EXIT trap from every hook entry point.
# GUARDS: nothing. This is a SOURCED OBSERVER, never a hook itself. It has no opinion on any tool
#      call and must NEVER be able to change one. See FAIL_POSTURE.
# REDIRECT: n/a — nothing is blocked here.
# SIGNPOST: design + verify recipe in the B4.1 build report (session scratchpad `B4.1-design.md`,
#      `B4.1-report.md`); the plan is `_ClaudeOps/plans/enforcement-layer.phase-2.plan.md` PHASE B4.
#      Change the field shape or journal path there first, then here.
# FAIL_POSTURE: SILENT-DEGRADE, deliberately the OPPOSITE of a guard's fail-closed posture. A guard
#      that can't decide must deny; a journal that can't write must vanish without a trace, because
#      the one invariant that must hold for EVERY caller of this file, unconditionally, is: sourcing
#      it, or calling `lhb_journal_fire`, must NEVER change the caller's own exit code, stdout, or
#      stderr — not even by one stray byte. A logging shim that can flip a deny into an allow is
#      worse than no logging shim.
# UPDATED: 2026-09-15
# ─────────────────────────────────────────────────────────────────────────────
#
# Contract for callers (every system/hooks/*.sh entry point + system/tools/mirror_line.sh):
#
#   . "$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/lib/journal.sh" 2>/dev/null || \
#     lhb_journal_fire() { :; }
#   trap 'lhb_journal_fire "$?" "<hook-file-name>" "<Event>" "<matcher-or-empty>" 2>/dev/null || true' EXIT
#
# The two-line pattern is deliberate:
#   - The `|| lhb_journal_fire() { :; }` fallback means a MISSING or BROKEN lib file still leaves a
#     valid (no-op) function defined, so the later `trap` line never hits "command not found" (which
#     bash would otherwise print to the hook's own stderr — exactly the kind of stray byte this file
#     exists to never produce).
#   - The `trap '... || true' EXIT` wrapping is the load-bearing safety line. Bash preserves a
#     script's ORIGINAL exit code through an EXIT trap regardless of what the trap's own commands
#     return (verified empirically, both with and without `set -uo pipefail`) — UNLESS the trap
#     itself calls `exit` with a different code. This file never calls `exit`. The outer `|| true`
#     is a second, independent line of defense: it guarantees the trap's own reported status is
#     always 0, so nothing here can ever interact badly with a caller's `set -e`-alikes (none of the
#     six current `set -uo pipefail` hooks trip in testing, but the guarantee should not depend on
#     today's set of callers).
#   - `2>/dev/null` on the trap invocation catches the one remaining leak path: an unset variable
#     reference under `set -u` prints to stderr even though it does not change $?. Every variable in
#     this file is defaulted with `${VAR:-}`, but the redirect is kept as a second, independent net.
#
# Fields written per line (JSONL), best-effort per B4.1's field list:
#   ts          — unix seconds (integer; one `date +%s` call, see cost note below)
#   hook        — the hook's own file name, passed in literally by the caller (zero-cost, no parsing)
#   event       — the hook's registered event, passed in literally (PreToolUse/PostToolUse/
#                 UserPromptSubmit/SessionStart/Stop/etc.) — a hook registered under more than one
#                 event (one case: guard_checkin_needs_project.sh) carries both, "+"-joined.
#   matcher     — the registered matcher string if any (e.g. "Bash", "Write|Edit"), else ""
#   decision    — derived from event + exit code only (see lhb_journal_decision below); this is a
#                 best-effort classification, not a re-parse of the guard's own deny JSON — the
#                 journal never re-reads a hook's stdout/stderr, because touching that stream at all
#                 is the one thing this file must never do.
#   exit_code   — the real, unmodified "$?" the caller's trap captured
#   session_id  — from $CLAUDE_CODE_SESSION_ID if the platform set it (env var, not a stdin re-parse
#                 — free, no subprocess); sanitized to [A-Za-z0-9_-] before going in the JSON line
#
# Cost note (measured this session, this machine, arm64 macOS, bash 3.2.57):
#   - `printf '...' >> file` from an already-running bash: ~0.057 ms/append (negligible).
#   - `date +%s` via command substitution from an already-running bash: ~2.6 ms/call, measured
#     10x50 loop, machine not idle (mode 9 caveat carried forward). This is the one subprocess this
#     file spawns per fire. The design scout's piggyback-on-the-existing-python3-stdin-parse idea
#     (B4.1-design.md) was NOT taken: it requires editing the decision-relevant python3 block inside
#     each of the 56 hooks that has one, and this build judged that surface too large and too close
#     to the decision path for a B4.1-scoped change, given the prime directive (instrumentation must
#     never change a decision). The `date` cost is spent instead, and B4.1-report.md carries the
#     real measured overhead against the ≤61.35 ms ceiling rather than asserting the trade was free.

lhb_journal_fire() {
    # $1=exit_code $2=hook-name $3=event $4=matcher (all optional; every use below is defaulted)
    if [ "${LHB_JOURNAL_DISABLE:-}" = "1" ]; then
        return 0
    fi

    local _rc _hook _event _matcher _journal _dir _ts _decision _sid

    _rc="${1:-}"
    _hook="${2:-unknown}"
    _event="${3:-unknown}"
    _matcher="${4:-}"

    _journal="${LHB_JOURNAL_PATH:-${HOME:-/tmp}/.claude/run/fire-journal.jsonl}"

    case "$_event" in
        PreToolUse*)
            case "$_rc" in
                0) _decision="allow" ;;
                2) _decision="deny" ;;
                1) _decision="deny" ;;
                "") _decision="unknown" ;;
                *) _decision="error" ;;
            esac
            ;;
        PostToolUse)
            if [ "$_rc" = "0" ]; then _decision="none"; else _decision="error"; fi
            ;;
        UserPromptSubmit|SessionStart)
            if [ "$_rc" = "0" ]; then _decision="inject"; else _decision="error"; fi
            ;;
        Stop)
            if [ "$_rc" = "0" ]; then _decision="none"; else _decision="error"; fi
            ;;
        *)
            if [ "$_rc" = "0" ]; then _decision="allow"; else _decision="deny"; fi
            ;;
    esac

    _sid="${CLAUDE_CODE_SESSION_ID:-}"
    _sid="${_sid//[^A-Za-z0-9_-]/}"

    _hook="${_hook//[^A-Za-z0-9_.-]/}"
    _event="${_event//[^A-Za-z0-9_+.|-]/}"
    _matcher="${_matcher//[^A-Za-z0-9_+.|-]/}"
    case "$_rc" in
        ''|*[!0-9-]*) _rc=-1 ;;
    esac

    _ts="$(date +%s 2>/dev/null)"
    case "$_ts" in
        ''|*[!0-9]*) _ts=0 ;;
    esac

    _dir="${_journal%/*}"
    if [ "$_dir" != "$_journal" ]; then
        mkdir -p "$_dir" 2>/dev/null
    fi

    # NOTE: 2>/dev/null must come BEFORE the >>"$_journal" append target in this redirection list.
    # Bash sets up redirections left-to-right; if the append target itself fails to open (unwritable
    # dir, disk full), the resulting error is written to whatever fd 2 currently is AT THAT POINT.
    # With 2>/dev/null first, fd 2 is already /dev/null before the failing >> is attempted, so the
    # "Permission denied" bash prints on a failed open is swallowed instead of leaking to the real
    # caller's stderr. Verified empirically — the reverse order leaks the message. This is exactly
    # the kind of stray byte the FAIL_POSTURE note above promises never happens.
    printf '{"ts":%s,"hook":"%s","event":"%s","matcher":"%s","decision":"%s","exit_code":%s,"session_id":"%s"}\n' \
        "$_ts" "$_hook" "$_event" "$_matcher" "$_decision" "$_rc" "$_sid" 2>/dev/null >>"$_journal"

    return 0
}
