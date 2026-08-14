#!/bin/bash
# safe_search.sh — Sanitized web search via Chrome + dev-browser + safe_input.py
#
# Usage: bash safe_search.sh "your search query"
#
# Flow:
#   1. Ensure dev-browser relay is running
#   2. Search Google via user's real Chrome browser
#   3. Extract page text
#   4. Pipe through safe_input.py (L0 + heuristic scan)
#
# Stdout: sanitized search results
# Stderr: verdict + any flags (informational)
# Exit 0 = clean, Exit 1 = flagged, Exit 2 = setup error

set -o pipefail

QUERY="$*"
if [ -z "$QUERY" ]; then
    echo "Usage: bash safe_search.sh 'your search query'" >&2
    exit 2
fi

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"  # residency: safe_input.py is CODE → clone
DEV_BROWSER="$HOME/.claude/skills/dev-browser/skills/dev-browser"
SAFE_INPUT="$CODE_ROOT/system/tools/safe_input.py"

# ---------------------------------------------------------------------------
# Step 1: Check/start relay server
# ---------------------------------------------------------------------------
_relay_running() {
    # Check if relay process is listening — try JSON endpoint first, fall back to process check
    curl -s --max-time 2 http://127.0.0.1:9222/json/version >/dev/null 2>&1 && return 0
    curl -s --max-time 2 http://127.0.0.1:9222 >/dev/null 2>&1 && return 0
    pgrep -f 'start-relay|start-extension' >/dev/null 2>&1 && return 0
    return 1
}

if ! _relay_running; then
    echo "[safe_search] Starting dev-browser relay server..." >&2
    cd "$DEV_BROWSER" && npm run start-extension >/dev/null 2>&1 &
    RELAY_PID=$!

    # Wait up to 10s for relay to be ready
    for i in $(seq 1 20); do
        if _relay_running; then
            echo "[safe_search] Relay server ready." >&2
            break
        fi
        sleep 0.5
    done

    if ! _relay_running; then
        echo "[safe_search] ERROR: Relay server failed to start." >&2
        exit 2
    fi
fi

# ---------------------------------------------------------------------------
# Step 2: Search Google via Chrome, extract text
# ---------------------------------------------------------------------------
ENCODED_QUERY=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote_plus(sys.argv[1]))" "$QUERY")
SEARCH_URL="https://www.google.com/search?q=${ENCODED_QUERY}"

# Write temp .mts file INSIDE the dev-browser project directory so it inherits
# "type":"module" and tsx supports top-level await. The filename AND the page
# name are made unique per invocation ($$ + $RANDOM) so concurrent searches from
# multiple sessions never clobber each other's script or drive the same Chrome
# tab — that race was the multi-session failure mode.
PAGE_ID="$$_${RANDOM}"
TEMP_SEARCH="$DEV_BROWSER/_safe_search_${PAGE_ID}.mts"
trap 'rm -f "$TEMP_SEARCH"' EXIT
cat > "$TEMP_SEARCH" <<TSEOF
import { connect, waitForPageLoad } from "@/client.js";

const PAGE_NAME = "safe-search-${PAGE_ID}";
let client: any;
try {
    client = await connect();
    const page = await client.page(PAGE_NAME);

    await page.goto("${SEARCH_URL}");
    await waitForPageLoad(page);

    const text = await page.evaluate(() => document.body.innerText);
    console.log(text);
} catch (e: any) {
    if (e.message && e.message.includes("No targets")) {
        console.error("EXTENSION_NOT_CONNECTED");
    } else {
        console.error("SEARCH_ERROR: " + e.message);
    }
    process.exitCode = 1;
} finally {
    // Pages persist on the relay after disconnect, so close THIS session's own
    // tab to avoid leaking a tab per search. Both steps best-effort.
    if (client) {
        try { await client.close(PAGE_NAME); } catch {}
        try { await client.disconnect(); } catch {}
    }
}
TSEOF

# ---------------------------------------------------------------------------
# Retry loop — Chrome terminates the MV3 service worker after ~30s idle. When
# it respawns, the relay rejects in-flight requests with "Extension connection
# replaced" (relay.ts onOpen, code 4001). This self-heals in ~3s, so a short
# retry absorbs the transient failure instead of failing the whole search.
# The real stderr error is captured separately (not masked) for diagnosis —
# masking it previously caused a wrong-cause hunt (blamed VPN, was SW cycling).
# Layer 2 (relay-side keepalive ping) is the upstream fix — see save-flagged log.
# ---------------------------------------------------------------------------
MAX_ATTEMPTS=3
ATTEMPT=1
RAW_TEXT=""
TSX_EXIT=1
LAST_ERR=""

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    ERR_FILE=$(mktemp)
    # stdout = clean page text; stderr = real error, kept separate so it never
    # pollutes the sanitized results but stays available for diagnosis.
    RAW_TEXT=$(cd "$DEV_BROWSER" && npx tsx "$TEMP_SEARCH" 2>"$ERR_FILE")
    TSX_EXIT=$?
    LAST_ERR=$(cat "$ERR_FILE")
    rm -f "$ERR_FILE"

    # Success: clean exit and a real result body
    if [ $TSX_EXIT -eq 0 ] && [ ${#RAW_TEXT} -ge 50 ]; then
        break
    fi

    # Genuinely not connected — retry won't help, fail fast with the fix.
    if echo "$LAST_ERR" | grep -q "EXTENSION_NOT_CONNECTED" 2>/dev/null; then
        echo "[safe_search] Chrome extension not connected." >&2
        echo "[safe_search] Click the dev-browser icon in Chrome, then try again." >&2
        rm -f "$TEMP_SEARCH"
        exit 2
    fi

    # Transient (service worker cycling / connection replaced / empty) — wait + retry.
    if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
        echo "[safe_search] Attempt $ATTEMPT/$MAX_ATTEMPTS failed (service worker likely cycling), retrying in 3s..." >&2
        sleep 3
    fi
    ATTEMPT=$((ATTEMPT + 1))
done

rm -f "$TEMP_SEARCH"

# All attempts exhausted — surface the REAL error (no longer masked).
if [ $TSX_EXIT -ne 0 ] || [ ${#RAW_TEXT} -lt 50 ]; then
    echo "[safe_search] Search failed after $MAX_ATTEMPTS attempts." >&2
    if [ -n "$LAST_ERR" ]; then
        echo "[safe_search] Last error: $(echo "$LAST_ERR" | grep -v '^$' | tail -2 | tr '\n' ' ')" >&2
    fi
    echo "[safe_search] If this persists: toggle dev-browser off/on in chrome://extensions, then click its icon." >&2
    exit 2
fi

# ---------------------------------------------------------------------------
# Step 3: Sanitize through safe_input.py
# ---------------------------------------------------------------------------
echo "$RAW_TEXT" | python3 "$SAFE_INPUT" -
exit $?
