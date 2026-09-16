#!/bin/bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: B4.1 (enforcement-layer Phase 2) — the fleet of 50+ guards fires constantly but leaves no
#      durable trace of WHAT fired, WHEN, or WHAT it decided. Nobody can answer "did guard X ever
#      run this week" without re-deriving it from scratch. This is that trace: a single sourced
#      library, called via an EXIT trap from every hook entry point.
#      B4.3 (2026-09-16) added rotation + a hard disk cap — the technical lead's ship condition
#      was "no new unbounded state store." Without this, fire-journal.jsonl grows forever.
# GUARDS: nothing. This is a SOURCED OBSERVER, never a hook itself. It has no opinion on any tool
#      call and must NEVER be able to change one. See FAIL_POSTURE.
# REDIRECT: n/a — nothing is blocked here.
# SIGNPOST: design + verify recipe in the B4.1 build report (session scratchpad `B4.1-design.md`,
#      `B4.1-report.md`); the plan is `_ClaudeOps/plans/enforcement-layer.phase-2.plan.md` PHASE B4.
#      Rotation design/verify: `journal-rotation-report.md` (Drive, enforcement-layer project).
#      Change the field shape or journal path there first, then here.
# FAIL_POSTURE: SILENT-DEGRADE, deliberately the OPPOSITE of a guard's fail-closed posture. A guard
#      that can't decide must deny; a journal that can't write must vanish without a trace, because
#      the one invariant that must hold for EVERY caller of this file, unconditionally, is: sourcing
#      it, or calling `lhb_journal_fire`, must NEVER change the caller's own exit code, stdout, or
#      stderr — not even by one stray byte. A logging shim that can flip a deny into an allow is
#      worse than no logging shim. Rotation inherits this exactly: a rotation that fails (read-only
#      dir, a rotated file that can't be deleted, a lost lock race) degrades to "the journal keeps
#      growing a bit past its cap this cycle," never to a changed decision, never to a leaked byte.
# UPDATED: 2026-09-16
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
#
# ── Rotation & the hard disk cap (B4.3) ─────────────────────────────────────────────────────────
#
# WHY: an append-only file with no ceiling is an unbounded state store — the one thing the ship
# gate for this feature explicitly forbids. Rotation must not reintroduce the per-fire subprocess
# cost B4.1 fought to remove (a plain `mkdir`/`stat` on every single fire already blew the ceiling
# once — see B4.1-report.md), so it CANNOT do a real, accurate size check on every fire. Instead:
#
#   - lhb_journal_maybe_rotate() is called once per fire, right after the append, and reuses the
#     SAME epoch-seconds value ("$_ts") the fire already paid a `date +%s` call for — it never
#     shells out to `date` itself.
#   - It is TIME-GATED: a real, forking size check (`wc -c`) runs AT MOST once every
#     LHB_JOURNAL_CHECK_INTERVAL_S seconds, machine-wide (tracked in a tiny sidecar state file, a
#     plain epoch-seconds integer, read/written with bash builtins only). On every other fire —
#     the overwhelming majority — this function does ZERO forks: only parameter expansion,
#     arithmetic, and a `read`/`printf` against a small local file. This is what "no new subprocess
#     per fire in the common path" means in practice for this file.
#   - When the gate opens and the live file is at/over LHB_JOURNAL_MAX_BYTES, it rotates: a single
#     `mv` to "<journal>.<epoch>.<pid>" (never a truncate-in-place — see concurrency note below),
#     under a non-blocking `mkdir`-based lock so two concurrent rotators can't race each other.
#     Losing that race is not a failure: the other fire is already handling it.
#   - Retention is a TOTAL byte budget across current + every rotated shard
#     (LHB_JOURNAL_MAX_TOTAL_BYTES): oldest shard deleted first, repeat until under budget. The
#     live file is never deleted, even if it alone exceeds the total budget (a misconfiguration —
#     MAX_TOTAL_BYTES should be >= MAX_BYTES — is not a license to drop data mid-write).
#
# CONCURRENCY SAFETY OF THE ROTATE-BY-RENAME: a `mv` (same-filesystem rename) does not affect an
# already-open file descriptor. A sibling fire whose `printf >>` opened the OLD path a moment
# before the rename keeps writing into the SAME inode, uncorrupted, now reachable only via the
# rotated name — its line is simply counted among the rotated shard's lines, never lost, never
# torn. A sibling fire whose `printf >>` runs AFTER the rename just recreates the path fresh
# (`>>` implies O_CREAT). Neither case can interleave or truncate a line — verified by the
# concurrency case in test_fire_journal.sh (20 parallel fires forced through a rotation mid-burst).
#
# DEFAULTS AND WHY (all overridable by env var):
#   LHB_JOURNAL_MAX_BYTES         5242880  (5 MiB)  — per-shard rotation threshold.
#   LHB_JOURNAL_MAX_TOTAL_BYTES  20971520  (20 MiB) — total cap, current + all rotated, oldest
#                                                      dropped first. At ~150-250 bytes/line this
#                                                      holds on the order of 100k lines — exactly
#                                                      the volume B4.2's query tool already proved
#                                                      it can read in under a second (0.789s,
#                                                      B4.2-report.md Verify 5) — chosen so the read
#                                                      side was never the limiting factor.
#   LHB_JOURNAL_CHECK_INTERVAL_S  2         (seconds) — how often the (forking) real size check is
#                                                      allowed to run, machine-wide. 2s keeps the
#                                                      amortized added cost negligible against the
#                                                      ≤61.35 ms ceiling (see journal-rotation-
#                                                      report.md's before/after remeasurement) while
#                                                      still catching runaway growth within a couple
#                                                      of seconds of real use. Set to 0 to force a
#                                                      real check on every fire — used by this file's
#                                                      own rotation tests, never by production
#                                                      defaults.
#
# Retention is a byte budget, not a time window — there is no "keep 7 days" clock here. A caller
# that wants a time-bounded view filters on the existing `ts` field via the query tool's
# `--since`/`--until`, which works identically across rotated shards (they carry real `ts` values
# same as the live file).

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
    # `mkdir` is an external binary (not a bash builtin) — a second subprocess fork on every single
    # fire, on top of the `date` call above, and it was the single biggest driver of a measured
    # overshoot against the ceiling this session (67.13 ms vs a 61.35 ms budget on the 25-guard
    # reference set — see B4.1-report.md). `[ -d ... ]` IS a builtin, so on every fire after the
    # very first (per journal directory, almost always true — the directory outlives any one hook),
    # this now costs nothing. `mkdir -p` still runs, once, the first time the directory is missing.
    if [ "$_dir" != "$_journal" ] && [ ! -d "$_dir" ]; then
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

    # Rotation/cap check — best-effort, see the header block above. Wrapped in its own
    # `2>/dev/null` and never allowed to influence this function's own (already-fixed) return 0.
    lhb_journal_maybe_rotate "$_journal" "$_ts" 2>/dev/null

    return 0
}

