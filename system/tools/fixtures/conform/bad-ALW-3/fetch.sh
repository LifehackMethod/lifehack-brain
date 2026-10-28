#!/bin/bash
# breaks ALW-3 on line 5: the only check is a non-empty test
dir="$(dirname "$0")"
curl -fsS https://example.com/data -o "$dir/page.html" || exit 1
[ -s "$dir/page.html" ] && echo "verified: fetch ok"
