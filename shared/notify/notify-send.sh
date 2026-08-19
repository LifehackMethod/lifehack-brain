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
#                  [--priority normal|critical] [--url <drive-link>] \
#                  [--title <title>] [--tags <tag1,tag2>]
#
# Exit 0  = sent (or deliberately SUPPRESSED by the governor — not an error).
# Exit 1  = send attempted but FAILED (network/curl).
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

SOURCE="" MESSAGE="" PRIORITY="normal" URL="" TITLE="" TAGS="" MARKDOWN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --source)   SOURCE="${2:-}";   shift 2 ;;
    --message)  MESSAGE="${2:-}";  shift 2 ;;
    --priority) PRIORITY="${2:-}"; shift 2 ;;
    --url)      URL="${2:-}";      shift 2 ;;
    --title)    TITLE="${2:-}";    shift 2 ;;
    --tags)     TAGS="${2:-}";     shift 2 ;;
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
export NOTIFY_QUIET_START NOTIFY_QUIET_END NOTIFY_DAILY_CAP NOTIFY_DEDUP_HOURS
_TMP="${TMPDIR:-/tmp}"
if ! python3 "$GOVERNOR" "$SOURCE" "$MESSAGE" "$PRIORITY" >/dev/null 2>"$_TMP/notify-gov.$$"; then
  reason="$(cat "$_TMP/notify-gov.$$" 2>/dev/null)"; rm -f "$_TMP/notify-gov.$$"
  echo "notify-send: ${reason:-suppressed by the gate}" >&2
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

# Dry-run: print what WOULD be sent, no network. (Setup verification.)
if [ "${NOTIFY_DRY_RUN:-0}" = "1" ]; then
  echo "DRY_RUN would POST -> $SERVER/<your topic, not printed>"
  echo "  priority: $NTFY_PRIO  title: '${TITLE:-}'  tags: '${TAGS:-}'  click: '${URL:-}'  markdown: $MARKDOWN"
  echo "  body: $MESSAGE"
  exit 0
fi

# --max-time = circuit breaker: a hung network must never wedge a cron job.
if curl -sS --max-time 10 "${HDRS[@]}" -d "$MESSAGE" "$SERVER/$TOPIC" >/dev/null 2>"$_TMP/notify-curl.$$"; then
  rm -f "$_TMP/notify-curl.$$"
  echo "notify-send: sent ($SOURCE -> $SERVER)"    # the topic is never printed — it is a secret
  exit 0
else
  err="$(cat "$_TMP/notify-curl.$$" 2>/dev/null)"; rm -f "$_TMP/notify-curl.$$"
  echo "notify-send: SEND FAILED — ${err:-curl error}" >&2
  exit 1
fi
