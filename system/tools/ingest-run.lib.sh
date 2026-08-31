#!/usr/bin/env bash
# ingest-run.lib.sh — SHARED scaffold for headless ingest/runner scripts.
#
# WHY: a headless `claude -p` runner needs the same handful of pieces every time — reachable-binary
# resolution, subscription auth, a single-instance lock, a cheap gate before spawning anything, and a
# watchdog-bounded launch. This is that plumbing, factored out once so a future runner script is a
# few lines of POLICY (what prompt, what model, what to check first) sourcing a few lines of PLUMBING.
#
# PORTED (2026-08-14) from claudeops-config's system/tools/ingest-run.lib.sh — that repo's donor
# comment called this file "the worst hardcode in the tree": it carried a literal absolute-path
# CLAUDE_BIN under a specific person's home directory, not even $HOME-relative, plus a Drive path
# under that same account. Both are fixed below. Three pieces were DROPPED rather than ported,
# each for a reason that already exists elsewhere in this repo, not invented here:
#   - the primary-machine / hardware gate (`require_primary`, `ingest_studio_gate`,
#     `require_studio_hardware`) — depended on `machine-token.sh`, which is excluded from this port
#     by ruling, and on a Drive-synced `state/primary-machine` marker electing one of two machines
#     as lead. This repo has no such model: "there is one machine. The two-machine plane is not part
#     of this system." (docs/data-layout.md:214). A gate for a concept that does not exist here is
#     not a gate, it is a function nothing can safely reach.
#     ⚖ NOTE 2026-08-15 — the two `…_studio_…` names on the line above are DONOR CODE IDENTIFIERS
#     and are deliberately NOT renamed. They named one of the donor's own machines, from an era
#     before that gate was renamed to a role. **None of the three functions exists in this repo** —
#     verified by grep: no definition and no call site anywhere, in any language; they survive only
#     inside port notes like this one recording that they were dropped, and the donor files that
#     defined them were never ported either. The surrounding sentence is DONOR DESCRIPTION, not a
#     description of this system. Renaming an identifier that points at nothing would only invent a
#     new false name; the machine it was named after is deliberately not named here. Same handling,
#     same wording, as system/organism/elements/pulse-cron.md's note on the identical names.
#   - the trusted-email-lane flag (`ingest_set_lane`, `_INGEST_LANE_FILE`) — already retired
#     repo-wide; see system/hooks/session_flight_recorder.sh's note on why it isn't here.
#   - the v1 per-item Sentinel check (`ingest_sentinel_check`) — the donor's OWN comments mark it
#     dead code with no live caller, superseded by the gate-routed v2 path (`ingest_gate_check`,
#     kept below). Porting known-dead code that also double-logs into the same JSONL
#     shared/gate/sentinel_response.py already writes internally would corrupt the exact counts
#     sentinel-health.py (this repo's ported twin) reports — not worth reviving.
#
# ⚠ CORRECTED 2026-08-15 (T9.7d stale-claim sweep). This block used to assert, in full caps, that
# the repo had neither a scheduler nor any cron wiring, that nothing invoked this library on any
# cadence, and that installing a schedule remained a separate not-yet-done step the reader must
# not assume. BOTH halves of that are FALSE, and it was the loudest stale claim in the tree:
#   - A scheduler ships. `system/tools/pulse.sh` is the daemon, `system/tools/install-schedulers.sh`
#     installs the single entry that drives it (cron on macOS/Linux, Task Scheduler on Windows), and
#     `system/pulse-config.md` is the row manifest.
#   - This library IS invoked on a cadence, by two live rows: `system-health` (300s) via
#     system-health-run.sh, and `sentinel-health` (1800s) via sentinel-health-run.sh. Both `source`
#     this file. A change here reaches them on their next tick — edit it as LIVE plumbing, not as
#     dormant ported code.
# Still true, and the reason the original note existed: this file is a LIBRARY, so it has no
# pulse-config.md row of its own and never will — it runs only through a caller that has one.
#
# LANE: this is plumbing only. What to flag, what to score, what a run should actually DO belongs in
# the calling skill/runner's own prompt — never in here.
#
# USAGE — a runner script sources this, sets a few vars, calls the functions in order:
#   source "$CODE_ROOT/system/tools/ingest-run.lib.sh"   # the lib derives its own CODE_ROOT
#   ingest_check_paused  "cal-ingest"                       # exit 0 if a human paused this source
#   ingest_load_auth     "cal-ingest"                       # claude token + isolated gws creds + pre-flight
#   ingest_acquire_lock  "cal-ingest"                       # single-instance (exit 0 if already running)
#   ingest_new_mail_gate "cal-ingest" "SomeLabel"            # INLINE (never $()); exits cheap if nothing new
#   CUTOFF="$INGEST_CUTOFF"                                  # the gate set it as a global
#   ingest_run_claude    "$MODEL" "$WATCHDOG" "$PROMPT" "$WORK_DIR"   # launch + watchdog → sets INGEST_RC
#   ingest_finish         "cal-ingest"                       # advance marker on success; exit INGEST_RC
#
# All machine-local paths (token, gws creds, marker, lock) live under ~/.config/lifehack — this
# repo's established config home (shared/brain_root.py, shared/gate/sentinel_response.py) — and are
# NEVER written into the tracked repo or the person's notes root.
set -uo pipefail

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
_INGEST_CFG="$HOME/.config/lifehack"

