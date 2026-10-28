#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: Shared core for the Standing Archivist's two Pulse runners
#      (archivist-audit-run.sh weekly · archivist-deepmine-run.sh monthly). Both do the SAME
#      machinery — headless auth, single-instance lock + watchdog, run a read-only
#      `claude -p` against the archivist skill, then read its JSON summary sidecar and write
#      the Helm-equivalent status tile + a governor-gated ping. Only the PROMPT, cadence, and
#      output filenames differ — those live in the thin wrappers.
# GUARDS: the Archivist is READ-ONLY forever — the claude session may write ONLY the two
#      output files named in its own prompt (a log + a proposals file, per
#      `.claude/skills/archivist-audit/SKILL.md` / `archivist-deepmine/SKILL.md`'s own
#      documented output contract). It NEVER executes proposals — that is a human, via the
#      next `/save`, main session, human-gated (the donor's `/archivist-review` was retired
#      2026-07-11; both ported skills already say so).
#
# ⚖ PORT NOTE (donor: system/tools/archivist-run.lib.sh). Three things dropped, not translated:
#   1. The LEAD-MACHINE gate (`require_primary`, `machine-token.sh`) — this product is one
#      machine by design, same drop as every other ported runner's own port note.
#   2. The Google-Drive "tappable stable file" upload (`_upload_queue`, a hardcoded personal
#      Drive folder id as its default). Both ported skills already document a DIFFERENT,
#      simpler output contract — the queue lands directly under `<notes>/records/proposals/`
#      and `<notes>/records/logs/`, which a person reaches through their own notes, no Drive
#      API round-trip and no folder id to leak. Dropping the upload does not lose the
#      capability; it follows the skill's OWN already-ported contract instead of the donor's
#      older one.
#   3. `~/.config/claudeops/*` paths -> `~/.config/lifehack/*` (this repo's established
#      machine-local config home).
#
# Contract — a wrapper sources this file, sets the vars below, then calls run_archivist:
#   ARCH_MODE          "audit" | "deepmine"   (lock name + tile sub-key + default filenames)
#   ARCH_LABEL         log prefix, e.g. "archivist-audit"
#   ARCH_WATCHDOG      hard timeout seconds (1800; max 3600 — NEVER 600)
#   ARCH_PROMPT        the full instruction to the headless read-only claude session
#   ARCH_PING_TITLE    ntfy title teaser, e.g. "Archivist — weekly audit"
#   ARCH_QUEUE_FILE    (optional) absolute path the claude session writes the proposals/log to
#   ARCH_SUMMARY_FILE  (optional) absolute path the claude session writes the JSON sidecar to
#   ARCH_MODEL         (optional) defaults to sonnet (mechanical/structural review, not
#                       judgment a human relies on unchecked — it proposes, never decides)
# Sidecar JSON the claude session MUST write to ARCH_SUMMARY_FILE:
#   {"status":"OK"|"NEEDS_REVIEW","finding_count":<int>,"headline":"<short teaser>"}
# ─────────────────────────────────────────────────────────────────────────────
set -u

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# The ONE headless-claude credential preflight (require_claude_token) — shared with the four other
# runners that fire `claude -p`, so the rc=75 stand-down contract cannot drift between copies again.
# A missing library is a REAL defect (exit 1), never a stand-down.
. "$CODE_ROOT/system/tools/claude-auth.lib.sh" || {
  echo "FATAL: cannot source $CODE_ROOT/system/tools/claude-auth.lib.sh"; exit 1; }
# Its gws sibling — the ONE headless-Google credential preflight, shared with the ten other runners
# that reach Google. Same rule: a missing library is a REAL defect (exit 1), never a stand-down.
. "$CODE_ROOT/system/tools/gws-auth.lib.sh" || {
  echo "FATAL: cannot source $CODE_ROOT/system/tools/gws-auth.lib.sh"; exit 1; }

# The data root, through the ONE resolver — never a hardcoded personal Drive path.
DATA="$(python3 "$CODE_ROOT/shared/brain_root.py" --quiet 2>/dev/null)"

# Reach `claude` at runtime, never a hardcoded personal path (house standard).
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude 2>/dev/null)}"
if [ -z "$CLAUDE_BIN" ]; then
  for _cb in "$HOME/.local/bin/claude" /opt/homebrew/bin/claude /usr/local/bin/claude; do
    [ -x "$_cb" ] && CLAUDE_BIN="$_cb" && break
  done
fi
CLAUDE_BIN="${CLAUDE_BIN:-claude}"

# (the gws credential path used to be hardcoded here; it now lives in gws-auth.lib.sh's
#  gws_creds_path, and the helper publishes what it looked at as $GWS_CREDS_FILE)
ARCH_MODEL="${ARCH_MODEL:-claude-sonnet-4-6}"

