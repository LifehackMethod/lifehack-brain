#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# gws-auth.lib.sh — THE gws (Google) headless-credential preflight. One copy, eleven callers.
#
# SIBLING of `system/tools/claude-auth.lib.sh`, and deliberately built to the SAME contract.
# Read that file's header first if you have not: everything it says about WHY the preflight is a
# shared function instead of a careful edit applies here verbatim, for the same reason and from the
# same session.
#
# WHY THIS FILE EXISTS (read this before "simplifying" it back into the callers):
# Eleven runners needed the same handful of lines — find the keychain-free exported gws credential
# file, export the three GOOGLE_WORKSPACE_CLI_* vars that point gws at it, and decide what to do
# when it is not there. All eleven hand-rolled it. The claude-token version of exactly this story
# was fixed TWICE and still shipped three copies carrying the bug, which is the whole reason that
# check now lives in one function; this file is that lesson applied to the second credential before
# it costs the same again. ⛔ Do not re-inline it.
#
# THE CONTRACT — rc=75 means STOOD DOWN, and it is NOT rc=3:
#   `system/pulse-config.md`'s exit-code table is the authority:
#     rc=0  -> ran and succeeded (including "checked, found nothing wrong")  -> counted `ran`
#     rc=75 -> the job's OWN preflight declined to run this tick (config/credentials not set
#              up yet)                                                       -> counted `skipped`
#     rc=2  -> transient pre-flight/infra failure                            -> held
#     anything else (INCLUDING 3) -> a real failure -> counted toward the 3-strike breaker
#   "No gws credential file yet" is true on day one of EVERY install, and PERMANENTLY true for a
#   student who never connects a Google account at all — which on a fresh install is nearly all of
#   them. With rc=3 that fires on every tick, trips Pulse's 3-strike breaker, and
#   `system-health.py`'s assess() renders the job DOWN/severity:error PERMANENTLY — i.e. it
#   presents "no Google account connected" as BREAKAGE and auto-disables a runner the person never
#   chose to use. rc=75 is the whole fix. `ingest_load_gws()` in ingest-run.lib.sh was the SIXTH
#   copy of that bug and the first REACHABLE one (the three fixed an hour earlier were latent —
#   no scheduler row pointed at them yet).
#
# ⛔ rc=75 IS NOT "EVERYTHING IS FINE." It is a NAMED, VISIBLE stand-down — every path below emits
# a line saying which credential is missing or unusable and how to supply it, per the house rule at
# `system/build-rules-index.md` (ABSENT-SUBJECT-RULE-v1, ratified T9.11b 2026-08-15): *a checker
# fails loud when its subject is absent or ambiguous.* "I checked and it's clean" and "there was
# nothing here I could check" are different claims and must never share a spelling.
#
# THE AMBIGUOUS CASE IS NOT THE ABSENT CASE, AND BOTH ARE STAND-DOWNS.
# Every one of the eleven hand-rolled copies gated on `[ -s "$GWS_CREDS" ]`. That test is TRUE for
# a file containing only a newline, and true for a file holding truncated/corrupt JSON — so the
# callers exported GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE pointing at garbage, sailed on, and let
# gws fail downstream with empty output. That is "I could not look" spelled as "I looked and it was
# fine" — the exact shape ABSENT-SUBJECT-RULE-v1 exists to forbid. So a present-but-unusable file
# gets its OWN named reason (`empty-gws-credentials` / `unparseable-gws-credentials`) and the same
# rc=75 treatment as missing: nothing is broken, the credential just is not usable yet.
#
# ⛔ WHAT IS **NOT** IN THIS FILE, ON PURPOSE — the live `gws ... getProfile` pre-flight.
# Seven runners follow their credential check with a 3x/4s retry loop that actually CALLS Google and
# exits **2** on failure. That is a DIFFERENT check with a DIFFERENT meaning and it is not buggy
# anywhere: reaching it means the person HAS configured credentials, so a failing call is a real
# transient/infra condition (rc=2 = "held", never the breaker) — not a stand-down. Folding it into
# this helper's 75 would tell Pulse "not configured yet" about a machine that IS configured, and
# would hide genuinely dead auth forever. It also ends differently per caller by design: four treat
# it as FATAL, three are warn-only and degrade into a partial result. Left with its callers,
# deliberately. See the decision note in `system/pulse-config.md`.
#
# USAGE — the caller decides HOW to terminate, this file only decides WHETHER:
#   source "$CODE_ROOT/system/tools/gws-auth.lib.sh"
#   require_gws_credentials "my-job"            || exit 75           # plain script, gws REQUIRED
#   require_gws_credentials "$SUBSYSTEM_NAME"   || { RC=75; exit 75; }   # trap reads $RC first
#   require_gws_credentials "$LABEL" _my_logger || return 75         # inside a lib function
#   load_gws_credentials_optional "my-job"                           # gws OPTIONAL: never fails
#   # on success both export GOOGLE_WORKSPACE_CLI_{CONFIG_DIR,CREDENTIALS_FILE,KEYRING_BACKEND}
# Same deliberate API choice as require_claude_token: it does NOT exit/return on your behalf,
# because the callers legitimately end differently — one is a function that must `return` (an
# `exit` there would kill its wrapper before the wrapper's own cleanup), several must set their
# `RC` global so their EXIT trap records the right code, one must write a status tile before
# leaving. A helper that exited for them could serve only one of those, which is how you get copies
# again.
#
# THE TWO ENTRY POINTS ARE NOT INTERCHANGEABLE — pick by what the job does without Google:
#   require_gws_credentials        — the job CANNOT do its work without Google. Absent/unusable
#                                    credentials = rc=75 stand-down, the job does not run.
#                                    (calendar-store-sync, tasks-store-sync, email-summary-write,
#                                    ingest-run.lib.sh's ingest_load_gws)
#   load_gws_credentials_optional  — the job produces a real, useful, DEGRADED result without
#                                    Google (a diary from local journal + status tiles; a vault
#                                    that marks each unreachable source in its manifest). Always
#                                    returns 0. Still emits ONE named line when the credential is
#                                    absent or unusable — silence there would be the same
#                                    "nothing to check" == "checked, clean" collapse; it just is
#                                    not fatal. (planning-analyze, planning-vault, planning-vault-weekly,
#                                    planning-diary, planning-weekly-analyze, planning-weekly-prime,
#                                    archivist-run.lib.sh)
#
# ARGS (both functions)
#   $1  label      — job name for the message, e.g. "calendar-store-sync". Optional; defaults "gws".
#   $2  logger     — OPTIONAL name of a caller function taking one string. If given (and it is a
#                    real function) the message goes through it, so a caller with its own
#                    timestamped/prefixed log format keeps that format byte-for-byte. Otherwise
#                    the message is echoed as "[label] <message>".
# RETURNS
#   require_gws_credentials:       0 usable + exported · 75 STOOD DOWN (message already emitted)
#   load_gws_credentials_optional: always 0 (check $GWS_AUTH_STANDDOWN_REASON if you care)
# SETS (globals, readable by the caller after the call)
#   GWS_CREDS_FILE               — the path it actually looked at
#   GWS_AUTH_STANDDOWN_REASON    — "" on success · "no-gws-credentials" ·
#                                  "empty-gws-credentials" · "unparseable-gws-credentials"
#
# ⛔ NO `set` LINE IN THIS FILE, ON PURPOSE — same reason as claude-auth.lib.sh, and here it is
# load-bearing in both directions. It is sourced into scripts running under three different option
# sets (`set -u`, `set -uo pipefail`, `set -eo pipefail`); setting options here would silently
# change the shell semantics of whichever caller sourced it. It is also why this lives in its OWN
# file rather than folded into ingest-run.lib.sh, which DOES carry heavy top-level side effects
# (`set -uo pipefail`, a GWS_BIN resolve, an EMAIL_SERVICE_READ export, a CODE_ROOT overwrite) —
# sourcing THAT from a `set -eo pipefail` runner would quietly rewrite its error semantics.
# Everything below is written to be correct under all three (every expansion is defaulted; nothing
# bare can trip -e).
#
# SCOPE — gws/Google credentials ONLY. The claude subscription token is a different credential with
# a different failure story and lives in claude-auth.lib.sh. A runner needing both calls both.
# ─────────────────────────────────────────────────────────────────────────────

