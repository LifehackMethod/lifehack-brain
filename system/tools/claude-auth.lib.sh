#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# claude-auth.lib.sh — THE headless-claude credential preflight. One copy, five callers.
#
# WHY THIS FILE EXISTS (read this before "simplifying" it back into the callers):
# Every runner that fires `claude -p` from a scheduled/headless context needs the same three
# lines — find the subscription token, export CLAUDE_CODE_OAUTH_TOKEN, stand down if it isn't
# there. That preflight was hand-rolled FIVE times (archivist-run.lib.sh · ingest-run.lib.sh ·
# cal-analyze-run.sh · cal-weekly-analyze-run.sh · planning-weekly-prime-run.sh), each copy
# carrying its own literal exit code. All five had the SAME wrong one (`3`), and the bug was
# fixed TWICE — in archivist-run.lib.sh and planning-weekly-prime-run.sh, 2026-08-15 — without
# the other three changing, because a fix applied to a copy does not reach the other copies.
# That is why this is a shared function and not a sixth careful edit. ⛔ Do not re-inline it.
#
# THE CONTRACT — rc=75 means STOOD DOWN, and it is NOT rc=3:
#   `system/pulse-config.md`'s exit-code table is the authority:
#     rc=0  -> ran and succeeded (including "checked, found nothing wrong")  -> counted `ran`
#     rc=75 -> the job's OWN preflight declined to run this tick (config/credentials not set
#              up yet)                                                       -> counted `skipped`
#     rc=2  -> transient pre-flight/infra failure                            -> held
#     anything else (INCLUDING 3) -> a real failure -> counted toward the 3-strike breaker
#   "No token file yet" is true on day one of EVERY install and stays true until the person runs
#   the one-time `claude setup-token`. With rc=3 that fires on every tick, trips Pulse's breaker
#   within three ticks, and `system-health.py`'s assess() renders the job DOWN/severity:error
#   PERMANENTLY — i.e. it presents "not configured yet" as BREAKAGE and auto-disables a runner a
#   student never got to use. rc=75 is the whole fix.
#
# ⛔ rc=75 IS NOT "EVERYTHING IS FINE." It is a NAMED, VISIBLE stand-down — this function always
# emits a line saying which credential is missing and how to supply it, per the house rule at
# `system/build-rules-index.md` (ABSENT-SUBJECT-RULE-v1, ratified T9.11b 2026-08-15): *a checker
# fails loud when its subject is absent or ambiguous.* "I checked and it's clean" and "there was
# nothing here I could check" are different claims and must never share a spelling. A caller that
# swallows the 75 and continues to `claude -p` gets exit 127 with EMPTY stdout — indistinguishable
# from "the model found nothing" (MODEL-REACH-RULE-v1, same file). Map unreachable · timed-out ·
# rate-limited · malformed · empty onto the stand-down outcome, NEVER onto clean.
#
# USAGE — the caller decides HOW to terminate, this function only decides WHETHER:
#   source "$CODE_ROOT/system/tools/claude-auth.lib.sh"
#   require_claude_token "my-job"            || exit 75            # plain script
#   require_claude_token "my-job" _my_logger || { _emit_tile ...; exit 75; }   # tile first
#   require_claude_token "$ARCH_LABEL" _alog || return 75          # inside a lib function
#   # on success: CLAUDE_CODE_OAUTH_TOKEN is exported, ready for `"$CLAUDE_BIN" -p ...`
# It deliberately does NOT exit/return-on-your-behalf, because the five callers legitimately end
# differently: one is a function that must `return` (an `exit` there would kill its wrapper before
# the wrapper's own cleanup), one must write a status tile before leaving, one must set its RC
# global so its EXIT trap records the right code. A helper that exited for them could serve only
# one of the three, which is how you end up with copies again.
#
# ARGS
#   $1  label      — job name for the message, e.g. "cal-analyze". Optional; defaults to "claude".
#   $2  logger     — OPTIONAL name of a caller function taking one string. If given (and it is a
#                    real function) the message goes through it, so a caller with its own
#                    timestamped/prefixed log format keeps that format byte-for-byte. Otherwise
#                    the message is echoed as "[label] <message>".
# RETURNS
#   0   token found and exported (CLAUDE_CODE_OAUTH_TOKEN)
#   75  STOOD DOWN — message already emitted; reason in $CLAUDE_AUTH_STANDDOWN_REASON
# SETS (globals, readable by the caller after the call)
#   CLAUDE_TOKEN_FILE            — the path it actually looked at
#   CLAUDE_AUTH_STANDDOWN_REASON — "" on success · "no-claude-token" · "empty-claude-token"
#
# ⛔ NO `set` LINE IN THIS FILE, ON PURPOSE. It is sourced into scripts running under three
# different option sets (`set -u`, `set -uo pipefail`, `set -eo pipefail`); setting options here
# would silently change the shell semantics of whichever caller sourced it. Everything below is
# written to be correct under all three (every expansion is defaulted; nothing bare can trip -e).
#
# SCOPE — claude subscription token ONLY. gws/Google credentials are a different credential with
# a different failure story and stay with their own callers.
# ─────────────────────────────────────────────────────────────────────────────

# Where the token lives. `~/.config/lifehack` is this repo's established machine-local config home
# (shared/brain_root.py, shared/gate/sentinel_response.py, ingest-run.lib.sh) — machine-local, 0600,
# and NEVER written into the tracked repo or the person's notes root. $CLAUDE_OAUTH_TOKEN_FILE
# overrides it; that is an escape hatch for tests and unusual installs, and it cannot manufacture a
# pass — whatever it points at still has to contain a non-whitespace token.
claude_token_path() {
  printf '%s' "${CLAUDE_OAUTH_TOKEN_FILE:-${HOME:-}/.config/lifehack/claude-oauth-token}"
}

require_claude_token() {
  local label="${1:-claude}" logger="${2:-}"
  local tokfile tok msg

  tokfile="$(claude_token_path)"
  CLAUDE_TOKEN_FILE="$tokfile"
  CLAUDE_AUTH_STANDDOWN_REASON=""

  if [ -r "$tokfile" ] && [ -s "$tokfile" ]; then
    tok="$(tr -d '[:space:]' < "$tokfile" 2>/dev/null)"
    if [ -n "$tok" ]; then
      export CLAUDE_CODE_OAUTH_TOKEN="$tok"
      return 0
    fi
    # AMBIGUOUS, not absent — and previously a SILENT PASS: the old `[ -s "$tok" ]` test is true
    # for a file containing only a newline, so the callers exported an EMPTY token, proceeded, and
    # got `claude -p` failing downstream with empty stdout — the exact "I could not look" spelled
    # as "I looked" that ABSENT-SUBJECT-RULE-v1 exists to forbid. It is a stand-down, same as
    # missing: nothing is broken, the credential just isn't usable yet.
    CLAUDE_AUTH_STANDDOWN_REASON="empty-claude-token"
    msg="STOOD DOWN: claude token file $tokfile exists but holds no token (whitespace only) — run 'claude setup-token' and save the token there."
  else
    CLAUDE_AUTH_STANDDOWN_REASON="no-claude-token"
    msg="STOOD DOWN: no claude token at $tokfile — run 'claude setup-token' and save it there."
  fi

  if [ -n "$logger" ] && type "$logger" >/dev/null 2>&1; then
    "$logger" "$msg"
  else
    echo "[$label] $msg"
  fi
  return 75
}