_alog() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${ARCH_LABEL}: $*"; }

# ── status tile: one shared archivist.json under state/status/, each mode owns its own sub-key ──
_write_tile() {  # args: status count summary
  local status="${1:-SILENT}" count="${2:-0}" summary="${3:-}"
  [ -n "$DATA" ] || { _alog "WARN: no data root — skipping tile write."; return 0; }
  # argv, never string-interpolated into the python source — a headline/summary containing a
  # quote (very likely — "can't", "3 items — don't skip") would otherwise break or inject.
  python3 -c 'import json,sys; print(json.dumps({sys.argv[1]: {"finding_count": int(sys.argv[2]), "headline": sys.argv[3]}}))' \
    "$ARCH_MODE" "${count:-0}" "$summary" | \
    python3 "$CODE_ROOT/system/tools/emit_status.py" \
      --out "$DATA/state/status/archivist.json" --desk archivist --pulse-job "archivist-$ARCH_MODE" \
      --stale-after-s 1209600 --status "$status" --rc 0 --summary "$summary" --json - || \
    _alog "WARN: tile write failed (non-fatal)"
}

_ping() {  # args: title message
  bash "$CODE_ROOT/shared/notify/notify-send.sh" --source archivist \
    --title "$1" --message "$2" || _alog "WARN: notify-send failed (rc=$?) — the ping was not sent"
}

# 5.7 ENVELOPE. Dry mode (`--dry`, or JOB_RUN_FORCED=1 from a by-hand `job-run.sh --force`): a real run is NOT bounded -- it launches a
# whole-tree model session (up to the watchdog), writes the log/proposals/sidecar, the audit's territory map (check 8), the status tile,
# a phone ping and (deepmine) the rotation ledger. That is more than "its own output", so a forced run is DRY: it does every READ
# (the notes root, the due-desk pick), prints what it WOULD do, and writes nothing -- no lock, no file, no tile, no ping, no ledger,
# no receipt, no model call.
# Exit codes: 0 ran and proved its work (receipt written) | 75 stood down (no token, a live owner holds the lock, NOTHING DUE) |
#             1 or other = a real failure, named on stderr.
_arch_fail() { echo "[${ARCH_LABEL}] FAILED at step '$1': $2" >&2; }

