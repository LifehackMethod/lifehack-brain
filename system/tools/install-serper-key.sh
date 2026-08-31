#!/bin/bash
# install-serper-key.sh — put your Serper web-search key where the system looks for it.
#
# Run it:   bash system/tools/install-serper-key.sh
#
# WHY THIS IS A SCRIPT AND NOT AN INSTRUCTION. An API key pasted into a chat window has
# been handed to a model, logged in a transcript, and synced to a notes folder. An API key
# typed as a command argument lands in your shell history in plain text. This script takes
# the key from your CLIPBOARD (or from a silent prompt), never from a chat message and never
# from argv, writes it 0600 to the one file the search path reads, and then proves the key
# works by running a real search through the sanitizer.
#
# What it does, in order:
#   1. Takes the key from the clipboard (macOS `pbpaste`), or `--prompt` for a silent typed
#      entry, or `--stdin` for a pipe. Never an argument.
#   2. Sanity-checks the shape and refuses obvious mistakes (a URL, an empty clipboard, a
#      value with spaces or newlines inside it).
#   3. ARCHIVES any existing key file beside itself before writing — never deletes one.
#   4. Writes ~/.config/lifehack/serper-key with umask 077, then chmod 600.
#   5. Runs ONE live search through system/tools/safe_search_api.sh and reports the verdict.
#
# It never prints the key. It prints a masked fingerprint (first 4 … last 4) so you can
# compare against the dashboard at serper.dev without the value appearing anywhere.
#
# Where the key comes from: a free account at serper.dev. The landing page advertises 2,500
# free queries and no credit card (read 2026-08-24). Creating the account and copying the key
# are YOUR hands — an agent does not create accounts or handle credentials.
#
# Exit 0 = key installed and a live search succeeded · 1 = setup refused · 2 = installed but
# the live check failed (the key file is still written; the verdict says why).

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KEY_FILE="${SERPER_KEY_FILE:-$HOME/.config/lifehack/serper-key}"
SOURCE="clipboard"
KEY=""

while [ $# -gt 0 ]; do
  case "$1" in
    --prompt)    SOURCE="prompt"; shift ;;
    --stdin)     SOURCE="stdin"; shift ;;
    --clipboard) SOURCE="clipboard"; shift ;;
    -h|--help)   sed -n '2,30p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2
       echo "A key is never passed as an argument — that puts it in your shell history." >&2
       echo "Usage: bash system/tools/install-serper-key.sh [--clipboard | --prompt | --stdin]" >&2
       exit 1 ;;
  esac
done

echo ""
echo "Installing your Serper web-search key."
echo "Target file: $KEY_FILE"
echo ""

# ── 1 · get the key, from somewhere that is not argv and not a chat window ──────────
case "$SOURCE" in
  clipboard)
    if ! command -v pbpaste >/dev/null 2>&1; then
      echo "No pbpaste on this machine, so the clipboard route is not available."
      echo "Run it again as:  bash system/tools/install-serper-key.sh --prompt"
      exit 1
    fi
    KEY="$(pbpaste 2>/dev/null | tr -d '[:space:]')"
    if [ -z "$KEY" ]; then
      echo "Your clipboard is empty."
      echo ""
      echo "  Copy the key from your serper.dev dashboard, then run this again."
      echo "  Or type it instead, with nothing echoed to the screen:"
      echo "    bash system/tools/install-serper-key.sh --prompt"
      exit 1
    fi
    ;;
  prompt)
    printf "Paste or type the key (it will NOT be shown): "
    read -rs KEY
    echo ""
    KEY="$(printf '%s' "$KEY" | tr -d '[:space:]')"
    ;;
  stdin)
    KEY="$(cat | tr -d '[:space:]')"
    ;;
esac

# ── 2 · refuse the obvious mistakes ────────────────────────────────────────────────
if [ -z "$KEY" ]; then
  echo "Nothing was supplied. Nothing was written."
  exit 1
fi
case "$KEY" in
  http://*|https://*)
    echo "That looks like a URL, not a key. Nothing was written."
    echo "The key is the value on the serper.dev dashboard, not the page address."
    exit 1 ;;
esac
if [ "${#KEY}" -lt 20 ]; then
  echo "That is ${#KEY} characters — too short to be a Serper key. Nothing was written."
  echo "A truncated copy is the commonest cause; copy the whole value again."
  exit 1
fi
MASK="${KEY:0:4}…${KEY: -4}  (${#KEY} chars)"
if ! printf '%s' "$KEY" | grep -qE '^[A-Za-z0-9_-]+$'; then
  echo "Note: that key contains characters outside the usual letters/digits set — $MASK."
  echo "Continuing anyway; the live check below is the real test."
fi

# ── 3 · never delete an existing key — move it aside ────────────────────────────────
if [ -s "$KEY_FILE" ]; then
  BACKUP="$KEY_FILE.replaced-$(date +%Y-%m-%d-%H%M%S)"
  if cp -p "$KEY_FILE" "$BACKUP" 2>/dev/null; then
    chmod 600 "$BACKUP" 2>/dev/null
    echo "A key was already there. The old one was kept at:"
    echo "  $BACKUP"
  else
    echo "A key is already there and could not be backed up. Stopping rather than overwrite it."
    exit 1
  fi
fi

# ── 4 · write it, readable by you and nobody else ──────────────────────────────────
mkdir -p "$(dirname "$KEY_FILE")" || { echo "Could not create $(dirname "$KEY_FILE")."; exit 1; }
( umask 077 && printf %s "$KEY" > "$KEY_FILE" ) || { echo "Could not write $KEY_FILE."; exit 1; }
chmod 600 "$KEY_FILE"
echo "Written: $KEY_FILE  ($(ls -l "$KEY_FILE" | cut -c1-10))"
echo "Key fingerprint: $MASK"
echo ""

# ── 5 · prove it, with one real search through the sanitizer ───────────────────────
echo "Running one live search to prove the key works…"
OUT="$(SAFE_SEARCH_VERBOSE=1 bash "$HERE/system/tools/safe_search_api.sh" "what year was the first modern olympics" 2>&1)"
RC=$?
if [ "$RC" -eq 0 ] || [ "$RC" -eq 1 ]; then
  echo ""
  echo "WORKS. Web search is live on this machine."
  [ "$RC" -eq 1 ] && echo "(The sanitizer flagged something in the results — that is the sanitizer doing its job, not a key problem.)"
  echo ""
  echo "First line of the sanitized result:"
  printf '%s\n' "$OUT" | grep -v '^\[safe_' | grep -v '^$' | head -1 | sed 's/^/  /'
  echo ""
  if [ "$SOURCE" = "clipboard" ] && command -v pbcopy >/dev/null 2>&1; then
    printf '' | pbcopy 2>/dev/null && echo "Your clipboard has been cleared, so the key is not sitting in it."
  fi
  echo ""
  echo "Try it:  /websearch <your question>"
  exit 0
fi

echo ""
echo "The key was written, but the live search FAILED. What the search path said:"
printf '%s\n' "$OUT" | grep '^\[safe_search_api\]' | sed 's/^/  /'
echo ""
echo "Commonest cause: a partial copy. Copy the key again from serper.dev and re-run this."
exit 2
