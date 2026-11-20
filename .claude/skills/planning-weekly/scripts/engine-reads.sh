#!/bin/bash
# engine-reads.sh — the session's READS from the engine, in one place, --json only.
# Commands are the engine-owned read commands documented in
# shared/grand_central/docs/planning-interface.md (never guessed, never redefined here):
#   gc fresh / gc week / gc urgent / gc due / gc person / gc org / gc upcoming / gc status
# Handles the two named no-feed states the interface documents:
#   - `gc fresh` exit 3 = stale: the caller is TOLD ("STALE: ..."), never silently planned on.
#   - `gc person`/`gc org` exit 1 with a "found": false body: printed as NOT FOUND, not a failure.
# Writes nothing. All args after the subcommand are passed through.
#
# Usage: engine-reads.sh <subcommand> [extra args...]
# allow-silence: build-ruled location — slice B of the planning-weekly build; the coordinator
# ruled this worktree skill folder as the home for these files, and the build task forbids
# own_list_add and any write outside the worktree. Not a personal tool; never moved to ClaudeOps.
set -u
ERRTMP="$(mktemp)" || { echo "ERROR: mktemp failed — cannot capture gc stderr" >&2; exit 1; }
trap 'rm -f "$ERRTMP"' EXIT

SUB="${1:-}"
[ -z "$SUB" ] && { echo "ERROR: usage: engine-reads.sh <fresh|week|urgent|due|person|org|upcoming|status> [args...]" >&2; exit 2; }
shift

case "$SUB" in
    fresh|week|urgent|due|person|org|upcoming|status) ;;
    *) echo "ERROR: unknown subcommand '$SUB' (allowed: fresh week urgent due person org upcoming status)" >&2; exit 2 ;;
esac

OUT="$(gc "$SUB" --json "$@" 2>"$ERRTMP")"
RC=$?
ERR="$(cat "$ERRTMP" 2>/dev/null)"

if [ -n "$ERR" ]; then printf '%s\n' "$ERR" >&2; fi

# The named no-feed states (planning-interface.md, "Known behaviour"):
# exit 1 + "found": false = not found (a valid answer, print the body);
# `gc fresh` exit 3 = stale (say so loudly, and still print the body).
if [ $RC -eq 0 ]; then
    printf '%s\n' "$OUT"
    exit 0
fi

case "$SUB" in
    person|org)
        case "$OUT" in
            *'"found": false'*|*'"found":false'*)
                printf '%s\n' "$OUT"
                exit 0 ;;
        esac
        ;;
    fresh)
        if [ $RC -eq 3 ]; then
            echo "STALE: the engine's feed is stale (gc fresh exited 3) — say so before planning on old data." >&2
            printf '%s\n' "$OUT"
            exit 3
        fi
        ;;
esac

echo "ERROR: gc $SUB --json exited $RC" >&2
printf '%s\n' "$OUT" >&2
exit $RC