# The ONE headless-claude credential preflight (require_claude_token) — shared with the four other
# runners that fire `claude -p`, so the rc=75 stand-down contract cannot drift between copies again.
# A missing library is a REAL defect (exit 1), never a stand-down.
. "$CODE_ROOT/system/tools/claude-auth.lib.sh" || {
  echo "FATAL: cannot source $CODE_ROOT/system/tools/claude-auth.lib.sh"; exit 1; }

# The ONE headless-gws credential preflight (require_gws_credentials) — shared with the ten other
# runners that reach Google, for the same reason and on the same rc=75 contract. Same rule: a
# missing library is a REAL defect (exit 1), never a stand-down.
. "$CODE_ROOT/system/tools/gws-auth.lib.sh" || {
  echo "FATAL: cannot source $CODE_ROOT/system/tools/gws-auth.lib.sh"; exit 1; }

# ── REACHING THE MODEL — runtime-resolved, no hardcoded user directory ──────────────────────────
# House standard, already live in this repo (shared/tools/intake_reader.py's CLAUDE_BIN block;
# documented at system/build-rules-index.md's MODEL-REACH-RULE and system/sops/skill-building-sop.md):
# `claude` is commonly installed at ~/.local/bin/claude, which is NOT on a cron/headless PATH. Order:
# an explicit $CLAUDE_BIN override first (never guessed away) → PATH → a short list of known install
# locations as a LAST resort → the bare name (so a caller that DOES have it on PATH at call time still
# works even if none of the above matched at source-time). No user's home directory is ever literal.
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude 2>/dev/null)}"
if [ -z "$CLAUDE_BIN" ]; then
  for _cb in "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
    [ -x "$_cb" ] && CLAUDE_BIN="$_cb" && break
  done
fi
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
unset _cb

# gws — same resolution shape this repo already uses (shared/tools/calendar_store_sync.py,
# system/hooks/guard_sheet_formula_writes.sh): PATH first, one known Apple-Silicon Homebrew location
# as a last resort. Only touched by ingest_load_gws / ingest_new_mail_gate below.
GWS_BIN="${GWS_BIN:-$(command -v gws 2>/dev/null)}"
GWS_BIN="${GWS_BIN:-/opt/homebrew/bin/gws}"

# ── EMAIL-SERVICE READ FLAG (blue-green rollout switch) ───────────────────────────────────────
# A future headless runner sourcing this lib inherits this exported var (the `claude -p` subprocess
# gets it via the environment). DEFAULT OFF (empty) → a desk's own raw read path is unaffected. To
# enable, write a comma-list of desk ids (or 'all') into the machine-local file below — e.g.
# `printf planning > ~/.config/lifehack/email-service-read`. shared/tools/email_service_read.py reads
# $EMAIL_SERVICE_READ and returns DISABLED when a desk isn't listed — this is that switch's one path
# in. Per-machine, never in the tracked repo or the notes root.
_ESR_FILE="$_INGEST_CFG/email-service-read"
if [ -s "$_ESR_FILE" ]; then
  export EMAIL_SERVICE_READ="$(tr -d '[:space:]' < "$_ESR_FILE")"
