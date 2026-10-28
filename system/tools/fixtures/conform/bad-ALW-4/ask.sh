#!/bin/bash
# breaks ALW-4 on line 4: ai output used as-is, no fixed-shape parse
dir="$(dirname "$0")"
ans="$(claude -p --model sonnet --allowedTools Read "summarise notes.txt")"
printf '%s\n' "$ans" > "$dir/summary.txt"
