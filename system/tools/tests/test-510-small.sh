#!/usr/bin/env bash
# test-510-small.sh -- self-monitoring 5.10 items (4) and (5), the small fixes. Stubs and seams only: no network, no Gmail, no launchctl.
# One line per case: "<case> PASS" or "<case> FAIL ...". Exits non-zero if any case failed.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
T="$(mktemp -d "${TMPDIR:-/tmp}/t510.XXXXXX")"; trap 'rm -rf "$T"' EXIT
FAILS=0
pass() { echo "$1 PASS"; }
fail() { echo "$1 FAIL ${2:-}"; FAILS=$((FAILS+1)); }

# ── (a) a scanner / gate exception withholds the mail (UNJUDGED -> exit 3), never reads as clean ──
cat > "$T/a.py" <<'PY'
import os, sys, json
sys.path.insert(0, os.path.join(os.environ["ROOT"], "shared", "tools"))
import email_fetch as ef
which = sys.argv[1]
def scan_ok(b): return []
def scan_boom(b): raise RuntimeError("scanner exploded")
def gate_ok(*a, **k): return {"content": a[2], "provenance_tag": "t"}
def gate_boom(*a, **k): raise RuntimeError("gate exploded")
scan, gate = (scan_boom, gate_ok) if which == "scan" else (scan_ok, gate_boom)
ef._gate_modules = lambda: (gate, scan, None)
mode = sys.argv[2]
if mode == "unit":
    g = ef.gate_message("primary", "hello", item="x")
    print(g["verdict"], repr(g["content"]))
else:
    ef.enabled = lambda: True
    ef.list_threads = lambda p: ({"threads": [{"id": "t1"}]}, None)
    ef.get_thread = lambda i, f="metadata": ({"messages": [{"id": "m1", "internalDate": "1000", "payload": {"mimeType": "text/plain", "headers": [], "body": {"data": "aGVsbG8="}}}]}, None)
    sys.exit(ef.main(["--consumer", "t510", "--query", "", "--cap", "5", "--since", "none", "--no-mark"]))
PY
for w in scan gate; do
  out="$(ROOT="$ROOT" python3 "$T/a.py" $w unit 2>&1)"
  case "$out" in "UNJUDGED ''") pass "a-$w-exception-unjudged";; *) fail "a-$w-exception-unjudged" "got: $out";; esac
  ROOT="$ROOT" LIFEHACK_LAST_SEEN_DIR="$T" SENTINEL_PAUSE_FILE="$T/nopause" python3 "$T/a.py" $w run >"$T/a.out" 2>"$T/a.err"; rc=$?
  if [ "$rc" -eq 3 ] && ! grep -q hello "$T/a.out"; then pass "a-$w-exception-run-exit3"; else fail "a-$w-exception-run-exit3" "rc=$rc out=$(head -c 200 "$T/a.out")"; fi
done

[ "$FAILS" -eq 0 ]
