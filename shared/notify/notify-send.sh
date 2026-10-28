#!/usr/bin/env bash
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: ONE place that turns "something happened" into a buzz on your phone — gated so it
#      cannot spam you, and disciplined so it cannot leak. Everything that wants your
#      attention calls this; nothing posts to the notification service directly. Two reasons
#      that matters: one gate is the only way a cap can actually hold, and one exit is the
#      only way to be sure nothing sensitive is going out in a push body.
# WHAT: finds your topic -> asks notify-governor.py for permission -> only on ALLOW posts a
#       TEASER. The teaser is the doorbell, never the parcel.
# REDIRECT: to push something, call this. Set NTFY_TOPIC, or put it in
#           ~/.config/lifehack/ntfy-topic. The gate is shared/notify/notify-governor.py.
# UPDATED: 2026-08-11 (ported; your topic comes from your own config, not a file in this repo)
# ─────────────────────────────────────────────────────────────────────────────
# notify-send.sh — outbound push dispatch (ntfy), governor-gated.
#
# Usage:
#   notify-send.sh --source <name> --message <teaser> \
#                  [--priority normal|critical|recovery] [--url <drive-link>] \
#                  [--title <title>] [--tags <tag1,tag2>]
#
# Exit 0  = sent (or deliberately SUPPRESSED by the governor — not an error).
# Exit 1  = send attempted but FAILED (network/curl), or a quiet-hours alert could not be queued.
# Exit 3  = the governor's state file is CORRUPT (5.9(e)): named on stderr, and the one alarm about it is still pushed.
# Exit 2  = setup/usage error (no topic configured, bad args).
#
# DISCIPLINE, and it is the whole reason this wrapper exists rather than a bare curl:
# --message is a TEASER. A push travels through somebody else's service, lands on a lock
# screen, and is read by whoever is holding the phone. Names, amounts, what a document
# said — none of that goes in the body. Put it behind --url, behind whatever asks for a
# login. The push says "go and look", never "here it is".

set -u
# CODE_ROOT = this script's OWN repo root (clone or Drive), so notify-send always uses
# the governor + config sitting next to it — never a hardcoded Drive copy that can go
# stale vs the canonical clone (the "dormant fix" residency bug, fixed 2026-06-18).
CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GOVERNOR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/notify-governor.py"

GOVERNOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── --flush-deferred: replay quiet-hours-queued sends (T10.A3 OL-N1 ⑥) ────────────────────────
# A separate mode, no --source/--message required. Meant to be called on every Pulse tick (pulse.sh
# does this — see that file) so a normal-priority digest queued at 23:50 for quiet hours actually
# reaches the phone once quiet hours lift, instead of being silently lost forever.
if [ "${1:-}" = "--flush-deferred" ]; then
  export NOTIFY_QUIET_START NOTIFY_QUIET_END NOTIFY_DAILY_CAP NOTIFY_DEDUP_HOURS NOTIFY_DEFERRED_MAX_AGE_HOURS
  _FE="${TMPDIR:-/tmp}/notify-flush.$$"
  out="$(python3 "$GOVERNOR_DIR/notify-governor.py" --flush-deferred 2>"$_FE")"; _frc=$?
  if [ "$_frc" -ne 0 ]; then   # 5.9(d): a failed flush is NAMED and fails the call (the deferred alerts are still queued, not lost)
    echo "notify-send: --flush-deferred FAILED (rc=$_frc): $(cat "$_FE")" >&2; rm -f "$_FE"; exit "$_frc"
  fi
  [ -s "$_FE" ] && cat "$_FE" >&2
  rm -f "$_FE"
  [ -z "$out" ] && exit 0
  rc_all=0
  while IFS=$'\t' read -r d_source d_message d_title d_tags d_prio d_url; do
    [ -n "$d_source" ] || continue
    args=(--source "$d_source" --message "$d_message")
    [ -n "$d_title" ] && args+=(--title "$d_title")
    [ -n "$d_tags" ]  && args+=(--tags "$d_tags")
    [ -n "$d_prio" ] && [ "$d_prio" != "normal" ] && args+=(--priority "$d_prio")   # 2.5b: a deferred recovery stays cap-exempt
    [ -n "$d_url" ]   && args+=(--url "$d_url")
    bash "${BASH_SOURCE[0]}" "${args[@]}" || rc_all=1
  done <<< "$out"
  exit "$rc_all"
