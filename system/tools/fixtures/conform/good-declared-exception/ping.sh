#!/bin/bash
# good: one declared ALW-1 exception on line 4 (see conform.decl)
out="$(dirname "$0")/page.html"
curl -fsS https://example.com/ping -X POST || true
curl -fsS https://example.com/data -o "$out" || exit 1
grep -q "<title>" "$out" || { echo "no title in fetched page" >&2; exit 1; }