else
  export EMAIL_SERVICE_READ="${EMAIL_SERVICE_READ:-}"
fi

# ── SENTINEL PAUSE GATE ───────────────────────────────────────────────────────────────────────
# On a DANGER verdict, shared/gate/sentinel_response.py's pause_source() appends the source to this
# exact file (its own PAUSE_FILE default). This gate makes the pause REAL: a paused source is skipped
# on every run until a human clears it by hand — Sentinel never auto-resumes. Exit 0 on the skip so a
# future scheduler's own breaker (if one is ever built) never counts a deliberate pause as a failure.
_INGEST_PAUSE_FILE="$_INGEST_CFG/sentinel-paused-sources"
ingest_check_paused() {                      # $1 = source key (job name, matching --source)
  [ -f "$_INGEST_PAUSE_FILE" ] || return 0
  if grep -qxF "$1" "$_INGEST_PAUSE_FILE" 2>/dev/null; then
    echo "[$1] PAUSED by Sentinel (danger) — skip until a human un-pauses ($_INGEST_PAUSE_FILE)."
    exit 0
  fi
}

# ── HEADLESS AUTH ─────────────────────────────────────────────────────────────
# (1) claude SUBSCRIPTION token — a cron/launchd background session can't read the macOS login
#     keychain where a normal interactive `claude` login lives. (2) gws isolated keychain-free creds
#     — gws keeps its own encryption key in the login keychain too, so a headless run needs its own
#     file-based credential profile. (3) a cheap pre-flight so a broken-auth runner aborts fast
#     instead of spawning a claude that can't reach Google.
# One-time per machine (from an interactive session): `claude setup-token` → save the token to
#   $_INGEST_CFG/claude-oauth-token; `gws auth export --unmasked > $_INGEST_CFG/gws-credentials.json
#   && chmod 600 "$_"`.
# AUTH is split so callers that don't need Google can skip it: ingest_load_gws alone for a pure
# local health emitter, ingest_load_auth (= claude + gws) for anything that fires `claude -p` and
# also needs Google.
ingest_load_claude() {   # claude OAuth subscription token — for any runner that fires `claude -p`
  # ⚖ FIXED 2026-08-15: this used to hand-roll the check and `exit 3` on a missing token file. That
  # is a REAL FAILURE under system/pulse-config.md's exit-code contract ("anything else"), so on a
  # fresh install — where no token file exists until the person runs the one-time `claude
  # setup-token` — three ticks would trip Pulse's 3-strike breaker and system-health.py would
  # render the job DOWN/severity:error permanently, auto-disabling a runner the student never got
  # to configure. The correct code is 75 = "this job's OWN preflight declined to run this tick"
  # -> counted `skipped`, never a fault.
  # This was the THIRD of five identical hand-rolled copies; the same bug had already been fixed
  # twice (archivist-run.lib.sh, planning-weekly-prime-run.sh) without reaching this one — which is
  # exactly why the check now lives in ONE place, system/tools/claude-auth.lib.sh, sourced at the
  # top of this file. ⛔ Do not re-inline it.
  # Still an `exit`, not a `return`: every caller of this lib treats auth as a hard precondition
  # before the run proper, and its own USAGE block above documents the call as terminal.
  require_claude_token "${1:-ingest}" || exit 75
}

