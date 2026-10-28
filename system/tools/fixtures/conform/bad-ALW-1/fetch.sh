#!/bin/bash
# breaks ALW-1 on line 4: curl error silenced with || true
out="$(dirname "$0")/page.html"
curl -fsS https://example.com/data -o "$out" || true
grep -q "<title>" "$out" || { echo "no title in fetched page" >&2; exit 1; }