# Where the exported credentials live. `~/.config/lifehack` is this repo's established machine-local
# config home (shared/brain_root.py, shared/gate/sentinel_response.py, ingest-run.lib.sh's
# $_INGEST_CFG) — machine-local, 0600, and NEVER written into the tracked repo or the person's notes
# root. $LIFEHACK_GWS_CREDS_FILE overrides it; that is an escape hatch for tests and unusual
# installs, and it cannot manufacture a pass — whatever it points at still has to exist and still
# has to parse. Deliberately NOT named GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE: that one is gws's own
# input variable, which this file WRITES, and reading + writing the same name would let a stale
# export from a previous job in the same shell silently redirect the check.
gws_creds_path() {
  printf '%s' "${LIFEHACK_GWS_CREDS_FILE:-${HOME:-}/.config/lifehack/gws-credentials.json}"
}

# The keychain-free config dir gws should use, derived from the creds path so a test override moves
# BOTH together and can never half-point at a real profile. Production value is unchanged:
# ~/.config/lifehack/gws-cron.
gws_config_dir() {
  local creds dir
  creds="$(gws_creds_path)"
  dir="${creds%/*}"
  [ "$dir" = "$creds" ] && dir="."
  printf '%s/gws-cron' "$dir"
}

# Message dispatch — through the caller's own logger when it gave us one, so its log format survives.
_gws_emit() {   # $1 label, $2 logger-name (may be empty), $3 message
  if [ -n "${2:-}" ] && type "${2}" >/dev/null 2>&1; then
    "${2}" "${3:-}"
  else
    echo "[${1:-gws}] ${3:-}"
  fi
}