ingest_load_gws() {      # gws keychain-free isolated creds + pre-flight
  local job="$1"
  # ⚖ FIXED 2026-08-15: this used to hand-roll the check and `exit 3` on a missing creds file. That
  # is a REAL FAILURE under system/pulse-config.md's exit-code contract ("anything else"), so three
  # ticks trip Pulse's 3-strike breaker and system-health.py renders the job DOWN/severity:error
  # PERMANENTLY. ⭐ And unlike the claude-token twin above, this branch is not a day-one-only
  # condition: it is PERMANENTLY true for anyone who never connects a Google account, which on a
  # fresh install is nearly everyone — so rc=3 here auto-disabled a runner for the majority case.
  # The correct code is 75 = "this job's OWN preflight declined to run this tick" -> `skipped`.
  # This was the SIXTH copy of that same hand-rolled branch and the first REACHABLE one (the three
  # fixed an hour earlier — calendar-store-sync, tasks-store-sync, email-summary-write — were
  # latent, with no scheduler row pointing at them yet). Eleven copies existed in all, which is
  # exactly why the check now lives in ONE place, system/tools/gws-auth.lib.sh, sourced at the top
  # of this file. ⛔ Do not re-inline it.
  # Still an `exit`, not a `return`: every caller of this lib treats auth as a hard precondition
  # before the run proper, and this lib's USAGE block documents the call as terminal — identical to
  # ingest_load_claude directly above.
  # REQUIRED, not optional: every caller of ingest_load_gws reads Gmail, and the new-mail gate and
  # the run proper are both meaningless without it.
  require_gws_credentials "$job" || exit 75
  # ── SEPARATE CHECK, SEPARATE CODE — deliberately NOT folded into the stand-down above. ──
  # Reaching this line means credentials EXIST and parse, i.e. this person HAS configured Google. A
  # failing live call is therefore a transient/infra condition, not "not set up yet": rc=2 = "held,
  # never trips the breaker" in pulse-config.md's table, which is the correct bucket and is what
  # the three sibling runners do verbatim. Collapsing it into 75 would report a CONFIGURED machine
  # as unconfigured and hide genuinely dead auth forever. Left inline (not in gws-auth.lib.sh) for
  # the same reason: it ends FATAL here and warn-only in planning-vault/planning-diary, and that difference
  # in severity is real, not noise.
  # RETRY the gws pre-flight (3x/4s) before declaring failure — a single getProfile call can fail on
  # a transient blip (token mid-refresh, momentary API hiccup); converting that into a brief wait
  # instead of an immediate hard failure avoids flapping a runner whose auth is actually fine.
  _GWS_PREFLIGHT_OK=0
  for _gws_try in 1 2 3; do
    if "$GWS_BIN" gmail users getProfile --params '{"userId":"me"}' >/dev/null 2>&1; then _GWS_PREFLIGHT_OK=1; break; fi
    if [ "$_gws_try" -lt 3 ]; then echo "[gws] pre-flight attempt $_gws_try failed — retry in 4s…"; sleep 4; fi
  done
  if [ "$_GWS_PREFLIGHT_OK" -ne 1 ]; then
    echo "[$job] FATAL: gws pre-flight failed — Google auth not healthy via isolated creds. Aborting before launch."; exit 2
  fi
}

ingest_load_auth() {     # FULL auth (claude + gws)
  ingest_load_claude "$1"
  ingest_load_gws "$1"
}

# ── SINGLE-INSTANCE LOCK ──────────────────────────────────────────────────────
# A run can take minutes; without a lock a second invocation (a second cron tick, a person running it
# twice) spawns a DUPLICATE. mkdir is atomic. Stale-steal after 25m (a generous watchdog ceiling +
# buffer) in case a prior run was hard-killed and never cleaned up after itself.
_INGEST_LOCKDIR=""
ingest_acquire_lock() {
  local job="$1"; _INGEST_LOCKDIR="/tmp/claudeops-${job}.lock"
  if ! mkdir "$_INGEST_LOCKDIR" 2>/dev/null; then
    _lock_mtime="$(stat -c %Y "$_INGEST_LOCKDIR" 2>/dev/null || stat -f %m "$_INGEST_LOCKDIR" 2>/dev/null || echo 0)"
    case "$_lock_mtime" in ''|*[!0-9]*) _lock_mtime=0 ;; esac
    if [ -d "$_INGEST_LOCKDIR" ] && [ "$(( $(date +%s) - _lock_mtime ))" -gt 1500 ]; then
      echo "[$job] stale lock (>25m) — stealing."; rm -rf "$_INGEST_LOCKDIR"
      mkdir "$_INGEST_LOCKDIR" 2>/dev/null || { echo "[$job] lock race — skip."; exit 0; }
    else echo "[$job] another run in progress — skip this tick."; exit 0; fi
  fi
  trap '_ingest_cleanup' EXIT
}
_ingest_cleanup() { [ -n "${_INGEST_LOCKDIR:-}" ] && rm -rf "$_INGEST_LOCKDIR" 2>/dev/null; }

