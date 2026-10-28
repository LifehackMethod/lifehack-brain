#!/bin/bash
# breaks ORD-3 on line 5: no truncation/last-line-complete guard
RECORD="$(dirname "$0")/record.tsv"
ccv=$(claude --version | awk '{print $1}')
: # (no truncation guard)
ans="$(claude -p --model sonnet --allowedTools Read "read notes.txt, answer yes or no")"
case "$ans" in yes|no) ;; *) echo "bad shape: $ans" >&2; exit 1 ;; esac
printf 's1\tok\t%s\tccv=%s\n' "$ans" "$ccv" >> "$RECORD"