run_archivist() {
  local dry=0 _a
  [ "${JOB_RUN_FORCED:-0}" = 1 ] && dry=1
  for _a in "$@"; do [ "$_a" = "--dry" ] && dry=1; done
  ARCH_DRY="$dry"
  if [ -z "$DATA" ]; then
    _alog "FATAL: no notes root set — nothing to audit. Set one: python3 shared/brain_root.py --set <folder>"
    return 2
  fi

  # 1) HEADLESS AUTH — claude OAuth token (cron can't read the login keychain).
  # STOOD DOWN, not a fault. No token file is true on day one of EVERY install (and stays true
  # until the person runs the one-time setup), so this branch fires on every tick of a fresh
  # machine. rc=75 = "this job's OWN preflight declined to run this tick" per
  # system/pulse-config.md's exit-code contract — Pulse counts it `skipped`, never toward the
  # 3-strike breaker. It was `return 3` before 2026-08-15, which fell in that contract's
  # "anything else -> a real failure" bucket: three ticks with no token tripped the breaker on
  # BOTH archivist rows (this lib drives audit AND deepmine), held them 60min, and paged the
  # phone — presenting "not configured yet" as BREAKAGE, the exact inversion rc=75 exists to
  # prevent. Same fix, same reason, as calendar-store-sync-run.sh / tasks-store-sync-run.sh /
  # email-summary-write-run.sh's identical missing-credentials branches.
  # ⚖ 2026-08-15, second pass: the check itself now lives in ONE place
  # (system/tools/claude-auth.lib.sh) because this fix was applied here and in
  # planning-weekly-prime-run.sh while three sibling copies kept `exit 3`. `_alog` is passed as the
  # logger so the stand-down line keeps this lib's own timestamped "[ts] <label>: …" format.
  # `return`, never `exit` — an exit here would kill the wrapper before its own cleanup.
  if [ "$ARCH_DRY" != 1 ]; then require_claude_token "$ARCH_LABEL" _alog || return 75; fi
  # gws is OPTIONAL for the archivist — it audits the local filesystem tree, so no Google means a
  # complete audit, not a failure. (Contrast the claude token directly above, which IS required.)
  # ⚖ 2026-08-15: was a hand-rolled `[ -s "$GWS_CREDS" ]` block, one of eleven identical copies —
  # now the shared helper (gws-auth.lib.sh, sourced at the top). Two things change: `[ -s ]` passed
  # a whitespace-only or corrupt file and exported it anyway, and the absence was SILENT. The
  # helper validates, and names the absence in one non-fatal line — routed through `_alog` so it
  # keeps this lib's own timestamped "[ts] <label>: …" format. ⛔ Do not re-inline it.
  [ "$ARCH_DRY" = 1 ] || load_gws_credentials_optional "$ARCH_LABEL" _alog

  # 2) SINGLE-INSTANCE LOCK (mkdir atomic; stale-steal after watchdog+buffer).
  local lockdir steal datestamp prc
  lockdir="${LIFEHACK_RUNNER_LOCK_ROOT:-/tmp}/claudeops-${ARCH_LABEL}.lock"
  steal=$(( ARCH_WATCHDOG + 300 ))
  . "$CODE_ROOT/system/tools/runner-lock.lib.sh" || { _alog "FATAL: cannot source runner-lock.lib.sh"; return 1; }
  # 5.9(h): pid-recording lock; a live owner is a stand-down (75, not the [F2] return 0), a corrupt lock is refused and named (1).
  if [ "$ARCH_DRY" != 1 ]; then
    runner_lock_acquire "$lockdir" "$steal" "$ARCH_LABEL" || return $?
    trap "rm -rf '$lockdir'" EXIT
  fi

  # 3) DATE + PRERUN HOOK. A wrapper may define arch_prerun to choose work dynamically
  #    (the deep-mine dispatcher picks the most-overdue desk here and sets ARCH_PROMPT +
  #    desk-specific paths). Returning non-zero from arch_prerun = "nothing due -> skip clean."
  # arch_prerun: 0 = work chosen | 1 = NOTHING DUE (stand down: 75, never the [F2] "exit 0 having done nothing") | other = a real fault.
  datestamp="$(date +%F)"
  if type arch_prerun >/dev/null 2>&1; then
    arch_prerun; prc=$?
    if [ "$prc" -eq 1 ]; then _alog "prerun: nothing due this tick — standing down (75), no receipt."; return 75; fi
    if [ "$prc" -ne 0 ]; then _arch_fail prerun "arch_prerun failed (rc=$prc)"; return 1; fi
  fi
  : "${ARCH_QUEUE_FILE:=$DATA/records/logs/archivist-${datestamp}-${ARCH_MODE}.md}"
  : "${ARCH_SUMMARY_FILE:=$DATA/system/logs/archivist_${datestamp}_${ARCH_MODE}.summary.json}"
  [ -n "${ARCH_PROMPT:-}" ] || { _alog "FATAL: ARCH_PROMPT unset"; return 1; }
  if [ "$ARCH_DRY" = 1 ]; then
    echo "[${ARCH_LABEL}] DRY RUN -- nothing below is done, nothing is written (no lock, file, tile, ping, ledger, receipt or model call)"
    echo "[${ARCH_LABEL}] would work on : ${ARCH_RECEIPT_DESK:-all} (notes root $DATA)"
    echo "[${ARCH_LABEL}] would run     : one headless model session, watchdog ${ARCH_WATCHDOG}s, prompt ${#ARCH_PROMPT} chars"
    echo "[${ARCH_LABEL}] would write   : $ARCH_QUEUE_FILE"
    echo "[${ARCH_LABEL}]                 $ARCH_SUMMARY_FILE"
    echo "[${ARCH_LABEL}]                 tile $DATA/state/status/archivist.json, receipt $HOME/.config/lifehack/archivist-${ARCH_MODE}/last-run.txt"
    return 0
  fi
  mkdir -p "$(dirname "$ARCH_QUEUE_FILE")" "$(dirname "$ARCH_SUMMARY_FILE")" || { _arch_fail mkdir "cannot create the output folders"; return 1; }
  rm -f "$ARCH_QUEUE_FILE" "$ARCH_SUMMARY_FILE" || { _arch_fail clear-stale "cannot remove a prior run's output"; return 1; }  # never read a prior run's stale output

  # 4) RUN the read-only audit/mine headless, hard-bounded by the watchdog.
  cd "$DATA" || { _alog "FATAL: cannot cd to $DATA"; return 1; }
  _alog "launching headless claude ($ARCH_MODEL, watchdog ${ARCH_WATCHDOG}s)…"
  "$CLAUDE_BIN" -p "$ARCH_PROMPT" --model "$ARCH_MODEL" --dangerously-skip-permissions </dev/null &
  local cpid wpid rc
  cpid=$!
  ( sleep "$ARCH_WATCHDOG"; kill -9 "$cpid" 2>/dev/null ) & wpid=$!
  wait "$cpid" 2>/dev/null; rc=$?
  pkill -P "$wpid" 2>/dev/null; kill "$wpid" 2>/dev/null; wait "$wpid" 2>/dev/null   # the watchdog's own sleep must die too, or it holds the job log pipe open for 30 min
  _alog "claude exit: $rc"

  # 5) TOOL BROKE (non-zero / watchdog kill) -> tile=ERROR, return non-zero so Pulse's circuit
  #    breaker counts it (3 consecutive -> auto-disable + buzz). NOT a found-drift.
  if [ "$rc" -ne 0 ]; then
    _write_tile "ERROR" 0 "claude exited $rc — tool broke, not drift"
    _alog "non-zero exit — tool broke (NOT drift). Pulse breaker will handle repeats."
    # This is a PASSTHROUGH of a foreign process's exit code, so it can collide with the two codes
    # Pulse reads as "not a fault" (75 = stood down, 2 = transient). A BROKEN claude must never be
    # laundered into "skipped" — that would silently swallow a real, repeating fault. Remap those
    # two values to a plain failure; every other code passes through unchanged.
    if [ "$rc" -eq 75 ] || [ "$rc" -eq 2 ]; then
      _alog "claude's own exit $rc collides with a Pulse not-a-fault code — reporting as 1 (real failure)."
      return 1
    fi
    return "$rc"
  fi

  # 6) SUCCESS -> read the sidecar, write the tile, ping only if there's something to review.
  #    Found-drift is SUCCESS (exit 0) — only a broken tool exits non-zero.
  # The sidecar is the PROOF the session did the work: absent, empty or malformed is a failure, never a default "NEEDS_REVIEW".
  local status count headline parsed
  [ -s "$ARCH_SUMMARY_FILE" ] || { _write_tile "ERROR" 0 "no summary sidecar — run produced no proof of work"; _arch_fail sidecar "no summary sidecar at $ARCH_SUMMARY_FILE"; return 1; }
  parsed="$(python3 -c '
import json,sys
d=json.load(open(sys.argv[1]))
st=d["status"]; n=d["finding_count"]
assert st in ("OK","NEEDS_REVIEW"), "status must be OK or NEEDS_REVIEW, got %r" % (st,)
assert isinstance(n,int) and not isinstance(n,bool) and n>=0, "finding_count must be a non-negative integer"
print(st); print(n); print(str(d.get("headline","")).replace("\n"," "))
' "$ARCH_SUMMARY_FILE")" || { _write_tile "ERROR" 0 "summary sidecar is malformed"; _arch_fail sidecar "malformed sidecar $ARCH_SUMMARY_FILE"; return 1; }
  status="$(printf '%s\n' "$parsed" | sed -n 1p)"; count="$(printf '%s\n' "$parsed" | sed -n 2p)"; headline="$(printf '%s\n' "$parsed" | sed -n 3p)"
  [ -s "$ARCH_QUEUE_FILE" ] || { _write_tile "ERROR" 0 "no log written"; _arch_fail log "the session wrote no log at $ARCH_QUEUE_FILE"; return 1; }

  if [ "$status" = "OK" ] && [ "$count" = "0" ]; then
    _write_tile "OK" 0 "clean — no drift found"
    _alog "clean — no drift found. Tile OK, no ping."
  else
    _write_tile "NEEDS_REVIEW" "$count" "${headline:-review ready}"
    _ping "$ARCH_PING_TITLE" "${headline:-review ready} — $count item(s). See $(basename "$ARCH_QUEUE_FILE") in your notes."
    _alog "done — $count finding(s), pinged. (exit 0: found-drift is success)"
  fi

  # POSTRUN HOOK — runs ONLY on success (the deep-mine dispatcher stamps the desk's
  # last-mined time here so the rotation advances). The audit wrapper defines no postrun.
  if type arch_postrun >/dev/null 2>&1; then arch_postrun || { _arch_fail postrun "arch_postrun failed"; return 1; }; fi

  # RECEIPT -- only now, after every step above succeeded. One line, atomic: `<job> ok desk=<d> status=<S> findings=<n> log_bytes=<b>`.
  local rdir rfile bytes
  rdir="$HOME/.config/lifehack/archivist-${ARCH_MODE}"; rfile="$rdir/last-run.txt"
  bytes="$(wc -c < "$ARCH_QUEUE_FILE" | tr -d ' ')"
  mkdir -p "$rdir" && printf 'archivist-%s ok desk=%s status=%s findings=%s log_bytes=%s\n' \
    "$ARCH_MODE" "${ARCH_RECEIPT_DESK:-all}" "$status" "$count" "$bytes" > "$rfile.tmp" && mv "$rfile.tmp" "$rfile" \
    || { _arch_fail receipt "cannot write $rfile"; return 1; }
  return 0
}