# ── CHEAP NEW-MAIL GATE ───────────────────────────────────────────────────────
# Spawning claude costs tokens even for a no-op. Before spawning, ask Gmail (cheap) whether anything
# NEW landed in <label> since the last successfully-processed tick. ECHOES the marker epoch (the
# work-list cutoff: process only mail after it); exits 0 cheap if nothing new. First run seeds the
# marker to NOW so an existing backlog is never avalanched on — that's a deliberate supervised/manual
# pass. Marker is machine-local (never in the tracked repo or the notes root).
_INGEST_MARKER_FILE=""; INGEST_MARKER_CANDIDATE=""
# ⚠️ CALL THIS INLINE — NEVER via $(...). It `exit`s the RUNNER on the cheap paths (no marker / no new
# mail). `exit` inside a $(...) command-substitution exits only the SUBSHELL, so the runner would sail
# on with an EMPTY cutoff and silently process the WHOLE backlog. So it returns the cutoff in the
# GLOBAL $INGEST_CUTOFF (not stdout), to force inline use.
ingest_new_mail_gate() {
  local job="$1" label="$2"
  INGEST_CUTOFF=""
  _INGEST_MARKER_FILE="$_INGEST_CFG/${job}-last-seen"; mkdir -p "$_INGEST_CFG" 2>/dev/null
  local marker; marker="$(tr -cd '0-9' < "$_INGEST_MARKER_FILE" 2>/dev/null)"
  if [ -z "$marker" ]; then
    date +%s > "$_INGEST_MARKER_FILE"
    echo "[$job] no marker — seeded to now; existing backlog left for a supervised/manual pass. exit." >&2
    exit 0
  fi
  local q="label:${label} after:${marker}"
  local new_count
  new_count="$("$GWS_BIN" gmail users messages list --params "{\"userId\":\"me\",\"q\":\"$q\",\"maxResults\":1}" 2>/dev/null | python3 -c "
import sys, json
try: d = json.load(sys.stdin)
except Exception: d = {}
print(len(d.get('messages', [])))" 2>/dev/null || echo 0)"
  if [ "${new_count:-0}" -lt 1 ]; then
    echo "[$job] no new mail in ${label} since marker ($marker) — exit cheap (no claude, no tokens)." >&2
    exit 0
  fi
  echo "[$job] new mail detected in ${label} (after $marker) — proceeding." >&2
  # Capture the candidate NOW (pre-run) so mail arriving DURING the run isn't skipped — it'll be
  # > this and caught next tick. Committed only on SUCCESS by ingest_finish.
  INGEST_MARKER_CANDIDATE="$(date +%s)"
  INGEST_CUTOFF="$marker"   # GLOBAL (not stdout) — the work-list cutoff; caller reads $INGEST_CUTOFF
}

# ── SENTINEL GATE — flow a per-item read THROUGH the on-path ingest gate ────────────────────────
# Piped through shared/gate/ingest_gate.py, so a read is sanitize→scan→provenance-tag→
# Sentinel-route in ONE on-path call. The gate enforces the email FLAG-never-DANGER invariant
# internally and writes its own event + status-tile update — this is a thin exit-code mapper, no
# separate logging here (see the header note on why the older per-item logger was dropped).
# Contract: exit 0 = clean/flag → caller CONTINUES · exit 2 = DANGER → caller HALTS this item.
# GRACEFUL: gate tool absent → continue (never blocks a runner on a missing optional dependency).
INGEST_GATE_TOOL="$CODE_ROOT/shared/gate/ingest_gate.py"
ingest_gate_check() {   # $1=desk  $2=source_type(email|web|file|calendar|api)  $3=item  $4=raw_content  $5=message_id(opt)
  [ -f "$INGEST_GATE_TOOL" ] || { echo "[sentinel] gate tool absent — skip check (continue)." >&2; return 0; }
  local desk="$1" stype="$2" item="$3" raw="$4" mid="${5:-}"
  local args=(--desk "$desk" --source-type "$stype" --item "$item")
  [ -n "$mid" ] && args+=(--message-id "$mid")
  local rc
  printf '%s' "$raw" | python3 "$INGEST_GATE_TOOL" "${args[@]}" >/dev/null 2>&1; rc=$?
  if [ "$rc" -eq 2 ]; then echo "[sentinel] DANGER on $item — halt (gate)." >&2; return 2; fi
  return 0
}

# ── LAUNCH + WATCHDOG ─────────────────────────────────────────────────────────
# Launch from the given working directory (so a caller can load a specific CLAUDE.md context, if it
# has one). Watchdog hard-kills a hung run. Sets INGEST_RC.
#
# ⭐ AN UNREACHABLE MODEL IS NOT A CLEAN RESULT. Measured (system/build-rules-index.md's
# MODEL-REACH-RULE): when `claude` cannot be found or fails to launch, stdout is EMPTY and the shell
# exit is 127 — indistinguishable, to a caller that only checks "did it print anything", from "the
# model ran and found nothing." In a headless/unattended run nobody is watching, so that ambiguity is
# invisible forever. Two things guard against it landing as silent success here:
#   1. a PRE-FLIGHT check below: if $CLAUDE_BIN does not resolve to something actually runnable, this
#      function refuses to launch at all and sets INGEST_RC=127 explicitly, with a loud FATAL line —
#      rather than letting a bad exec silently produce the same 127 with no explanation.
#   2. INGEST_RC is never treated as success by anything downstream unless it is exactly 0 —
#      ingest_finish (below) only advances the retry marker on INGEST_RC -eq 0, so 127 (unreachable),
#      137 (watchdog SIGKILL), or any other non-zero code all fail CLOSED: the marker does not
#      advance and the same work is retried next run. This was already true of the donor's exit-code
#      propagation; the explicit check + labelled log line are what's added here.
INGEST_RC=1
ingest_run_claude() {
  local model="$1" watchdog="$2" prompt="$3" work_dir="$4"
  cd "$work_dir" || { echo "FATAL: cannot cd to $work_dir"; exit 1; }
  if [ -z "$CLAUDE_BIN" ] || { [ "$CLAUDE_BIN" != "claude" ] && [ ! -x "$CLAUDE_BIN" ]; } ; then
    echo "[ingest] FATAL: claude binary not reachable (resolved to '$CLAUDE_BIN') — this is a FAILURE, not a clean 'found nothing' result."
    INGEST_RC=127
    return 127
  fi
  echo "[ingest] launching headless claude ($model, watchdog ${watchdog}s)…"
  "$CLAUDE_BIN" -p "$prompt" --model "$model" --dangerously-skip-permissions &
  local cpid=$!
  ( sleep "$watchdog"; kill -9 "$cpid" 2>/dev/null ) & local wpid=$!
  wait "$cpid" 2>/dev/null; INGEST_RC=$?
  kill "$wpid" 2>/dev/null; wait "$wpid" 2>/dev/null
  case "$INGEST_RC" in
    0)   echo "[ingest] claude exit: 0" ;;
    127) echo "[ingest] claude exit: 127 — binary not found / not executable at run time. Treated as FAILURE, never success." ;;
    137) echo "[ingest] claude exit: 137 — watchdog killed a hung run after ${watchdog}s. Treated as FAILURE, never success." ;;
    *)   echo "[ingest] claude exit: $INGEST_RC" ;;
  esac
}

# ── FINISH ────────────────────────────────────────────────────────────────────
# On rc=0 advance the high-water marker (don't re-spawn on the same mail). Non-zero (incl. watchdog
# kill 137, unreachable-binary 127) leaves the marker so new mail retries next run.
ingest_finish() {
  local job="$1"
  if [ "$INGEST_RC" -eq 0 ] && [ -n "$INGEST_MARKER_CANDIDATE" ] && [ -n "$_INGEST_MARKER_FILE" ]; then
    echo "$INGEST_MARKER_CANDIDATE" > "$_INGEST_MARKER_FILE"
    echo "[$job] marker advanced → $INGEST_MARKER_CANDIDATE (no re-spawn until newer mail)."
  else
    echo "[$job] rc=$INGEST_RC — marker NOT advanced; new mail retries next run."
  fi
  exit "$INGEST_RC"
}
