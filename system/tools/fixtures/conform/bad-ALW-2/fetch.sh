#!/bin/bash
# breaks ALW-2 on line 4: marker advanced on exit code alone, no content check
dir="$(dirname "$0")"
if curl -fsS https://example.com/data -o "$dir/page.html"; then touch "$dir/last_run"; fi
