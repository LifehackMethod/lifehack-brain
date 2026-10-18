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

GOVERNOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── --flush-deferred: replay quiet-hours-queued sends (T10.A3 OL-N1 ⑥) ────────────────────────
# A separate mode, no --source/--message required. Meant to be called on every Pulse tick (pulse.sh
# does this — see that file) so a normal-priority digest queued at 23:50 for quiet hours actually
# reaches the phone once quiet hours lift, instead of being silently lost forever.
if [ "${1:-}" = "--flush-deferred" ]; then
  export NOTIFY_QUIET_START NOTIFY_QUIET_END NOTIFY_DAILY_CAP NOTIFY_DEDUP_HOURS NOTIFY_DEFERRED_MAX_AGE_HOURS
  out="$(python3 "$GOVERNOR_DIR/notify-governor.py" --flush-deferred 2>/dev/null)" || true
  [ -z "$out" ] && exit 0
  rc_all=0
  while IFS=$'\t' read -r d_source d_message d_title d_tags d_url; do
    [ -n "$d_source" ] || continue
    args=(--source "$d_source" --message "$d_message")
    [ -n "$d_title" ] && args+=(--title "$d_title")
    [ -n "$d_tags" ]  && args+=(--tags "$d_tags")
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

# ── PRIORITY (widened 2026-09-21) ─────────────────────────────────────────────
# ntfy carries FIVE levels (1 min .. 5 max) and the phone app can filter on them — "notify me
# for high and above" is a setting the human controls on the device, which is a far better
# volume dial than anything this script can decide for her. This wrapper used to collapse all
# five into two (everything 3, critical 5), so that filter had nothing to bite on.
# Aliases are normalised HERE, before the governor sees the value, because the governor's
# bypass logic tests the literal string "critical" — sending it "urgent" would look like a
# normal send and silently obey quiet hours. Normalising early is what stops that trap.
case "$PRIORITY" in
  min|1)                  PRIORITY="min" ;;
  low|2)                  PRIORITY="low" ;;
  normal|default|3|"")    PRIORITY="normal" ;;
  high|4)                 PRIORITY="high" ;;
  critical|urgent|max|5)  PRIORITY="critical" ;;
  misconfig)              PRIORITY="misconfig" ;;
  *) echo "notify-send: unknown --priority '$PRIORITY' (min|low|normal|high|critical|misconfig)" >&2; exit 2 ;;
esac

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
python3 "$GOVERNOR" "$SOURCE" "$MESSAGE" "$PRIORITY" "$IDENTITY" >/dev/null 2>"$_TMP/notify-gov.$$"
GOV_RC=$?
GOV_ERR="$(cat "$_TMP/notify-gov.$$" 2>/dev/null)"; rm -f "$_TMP/notify-gov.$$"
# The governor's contract: exit 0 = ALLOW; exit 1 + a stderr line beginning "SUPPRESS:" = a
# deliberate "no". ANYTHING ELSE IS A CRASH, NOT A DECISION, and a gate that could not run has
# decided nothing.
# ⚠ WHY THIS READS STDERR AND NOT THE EXIT CODE (corrected 2026-09-21, same day): the first
# version of this fix tested `rc > 1` for a crash. That can never fire -- Python exits 1 on an
# uncaught exception, which is the SAME code the governor uses for SUPPRESS. So a crash still
# read as "suppressed" and still exited 0. Caught by a simulated crash before commit. The only
# thing that tells a decision from a traceback is what was said, so that is what is tested.
case "$GOV_RC:$GOV_ERR" in
  0:*)
    : ;;   # ALLOW -- fall through to the send
  1:SUPPRESS:*)
    reason="$GOV_ERR"
    echo "notify-send: $reason" >&2
    # OL-N1 ⑥: a normal-priority send dropped for QUIET HOURS SPECIFICALLY (never dedup, never the
    # cap -- both of those are correct, permanent drops) gets queued so it can still reach the phone
    # once quiet hours lift, instead of being lost for good. See --flush-deferred above.
    case "$reason" in
      "SUPPRESS: quiet hours"*)
        python3 "$GOVERNOR" --queue-deferred "$SOURCE" "$MESSAGE" "$TITLE" "$TAGS" "$URL" >/dev/null 2>&1 || true
        ;;
    esac
    exit 0   # being suppressed is the system working -- never report it as a failure
    ;;
  *)
    echo "notify-send: GOVERNOR FAILED (rc=$GOV_RC) -- this is NOT a suppression. Nothing was sent." >&2
    printf '%s
' "${GOV_ERR:-<no stderr from governor>}" | head -5 >&2
    exit 1
    ;;
esac
rm -f "$_TMP/notify-gov.$$"

# ── Compose + send ────────────────────────────────────────────────────────────
# ntfy priority: 1 min, 2 low, 3 default, 4 high, 5 max.
# ONLY "critical" bypasses quiet hours and the daily cap -- that is the governor's decision,
# not this mapping. "high" is louder on the phone but still fully gated, which is exactly what
# a time-sensitive-but-not-emergency item (a walk-in sheet needed this afternoon) should be.
case "$PRIORITY" in
  min)       NTFY_PRIO=1 ;;
  low)       NTFY_PRIO=2 ;;
  high)      NTFY_PRIO=4 ;;
  critical)  NTFY_PRIO=5 ;;
  *)         NTFY_PRIO=3 ;;   # normal, misconfig
esac

HDRS=(-H "Priority: $NTFY_PRIO")
[ -n "$TITLE" ] && HDRS+=(-H "Title: $TITLE")
[ -n "$TAGS" ]  && HDRS+=(-H "Tags: $TAGS")
[ -n "$URL" ]   && HDRS+=(-H "Click: $URL")
[ "$MARKDOWN" = "1" ] && HDRS+=(-H "Markdown: yes")

# ── ASCII GUARD (added 2026-09-21, after a live test) ─────────────────────────
# MEASURED, not theorised. On this Windows machine a teaser containing non-ASCII does not
# arrive as a message:
#   "1 email ... U+00B7 1 walk-in"  -> ntfy turned the BODY INTO AN ATTACHMENT; the phone
#                                      showed "You received a file: attachment.txt"
#   "a U+2014 b" (em dash), "cafe" with U+00E9  -> same, attachment
#   "a U+2192 b" (arrow)                        -> arrived, but mangled to "a ? b"
#   plain ASCII                                 -> arrived correctly, every time
# curl still exits 0 in every case, so this is a SILENT CONTENT failure: the alert "sends"
# and the human sees a file prompt or a question mark instead of the teaser.
# The exact cause (shell codepage vs curl vs ntfy body sniffing) is NOT pinned down. The fix
# does not depend on knowing: a push body is a doorbell of a few words, so fold it to ASCII
# and it always arrives. Anything that needs real typography belongs behind --url anyway,
# which is the teaser discipline this whole wrapper exists to enforce.
_ascii_fold() {
  python3 "$GOVERNOR_DIR/ascii_fold.py"
}
MESSAGE="$(printf '%s' "$MESSAGE" | _ascii_fold)"
[ -n "$TITLE" ] && TITLE="$(printf '%s' "$TITLE" | _ascii_fold)"
[ -n "$MESSAGE" ] || { echo "notify-send: message was empty after ASCII folding" >&2; exit 2; }

# Rebuild the headers so the folded TITLE is the one actually sent.
HDRS=(-H "Priority: $NTFY_PRIO" -H "Content-Type: text/plain; charset=utf-8")
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