fi

SOURCE="" MESSAGE="" PRIORITY="normal" URL="" TITLE="" TAGS="" MARKDOWN=0 IDENTITY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --source)   SOURCE="${2:-}";   shift 2 ;;
    --message)  MESSAGE="${2:-}";  shift 2 ;;
    --priority) PRIORITY="${2:-}"; shift 2 ;;
    --url)      URL="${2:-}";      shift 2 ;;
    --title)    TITLE="${2:-}";    shift 2 ;;
    --tags)     TAGS="${2:-}";     shift 2 ;;
    --identity) IDENTITY="${2:-}"; shift 2 ;;   # OL-N1 ④: dedup on THIS, not on --message text
    --markdown) MARKDOWN=1;        shift 1 ;;   # render body as markdown in the ntfy app/web view
    *) echo "notify-send: unknown arg '$1'" >&2; exit 2 ;;
  esac
done

[ -n "$SOURCE" ]  || { echo "notify-send: --source required" >&2; exit 2; }
[ -n "$MESSAGE" ] || { echo "notify-send: --message required" >&2; exit 2; }

# ── Where your topic comes from ───────────────────────────────────────────────
# A topic is a shared secret in disguise: anyone who knows the string can read every
# notification you send to it. So it is NOT a file in this repository — it lives with your
# own config, in the same place as everything else that is yours. Environment first, so a
# scheduled job or a test can override it without touching your setup.
TOPIC_FILE="${NTFY_TOPIC_FILE:-$HOME/.config/lifehack/ntfy-topic}"
TOPIC="${NTFY_TOPIC:-}"
if [ -z "$TOPIC" ] && [ -r "$TOPIC_FILE" ]; then
  TOPIC="$(tr -d '[:space:]' < "$TOPIC_FILE")"
fi
SERVER="${NTFY_SERVER:-https://ntfy.sh}"
if [ -z "$TOPIC" ]; then
  echo "notify-send: no topic set, so there is nowhere to send this." >&2
  echo "notify-send: choose a long unguessable string — anyone who knows it can read your" >&2
  echo "notify-send: notifications — subscribe to it in the app, then:" >&2
  echo "notify-send:   mkdir -p \"\$(dirname "$TOPIC_FILE")\" && umask 077 && printf %s '<your-topic>' > $TOPIC_FILE" >&2
  exit 2
fi

# ── Governor gate (anti-spam) — pass tuning through as env ────────────────────
export NOTIFY_QUIET_START NOTIFY_QUIET_END NOTIFY_DAILY_CAP NOTIFY_DEDUP_HOURS NOTIFY_MISCONFIG_DEDUP_HOURS
_TMP="${TMPDIR:-/tmp}"
# 5.9(e): governor exit 3 = its state file is CORRUPT. Say so loudly on stderr, DO NOT swallow it as "suppressed", and still send the one
# alarm about the problem itself (the governor cannot gate it -- it is the thing that is broken), then fail the call (exit 3).
FINAL_RC=0
python3 "$GOVERNOR" "$SOURCE" "$MESSAGE" "$PRIORITY" "$IDENTITY" >/dev/null 2>"$_TMP/notify-gov.$$"; _grc=$?
if [ "$_grc" -eq 3 ]; then
  echo "notify-send: $(cat "$_TMP/notify-gov.$$")" >&2; rm -f "$_TMP/notify-gov.$$"
  _orig_source="$SOURCE"
  SOURCE="notify-governor"; TITLE="Notify governor state corrupt"; PRIORITY="critical"; TAGS="rotating_light"; URL=""
  MESSAGE="The notification governor state file ($(basename "${NOTIFY_STATE_FILE:-lifehack-notify-state.json}")) is corrupt, so an alert from '$_orig_source' was NOT sent. Fix or delete the file."
  FINAL_RC=3