# Decide whether the credential file is USABLE, and export gws's env when it is.
# Returns 0 usable (exported) · 1 not usable (GWS_AUTH_STANDDOWN_REASON + $_GWS_MSG set, NOT emitted
# — the two public entry points differ only in how loudly and how fatally they report it).
_gws_creds_probe() {
  local creds cfgdir raw
  creds="$(gws_creds_path)"
  cfgdir="$(gws_config_dir)"
  GWS_CREDS_FILE="$creds"
  GWS_AUTH_STANDDOWN_REASON=""
  _GWS_MSG=""

  if [ ! -r "$creds" ]; then
    GWS_AUTH_STANDDOWN_REASON="no-gws-credentials"
    _GWS_MSG="STOOD DOWN: no gws credentials at $creds — this job needs the Google Workspace CLI (gws) set up first. From an interactive session run: gws auth export --unmasked > $creds && chmod 600 \"\$_\" && mkdir -p $cfgdir. See INSTALL.md."
    return 1
  fi

  # AMBIGUOUS, not absent — and previously a SILENT PASS. The old `[ -s "$creds" ]` test is true for
  # a file containing only a newline, so every caller exported it and let gws fail downstream with
  # empty output. Read it, strip whitespace, and require something to actually be there.
  raw="$(tr -d '[:space:]' < "$creds" 2>/dev/null)"
  if [ -z "$raw" ]; then
    GWS_AUTH_STANDDOWN_REASON="empty-gws-credentials"
    _GWS_MSG="STOOD DOWN: gws credential file $creds exists but is empty (whitespace only) — re-export it: gws auth export --unmasked > $creds && chmod 600 \"\$_\". See INSTALL.md."
    return 1
  fi

  # Non-empty is still not the same as USABLE: a truncated or corrupt export is bytes that mean
  # nothing to gws. Parse it. python3 is a hard dependency of every runner that sources this file.
  if command -v python3 >/dev/null 2>&1; then
    if ! python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$creds" >/dev/null 2>&1; then
      GWS_AUTH_STANDDOWN_REASON="unparseable-gws-credentials"
      _GWS_MSG="STOOD DOWN: gws credential file $creds is not valid JSON (truncated or corrupt export) — re-export it: gws auth export --unmasked > $creds && chmod 600 \"\$_\". See INSTALL.md."
      return 1
    fi
  else
    # We could not run the parse check. Say so out loud rather than let "unchecked" read as
    # "checked and fine" — ABSENT-SUBJECT-RULE-v1 again, applied to our own instrument. Not a
    # stand-down: the credential may well be perfect, and gws itself will report a bad one.
    _gws_emit "${_GWS_LABEL:-gws}" "${_GWS_LOGGER:-}" "NOTE: python3 not found — gws credential JSON at $creds was NOT validated, only checked for existence and non-emptiness. Proceeding."
  fi

  export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$cfgdir"
  export GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE="$creds"
  export GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND=file
  return 0
}

# gws REQUIRED — absent/unusable credentials means this job does not run this tick. 0 | 75.
require_gws_credentials() {
  _GWS_LABEL="${1:-gws}"; _GWS_LOGGER="${2:-}"
  _gws_creds_probe && return 0
  _gws_emit "$_GWS_LABEL" "$_GWS_LOGGER" "$_GWS_MSG"
  return 75
}

# gws OPTIONAL — the job degrades into a real, useful, partial result without Google. Always 0.
# Still names the absence, because a job that quietly produced a Google-less result and reported it
# as a normal run is the same collapse rc=75 exists to prevent — just at a lower severity.
load_gws_credentials_optional() {
  _GWS_LABEL="${1:-gws}"; _GWS_LOGGER="${2:-}"
  _gws_creds_probe && return 0
  _gws_emit "$_GWS_LABEL" "$_GWS_LOGGER" "NOTE: ${_GWS_MSG#STOOD DOWN: } Google-backed sources will be marked unavailable this run; the rest of the job continues."
  return 0
}
