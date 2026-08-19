#!/bin/bash
# safe_search_api.sh — web search that is sanitized before the model sees a word of it.
#
# Usage: bash safe_search_api.sh "your search query" [--tbs qdr:w]
#
# THE INVARIANT: nothing from the web reaches the model before the sanitizer has run on it.
# Search results are not neutral text — a title and a snippet are written by whoever owns the
# page, they are chosen by what ranks, and they arrive with no filter after them. So the call
# goes out, the JSON is reduced to plain text, and that text goes through safe_input.py on the
# way in. There is no path around it: the built-in WebSearch tool is blocked by
# system/hooks/ingest_gate_enforce.sh, which points here.
#
# THIS IS THE ONLY SEARCH PATH. The system this came from also had a Chrome-driving fallback;
# it is deliberately NOT here, because it depended on a separate browser-relay skill that is not
# part of this repository and would have been a fallback that cannot work. If the key below is
# missing, this stops and says so — which is the honest failure, and better than quietly
# degrading to something that is not installed.
#
# Flow:
#   1. Find the Serper API key (three places, in order — see below). The value is never printed.
#   2. POST the query to https://google.serper.dev/search
#   3. Reduce the JSON to readable text (title / link / snippet, answer box, knowledge panel)
#   4. Pipe that text through safe_input.py before it reaches the model
#
# Stdout: sanitized results · Stderr: the verdict, any flags, any errors.
# Exit 0 = clean · 1 = the sanitizer flagged something · 2 = setup or API error.

set -o pipefail

# Parse args: pull out an optional `--tbs <value>` (Serper time filter, e.g.
# qdr:w = past week, qdr:d = past day) — everything else is the query. With no
# --tbs the call is byte-identical to before (default off; opt-in per caller).
QUERY=""
TBS=""
while [ $# -gt 0 ]; do
    case "$1" in
        --tbs) TBS="${2:-}"; shift 2 ;;
        *) QUERY="${QUERY:+$QUERY }$1"; shift ;;
    esac
done
if [ -z "$(printf '%s' "$QUERY" | tr -d '[:space:]')" ]; then
    echo "Usage: bash safe_search_api.sh 'your search query' [--tbs qdr:w]" >&2
    exit 2
fi

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"  # residency: safe_input.py is CODE → clone
SAFE_INPUT="$CODE_ROOT/system/tools/safe_input.py"

# ---------------------------------------------------------------------------
# Step 1: find the API key. Three places, in this order, and the order is the point.
#
#   1. $SERPER_API_KEY          — an environment variable. Works everywhere, including
#                                 Linux and Windows, and it is what a scheduled job can set.
#   2. ~/.config/lifehack/serper-key  — a file you own, 600 permissions. The same config
#                                 directory that already holds your notes-root pointer.
#   3. the macOS keychain       — LAST, and macOS-only, because of a two-week outage worth
#                                 remembering: the login keychain belongs to your GUI session.
#                                 A scheduled job runs in a non-GUI security session, so the
#                                 lookup came back EMPTY, every search exited 2, and the thing
#                                 that depended on it silently fell back to a worse path. It had
#                                 been failing for two weeks before anyone noticed, because the
#                                 error was swallowed by a 2>/dev/null.
#
# So: the portable sources first, the convenient-but-fragile one last, and the failure below
# names every place it looked rather than saying "no key."
# ---------------------------------------------------------------------------
KEY_FILE="${SERPER_KEY_FILE:-$HOME/.config/lifehack/serper-key}"
API_KEY=""
SOURCE=""
KC_ERR=""

if [ -n "${SERPER_API_KEY:-}" ]; then
    API_KEY="$SERPER_API_KEY"; SOURCE="the SERPER_API_KEY environment variable"
fi

if [ -z "$API_KEY" ] && [ -r "$KEY_FILE" ]; then
    API_KEY=$(tr -d '[:space:]' < "$KEY_FILE"); [ -n "$API_KEY" ] && SOURCE="$KEY_FILE"
fi

if [ -z "$API_KEY" ] && command -v security >/dev/null 2>&1; then
    KC_ERR=$(security find-generic-password -s "serper-api-key" -a "lifehack" -w 2>&1 >/dev/null)
    API_KEY=$(security find-generic-password -s "serper-api-key" -a "lifehack" -w 2>/dev/null)
    [ -n "$API_KEY" ] && SOURCE="the macOS keychain"
fi

if [ -z "$API_KEY" ]; then
    echo "[safe_search_api] No Serper API key. Web search needs one — get a free key at serper.dev." >&2
    echo "[safe_search_api] Looked in all three places:" >&2
    echo "[safe_search_api]   1. \$SERPER_API_KEY — not set" >&2
    echo "[safe_search_api]   2. $KEY_FILE — $([ -e "$KEY_FILE" ] && echo 'there, but unreadable or empty' || echo 'not there')" >&2
    if command -v security >/dev/null 2>&1; then
        echo "[safe_search_api]   3. macOS keychain (service 'serper-api-key', account 'lifehack') — ${KC_ERR:-nothing stored}" >&2
    else
        echo "[safe_search_api]   3. macOS keychain — not this platform" >&2
    fi
    echo "[safe_search_api] The portable fix, which also works for scheduled jobs:" >&2
    echo "[safe_search_api]   mkdir -p \"\$(dirname "$KEY_FILE")\" && umask 077 && printf %s '<your-key>' > $KEY_FILE" >&2
    exit 2
