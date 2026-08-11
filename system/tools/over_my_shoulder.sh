#!/bin/bash
# over_my_shoulder.sh — Let Claude READ the user's live Chrome to help them navigate.
#
# READ-ONLY by design. The human drives (clicks/types/navigates); Claude only
# observes the page the user is on and advises. Claude never clicks, types,
# submits, or navigates — that keeps the prompt-injection-to-action loop broken.
# All page content is sanitized through safe_input.py (L0 + heuristic) before it
# reaches the model, exactly like web search.
#
# READ PATH (2026-06-09 rewrite): the page text is read by injecting a content
# script (chrome.scripting.executeScript) via the relay's /read-active endpoint —
# NO debugger attach. This deleted the long-standing "Cannot access a
# chrome-extension:// URL of different extension" attach failure that wedged the
# reader on password-manager autofill popups (history: dev-browser-debug-sop.md).
# It reads the page's own DOM text (incl. the site's modals/overlays); it cannot
# read another extension's popup or native browser UI — no in-browser tool can.
#
# Uses the SAME dev-browser relay + extension as the Chrome search path.
#
# Usage:
#   bash over_my_shoulder.sh            # read the active (visible) tab's text
#   bash over_my_shoulder.sh tabs       # list open tabs only (no page content)
#   bash over_my_shoulder.sh <index>    # read a specific tab by its [index]
#   bash over_my_shoulder.sh <substr>   # read the first tab whose URL/title contains <substr>
#
# Stdout: sanitized tab list (+ page content). Stderr: verdict / errors.
# Exit 0 = clean, 1 = flagged, 2 = setup error (relay/extension not connected).

set -o pipefail

CODE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"  # residency: these are CODE → clone
SAFE_INPUT="$CODE_ROOT/system/tools/safe_input.py"
OMS_FMT="$CODE_ROOT/system/tools/oms_format.py"
RELAY="http://127.0.0.1:9222"

ARG="$1"

# Ensure the relay is up (same check as safe_search.sh).
if ! curl -s --max-time 2 "$RELAY/" >/dev/null 2>&1; then
    echo "[over_my_shoulder] dev-browser relay is not running on :9222." >&2
    echo "[over_my_shoulder] Open Chrome and click the dev-browser icon, then retry." >&2
    exit 2
fi

# HARD GATE: only the EXTENSION-mode relay reads the user's REAL Chrome. The
# standalone server serves its OWN headless browser — reading that and calling it
# "your tabs" is the exact failure this skill had for months (root cause #1,
# 2026-06-07). Fail loudly instead of silently returning headless tabs.
RELAY_INFO=$(curl -s --max-time 2 "$RELAY/" 2>/dev/null)
if ! printf '%s' "$RELAY_INFO" | grep -q '"mode"[[:space:]]*:[[:space:]]*"extension"'; then
    echo "[over_my_shoulder] Relay is NOT in extension mode — it is not reading your real Chrome." >&2
    echo "[over_my_shoulder] Start the extension relay (npm run start-extension in the dev-browser dir) and connect the Chrome extension, then retry." >&2
    exit 2
fi
if ! printf '%s' "$RELAY_INFO" | grep -q '"extensionConnected"[[:space:]]*:[[:space:]]*true'; then
    echo "[over_my_shoulder] Chrome extension not connected to the relay — click the dev-browser icon in Chrome, then retry." >&2
    exit 2
fi

ERRTMP="/tmp/_oms_err_$$"
trap 'rm -f "$ERRTMP"' EXIT

if [ "$(printf '%s' "$ARG" | tr '[:upper:]' '[:lower:]')" = "tabs" ]; then
    # List open tabs only — metadata, no page content.
    RESP=$(curl -s --max-time 6 "$RELAY/list-tabs" 2>/dev/null)
    OUT=$(printf '%s' "$RESP" | python3 "$OMS_FMT" tabs 2>"$ERRTMP")
else
    # Read one tab's text. Pass the selector (index or substring) if given.
    if [ -n "$ARG" ]; then
        BODY=$(ARG="$ARG" python3 -c 'import json,os; print(json.dumps({"select": os.environ["ARG"]}))')
    else
        BODY='{}'
    fi
    RESP=$(curl -s --max-time 12 -X POST -H 'Content-Type: application/json' -d "$BODY" "$RELAY/read-active" 2>/dev/null)
    OUT=$(printf '%s' "$RESP" | python3 "$OMS_FMT" read 2>"$ERRTMP")
fi
RC=$?

if [ $RC -ne 0 ]; then
    ERR=$(cat "$ERRTMP" 2>/dev/null)
    case "$ERR" in
        *NO_READABLE_TAB*) echo "[over_my_shoulder] No readable web page is open to read — open an http(s) tab (the focused window may be a password-manager popup or a chrome:// page), then retry." >&2 ;;
        *READ_FAILED*)     echo "[over_my_shoulder] Could not read that tab: $ERR" >&2 ;;
        "")                echo "[over_my_shoulder] No response from the relay — is the extension still connected? Click the dev-browser icon and retry." >&2 ;;
        *)                 echo "[over_my_shoulder] $ERR" >&2 ;;
    esac
    exit 2
fi

# Sanitize everything (tab list or page content) before it reaches the model.
printf '%s\n' "$OUT" | python3 "$SAFE_INPUT" -
exit $?
