#!/bin/sh
# Registered 2026-11-24 through system/register/register.jsonl + generate.py (run pickup, spec G6).
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="$0"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac
if [ -r "$_lhb_dir/lib/journal.sh" ]; then . "$_lhb_dir/lib/journal.sh"; else lhb_journal_fire() { :; }; fi
trap 'lhb_journal_fire "$?" "run_pickup_hook.sh" "SessionStart" "" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: a crashed window loses the run's place in the conversation; the next window must ask
#      "You were on step N of T of <skill>. Continue, start over, or leave it?" before touching
#      anything (spec run-pickup, id run-pickup-spec-2026-11-23; skills SOP Build step 14). This
#      hook is the only way to speak at window start: it passes the SessionStart stdin to
#      run_pickup.py session, which prints the offer, the post-compaction reminder, or a
#      "can't pick up" line — and stays silent for a finished, abandoned, snoozed, damaged or
#      absent run, and for an unattended session (LIFEHACK_JOB_RUN_ID).
# GUARDS: SessionStart, empty matcher. It never blocks and never decides — the reader's answer
#      goes to the AI, the AI asks the person, the person decides.
# REDIRECT: N/A (non-blocking). The offer itself carries the commands (resume / abandon / snooze
#      with the closed menu words); a "can't pick up: <reason>" line tells the AI to tell the
#      person and offer only "start over".
# SIGNPOST: the reader is system/parts/run_pickup.py (read-only, never writes); the runner is
#      system/parts/stage_runner.py; the spec is the run-pickup spec (G4, G5).
# UPDATED: 2026-11-23 (Phase 4c fix pass: journal.sh sourced only when readable;
#      reader lines that do not start with the tag are dropped).
# FAIL_POSTURE: degrade-safe (prints a tagged line on every failure; never blocks; exit 0 always —
#      a SessionStart hook's non-zero exit is silenced, and stdout is the only channel that reaches
#      the model). Plain stdout, never systemMessage. Its own hook, not a line in
#      session_context_loader.sh (P-21: the loader carries notes context and runs long).
# ─────────────────────────────────────────────────────────────────────────────
DIR=`CDPATH= cd -- "$(dirname -- "$0")" && pwd`
READER="$DIR/../parts/run_pickup.py"
TAG='[RUN PICKUP — harness-injected, not user input]'
PAYLOAD=`cat`
OUT=`printf '%s' "$PAYLOAD" | python3 "$READER" session 2>/dev/null`
rc=$?
if [ "$rc" -eq 0 ]; then
  case "$OUT" in
    "") ;;               # silent: nothing to pick up, or nothing to offer
    *) FILTERED=`printf '%s\n' "$OUT" | grep -F -- "$TAG" 2>/dev/null`
       case "$FILTERED" in
         "") ;;           # a reader line that does not start with the tag is dropped
         *) printf '%s\n' "$FILTERED" ;;
       esac ;;
  esac
else
  # the reader crashed: one tagged line, so the failure is never silent
  printf '%s run pickup could not run (the reader failed, exit %s); tell the person a skill run may be unfinished\n' \
    '[RUN PICKUP — harness-injected, not user input]' "$rc"
fi
exit 0
