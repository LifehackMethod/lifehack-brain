#!/bin/bash
# breaks ORD-1 (folder): runner writes record.tsv on line 8 but no *.card exists
RECORD="$(dirname "$0")/record.tsv"
ccv=$(claude --version | awk '{print $1}')
[ -z "$(tail -c1 "$RECORD")" ] || { echo "truncated record" >&2; exit 1; }
ans="$(claude -p --model sonnet --allowedTools Read "read notes.txt, answer yes or no")"
case "$ans" in yes|no) ;; *) echo "bad shape: $ans" >&2; exit 1 ;; esac
printf 's1\tok\t%s\tccv=%s\n' "$ans" "$ccv" >> "$RECORD"