fi
[ -n "${SAFE_SEARCH_VERBOSE:-}" ] && echo "[safe_search_api] key from $SOURCE" >&2

# ---------------------------------------------------------------------------
# Cost guard: cap daily calls so a runaway loop can't burn the monthly credit
# pool. On breach, exit 2 and say so — there is no second path to degrade to, by design.
# Override with SERPER_MAX_DAILY. (Safety cap, not exact billing; a small race
# under heavy concurrency is acceptable.)
# ---------------------------------------------------------------------------
MAX_DAILY="${SERPER_MAX_DAILY:-500}"
CALL_LOG="${TMPDIR:-/tmp}/serper_calls_$(date +%Y%m%d).log"
[ -f "$CALL_LOG" ] || : > "$CALL_LOG" 2>/dev/null
COUNT=$(wc -l < "$CALL_LOG" 2>/dev/null | tr -d ' '); COUNT=${COUNT:-0}
if [ "$COUNT" -ge "$MAX_DAILY" ] 2>/dev/null; then
    echo "[safe_search_api] Daily Serper call cap reached ($COUNT/$MAX_DAILY). Raise it with SERPER_MAX_DAILY=N." >&2
    exit 2
fi
printf '%s\n' "$(date +%H:%M:%S)" >> "$CALL_LOG"

# ---------------------------------------------------------------------------
# Step 2 + 3: Call Serper and reduce JSON -> readable text.
# Key is passed via env (never argv / never printed). HTTP errors are surfaced
# with a sentinel so the wrapper can distinguish auth failures from results.
# ---------------------------------------------------------------------------
REDUCED=$(SERPER_KEY="$API_KEY" QUERY="$QUERY" SERPER_TBS="$TBS" python3 <<'PY'
import os, json, urllib.request, urllib.error

key = os.environ["SERPER_KEY"]
q = os.environ["QUERY"]
tbs = os.environ.get("SERPER_TBS", "").strip()

payload = {"q": q}
if tbs:
    payload["tbs"] = tbs      # Serper time filter (qdr:w = past week) — narrows to recent

req = urllib.request.Request(
    "https://google.serper.dev/search",
    data=json.dumps(payload).encode(),
    headers={"X-API-KEY": key, "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
except urllib.error.HTTPError as e:
    body = e.read().decode(errors="replace")[:300]
    print(f"__SERPER_ERROR__ HTTP {e.code}: {body}")
    raise SystemExit(0)
except Exception as e:
    print(f"__SERPER_ERROR__ {type(e).__name__}: {e}")
    raise SystemExit(0)

lines = []
ab = data.get("answerBox") or {}
ans = ab.get("answer") or ab.get("snippet") or ""
if ans:
    lines.append(f"ANSWER: {ans}")

kg = data.get("knowledgeGraph") or {}
if kg.get("title") or kg.get("description"):
    lines.append(f"KNOWLEDGE: {kg.get('title','')} — {kg.get('description','')}")

for i, o in enumerate(data.get("organic", [])[:10], 1):
    lines.append(f"{i}. {o.get('title','')}\n   {o.get('link','')}\n   {o.get('snippet','')}")

paa = data.get("peopleAlsoAsk") or []
qs = "; ".join(p.get("question", "") for p in paa[:5] if p.get("question"))
if qs:
    lines.append(f"PEOPLE ALSO ASK: {qs}")

print("\n".join(lines) if lines else "(no results returned)")
PY
)

# ---------------------------------------------------------------------------
# Surface API/auth errors before sanitizing
# ---------------------------------------------------------------------------
if printf '%s' "$REDUCED" | grep -q "^__SERPER_ERROR__"; then
    ERR=$(printf '%s' "$REDUCED" | sed 's/^__SERPER_ERROR__ //')
    echo "[safe_search_api] Serper request failed: $ERR" >&2
    case "$ERR" in
        *403*|*401*) echo "[safe_search_api] Auth failed — the stored key is probably wrong or truncated. Copy it again from serper.dev." >&2 ;;
    esac
    exit 2
fi

# Never let an empty reduction (malformed-but-valid JSON, OS-level crash) sail
# through as a clean exit 0 — treat it as a failure so /websearch can fall back.
if [ -z "$REDUCED" ]; then
    echo "[safe_search_api] Empty result from reducer — treating as failure (exit 2)." >&2
    exit 2
fi

# ---------------------------------------------------------------------------
# Step 4: Sanitize through safe_input.py (L0 + heuristic) before the model sees it
# ---------------------------------------------------------------------------
printf '%s\n' "$REDUCED" | python3 "$SAFE_INPUT" -
exit $?