elif [ "$_grc" -ne 0 ]; then
  reason="$(cat "$_TMP/notify-gov.$$" 2>/dev/null)"; rm -f "$_TMP/notify-gov.$$"
  echo "notify-send: ${reason:-suppressed by the gate}" >&2
  # OL-N1 ⑥: a normal-priority send dropped for QUIET HOURS SPECIFICALLY (never dedup, never the
  # cap — both of those are correct, permanent drops) gets queued so it can still reach the phone
  # once quiet hours lift, instead of being lost for good. See --flush-deferred above.
  case "$reason" in
    "SUPPRESS: quiet hours"*)
      if ! python3 "$GOVERNOR" --queue-deferred "$SOURCE" "$MESSAGE" "$TITLE" "$TAGS" "$URL" "$PRIORITY" >/dev/null; then
        # 5.9(d): the queue write failed -> this alert is LOST. Say so on stderr and fail the call; never "suppressed, fine".
        echo "notify-send: LOST: could not queue the quiet-hours alert from '$SOURCE' (queue write failed) -- it will not be delivered" >&2
        exit 1
      fi
      ;;
  esac
  exit 0   # being suppressed is the system working — never report it as a failure
fi
rm -f "$_TMP/notify-gov.$$"

# ── Compose + send ────────────────────────────────────────────────────────────
# ntfy priority: 1 min · 3 default · 5 urgent. critical -> urgent.
NTFY_PRIO=3; [ "$PRIORITY" = "critical" ] && NTFY_PRIO=5

HDRS=(-H "Priority: $NTFY_PRIO")
[ -n "$TITLE" ] && HDRS+=(-H "Title: $TITLE")
[ -n "$TAGS" ]  && HDRS+=(-H "Tags: $TAGS")
[ -n "$URL" ]   && HDRS+=(-H "Click: $URL")
[ "$MARKDOWN" = "1" ] && HDRS+=(-H "Markdown: yes")

# TEST-ONLY seam (self-monitoring 2.0): LIFEHACK_NOTIFY_LOG. This sits AFTER the governor, so the governor's
# quiet hours, dedup and daily cap all ran; where this script would POST to ntfy it appends one line
# "title | message | identity | priority" to the file instead, so the log holds exactly what would reach the
# phone. No network. Inert when unset.
if [ -n "${LIFEHACK_NOTIFY_LOG:-}" ]; then
  printf '%s | %s | %s | %s\n' "$TITLE" "$MESSAGE" "$IDENTITY" "$PRIORITY" >> "$LIFEHACK_NOTIFY_LOG"
  exit "$FINAL_RC"
fi

# Dry-run: print what WOULD be sent, no network. (Setup verification.)
if [ "${NOTIFY_DRY_RUN:-0}" = "1" ]; then
  echo "DRY_RUN would POST -> $SERVER/<your topic, not printed>"
  echo "  priority: $NTFY_PRIO  title: '${TITLE:-}'  tags: '${TAGS:-}'  click: '${URL:-}'  markdown: $MARKDOWN"
  echo "  body: $MESSAGE"
  exit "$FINAL_RC"
fi

# --max-time = circuit breaker: a hung network must never wedge a cron job.
if curl -sS --max-time 10 "${HDRS[@]}" -d "$MESSAGE" "$SERVER/$TOPIC" >/dev/null 2>"$_TMP/notify-curl.$$"; then
  rm -f "$_TMP/notify-curl.$$"
  echo "notify-send: sent ($SOURCE -> $SERVER)"    # the topic is never printed — it is a secret
  exit "$FINAL_RC"
else
  err="$(cat "$_TMP/notify-curl.$$" 2>/dev/null)"; rm -f "$_TMP/notify-curl.$$"
  echo "notify-send: SEND FAILED — ${err:-curl error}" >&2
  exit 1
fi
