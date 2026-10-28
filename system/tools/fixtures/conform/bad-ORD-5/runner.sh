#!/bin/bash
# breaks ORD-5 on line 6: claude -p lacks --model
RECORD="$(dirname "$0")/record.tsv"
ccv=$(claude --version | awk '{print $1}')
[ -z "$(tail -c1 "$RECORD")" ] || { echo "truncated record" >&2; exit 1; }
ans="$(claude -p --allowedTools Read "read notes.txt, answer yes or no")"
case "$ans" in yes|no) ;; *) echo "bad shape: $ans" >&2; exit 1 ;; esac
printf 's1\tok\t%s\tccv=%s\n' "$ans" "$ccv" >> "$RECORD"