lhb_journal_maybe_rotate() {
    # $1=journal path  $2=current epoch seconds (the caller's own already-paid `date +%s` — this
    # function must NEVER call `date` itself, or it reintroduces exactly the per-fire subprocess
    # cost B4.1 fought to remove). Every early exit below is a silent no-op: this function must
    # never be the reason a fire behaves differently. See the rotation header note for the full
    # design rationale (time-gated sampling, rename-based rotation, byte-budget retention).
    local _j _now _dir _base _statefile _lockdir _lastcheck _maxbytes _maxtotal _interval _cursz
    local _rotated _shard _suffix _shard_ts _oldest _oldest_ts _total _sz _iterguard

    _j="${1:-}"
    _now="${2:-}"
    [ -n "$_j" ] || return 0
    case "$_now" in ''|*[!0-9]*) return 0 ;; esac

    _maxbytes="${LHB_JOURNAL_MAX_BYTES:-5242880}"
    _maxtotal="${LHB_JOURNAL_MAX_TOTAL_BYTES:-20971520}"
    _interval="${LHB_JOURNAL_CHECK_INTERVAL_S:-2}"
    case "$_maxbytes" in ''|*[!0-9]*) _maxbytes=5242880 ;; esac
    case "$_maxtotal" in ''|*[!0-9]*) _maxtotal=20971520 ;; esac
    case "$_interval" in ''|*[!0-9]*) _interval=2 ;; esac

    _dir="${_j%/*}"
    [ "$_dir" = "$_j" ] && _dir="."
    _base="${_j##*/}"
    # Sidecar meta files live under a DIFFERENT basename (a leading dot, prepended to the whole
    # journal basename) so they can never collide with the "$_j.<epoch>.<pid>" glob used below to
    # enumerate rotated shards.
    _statefile="$_dir/.${_base}.rotstate"
    _lockdir="$_dir/.${_base}.rotlock"

    _lastcheck=0
    if [ -f "$_statefile" ]; then
        IFS= read -r _lastcheck 2>/dev/null <"$_statefile"
    fi
    case "${_lastcheck:-}" in ''|*[!0-9]*) _lastcheck=0 ;; esac

    # Time-gated sampling: this is the ONLY thing standing between "checks every fire" (a forking
    # `wc -c`, unacceptable per the cost budget) and "checks at most once every N seconds,
    # machine-wide" (bash builtins only, until this line, on every fire that finds the gate shut).
    if [ $(( _now - _lastcheck )) -lt "$_interval" ]; then
        return 0
    fi
    # Claim the window immediately, before the (possibly slower) check below, so concurrent
    # siblings firing in the same instant see the gate as already-claimed. A lost race here just
    # means two real checks happen close together instead of one — never a correctness problem.
    printf '%s' "$_now" 2>/dev/null >"$_statefile"

    _cursz=0
    if [ -f "$_j" ]; then
        _cursz="$(wc -c 2>/dev/null <"$_j")"
        _cursz="${_cursz//[^0-9]/}"
    fi
    [ -n "$_cursz" ] || _cursz=0

    # Below this point we do real work (a possible rotation, and ALWAYS a retention pass -- see
    # note below on why retention cannot be conditioned on "did a rotation just happen") only
    # when the current file is at/over its own shard cap OR any rotated shards already exist (a
    # cheap glob test, no fork) -- if neither, there is nothing this cycle could possibly need to
    # do, so skip acquiring the lock at all.
    if [ "$_cursz" -lt "$_maxbytes" ]; then
        _oldest=""
        for _shard in "$_j".[0-9]*.[0-9]*; do
            [ -f "$_shard" ] && { _oldest="$_shard"; break; }
        done
        [ -n "$_oldest" ] || return 0
    fi

    # Non-blocking mutex: `mkdir` is atomic for exactly one racer. Failing to acquire it is not a
    # failure — another fire is already doing rotation/retention this cycle.
    mkdir "$_lockdir" 2>/dev/null || return 0

    _cursz=0
    if [ -f "$_j" ]; then
        _cursz="$(wc -c 2>/dev/null <"$_j")"
        _cursz="${_cursz//[^0-9]/}"
    fi
    [ -n "$_cursz" ] || _cursz=0
    if [ "$_cursz" -ge "$_maxbytes" ]; then
        _rotated="$_j.$_now.$$"
        mv -- "$_j" "$_rotated" 2>/dev/null
    fi

    # Retention runs on EVERY gate-open cycle, not only when a rotation just happened: the
    # current (still-filling) shard growing past prior rotated shards can itself push the total
    # over budget before it reaches its OWN per-shard cap, and that must still be caught here
    # (a real gap found and fixed during this build's own Verify #1 -- see journal-rotation-
    # report.md). Sum current + every rotated shard; delete the OLDEST rotated shard first until
    # back under the total budget. Bounded to 1000 iterations purely as a belt-and-braces guard
    # against ever looping forever (there are never remotely that many shards in practice — a
    # single 5 MiB shard is dropped as one unit).
    _iterguard=0
    while [ "$_iterguard" -lt 1000 ]; do
        _iterguard=$((_iterguard + 1))
        _total=0
        if [ -f "$_j" ]; then
            _sz="$(wc -c 2>/dev/null <"$_j")"
            _sz="${_sz//[^0-9]/}"
            _total=$((_total + ${_sz:-0}))
        fi
        _oldest=""
        _oldest_ts=""
        for _shard in "$_j".[0-9]*.[0-9]*; do
            [ -f "$_shard" ] || continue
            _suffix="${_shard#"$_j".}"
            _shard_ts="${_suffix%%.*}"
            case "$_shard_ts" in ''|*[!0-9]*) continue ;; esac
            _sz="$(wc -c 2>/dev/null <"$_shard")"
            _sz="${_sz//[^0-9]/}"
            _total=$((_total + ${_sz:-0}))
            if [ -z "$_oldest_ts" ] || [ "$_shard_ts" -lt "$_oldest_ts" ]; then
                _oldest_ts="$_shard_ts"
                _oldest="$_shard"
            fi
        done
        [ "$_total" -gt "$_maxtotal" ] || break
        [ -n "$_oldest" ] || break
        rm -f -- "$_oldest" 2>/dev/null
        # Couldn't actually remove it (e.g. a read-only rotated-shard directory) -- stop instead
        # of looping forever on the same immovable file. This is the fail-safe path Verify #4
        # exercises directly.
        [ -e "$_oldest" ] && break
    done

    rmdir "$_lockdir" 2>/dev/null
    return 0
}
