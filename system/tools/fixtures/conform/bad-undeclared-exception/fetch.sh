#!/bin/bash
# breaks ALW-1 on line 5: inline waiver is not a declaration (no conform.decl)
out="$(dirname "$0")/page.html"
# conform: allow ALW-1
curl -fsS https://example.com/data -o "$out" || true
grep -q "<title>" "$out" || { echo "no title in fetched page" >&2; exit 1; }
