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

# ── (b) a search error exits 2 (transient), marker text kept ──
mkdir -p "$T/bin"; cat > "$T/bin/python3" <<'STUB'
#!/bin/bash
# stub: the FIRST call is the Serper reducer (stdin heredoc); the second is safe_input.py (sanitizer). STUBOUT/STUBRC drive the first only.
cat > /dev/null
if [ ! -e "$STUBDIR/called" ]; then touch "$STUBDIR/called"; [ -n "$STUBOUT" ] && echo "$STUBOUT"; exit "${STUBRC:-0}"; fi
echo "sanitized"; exit 0
STUB
chmod +x "$T/bin/python3"
sc() {  # case-name want-rc stubout stubrc [want-stderr-substring]
  rm -rf "$T/sd"; mkdir -p "$T/sd"
  STUBDIR="$T/sd" STUBOUT="$3" STUBRC="$4" SERPER_API_KEY=k TMPDIR="$T/sd" PATH="$T/bin:$PATH" bash "$ROOT/system/tools/safe_search_api.sh" hello >"$T/sd/out" 2>"$T/sd/err"; local rc=$?
  if [ "$rc" -eq "$2" ] && { [ -z "${5:-}" ] || grep -q -- "$5" "$T/sd/err"; }; then pass "$1"; else fail "$1" "rc=$rc want $2; err=$(head -c 160 "$T/sd/err")"; fi
}
sc b-http-error-exit2       2 "__SERPER_ERROR__ HTTP 500: boom" 0 "Serper request failed: HTTP 500"
sc b-other-error-exit2      2 "__SERPER_ERROR__ URLError: x"     0 "Serper request failed: URLError"
sc b-reducer-crash-exit2    2 "1. partial result"                1 "reducer"
sc b-clean-exit0            0 "1. a result"                      0

# ── (c) a failed `launchctl bootstrap` fails the install, loudly (stub launchctl on PATH; no real launchctl) ──
mkdir -p "$T/c/code/system/tools" "$T/c/home" "$T/c/bin"
printf '#!/usr/bin/env bash\necho fine\n' > "$T/c/code/system/tools/ok-run.sh"
printf '```jobs\nj1 | yes | 3600 | o. | $HOME/x ~ ^ran j1 n=[0-9]+ | none | 0 | none | bash "$LIFEHACK_CODE_ROOT/system/tools/ok-run.sh"\n```\n' > "$T/c/manifest.md"
cat > "$T/c/bin/launchctl" <<'STUB'
#!/bin/bash
echo "launchctl $*" >> "$STUBLOG"
[ "$1" = bootstrap ] && exit "${BOOTSTRAP_RC:-0}"
exit 0
STUB
chmod +x "$T/c/bin/launchctl"
ci() {  # case-name want-rc bootstrap-rc
  : > "$T/c/log"; rm -rf "$T/c/la"; mkdir -p "$T/c/la"
  STUBLOG="$T/c/log" BOOTSTRAP_RC="$3" PATH="$T/c/bin:$PATH" PULSE_CONFIG="$T/c/manifest.md" LIFEHACK_CODE_ROOT="$T/c/code" LIFEHACK_DESK_REPO="$T/c/nodesk" \
    HOME="$T/c/home" LAUNCHAGENTS_DIR="$T/c/la" LIFEHACK_TEST_OS_OVERRIDE=mac bash "$ROOT/system/tools/install-schedulers.sh" --install >"$T/c/out" 2>"$T/c/err"; local rc=$?
  grep -q "^launchctl bootstrap" "$T/c/log" || { fail "$1" "bootstrap was never called (stub unused): $(head -c 200 "$T/c/err")"; return; }
  if [ "$rc" -eq "$2" ] && { [ "$2" -eq 0 ] || grep -qi "bootstrap.*fail" "$T/c/err"; }; then pass "$1"; else fail "$1" "rc=$rc want $2; err=$(head -c 200 "$T/c/err")"; fi
}
ci c-bootstrap-fails-install 1 5
ci c-bootstrap-ok-installs   0 0

# ── (d) email-summary-write-run.sh: the watchdog kills the whole process group, so no python is left orphaned ──
D="$T/d"; mkdir -p "$D/code/system/tools" "$D/code/shared/tools" "$D/home" "$D/lock"
cp "$ROOT/system/tools/email-summary-write-run.sh" "$ROOT/system/tools/runner-lock.lib.sh" "$D/code/system/tools/"
printf 'require_gws_credentials() { GWS_CREDS_FILE=/dev/null; return 0; }\n' > "$D/code/system/tools/gws-auth.lib.sh"
printf 'write_status_tile() { :; }\n' > "$D/code/system/tools/status-tile.lib.sh"
printf 'print("%s")\n' "$D/data" > "$D/code/shared/brain_root.py"
printf 'import sys\nsys.exit(0)\n' > "$D/code/shared/tools/email_fetch.py"
cat > "$D/code/shared/tools/email_summary_sync.py" <<'PY'
import os, sys, time
open(os.environ["ORPHAN_PIDFILE"], "w").write(str(os.getpid()))
time.sleep(120)
PY
ORPHAN_PIDFILE="$D/pid" HOME="$D/home" LIFEHACK_RUNNER_LOCK_ROOT="$D/lock" EMAIL_WRITE_WATCHDOG_SECS=2 \
  bash "$D/code/system/tools/email-summary-write-run.sh" >"$D/out" 2>&1; drc=$?
sleep 1
if [ -s "$D/pid" ] && kill -0 "$(cat "$D/pid")" 2>/dev/null; then
  fail d-watchdog-no-orphan "python pid $(cat "$D/pid") survived the watchdog (rc=$drc)"; kill -9 "$(cat "$D/pid")" 2>/dev/null
elif [ ! -s "$D/pid" ]; then fail d-watchdog-no-orphan "the stub work never started: $(head -c 200 "$D/out")"
elif [ "$drc" -eq 0 ]; then fail d-watchdog-no-orphan "a watchdog-killed run exited 0"
else pass d-watchdog-no-orphan; fi

# ── (e) the door refuses a check with no value-bearing field; (f) it refuses a row whose command file is missing ──
E="$T/e"; mkdir -p "$E/code/system/tools" "$E/fakehome/.claude/skills/ClaudeOps/desks/x"; printf '#!/usr/bin/env bash\necho fine\n' > "$E/code/system/tools/ok-run.sh"
door() {  # check [command] -> sets DOOR_OUT, DOOR_RC
  printf '```jobs\nrow1 | yes | 3600 | o. | %s | none | 0 | none | %s\n```\n' "$1" "${2:-bash \"\$LIFEHACK_CODE_ROOT/system/tools/ok-run.sh\"}" > "$E/m.md"
  DOOR_OUT="$(LIFEHACK_JOBS_FILE="$E/m.md" LIFEHACK_CODE_ROOT="$E/code" LIFEHACK_DESK_REPO="$E/fakehome/.claude/skills/ClaudeOps" HOME="$E/fakehome" bash "$ROOT/system/tools/install-schedulers.sh" --check-row row1 2>&1)"; DOOR_RC=$?
}
want_refused() { door "$2" "${3:-}"; if [ "$DOOR_RC" -ne 0 ] && echo "$DOOR_OUT" | grep -q -- "$4"; then pass "$1"; else fail "$1" "rc=$DOOR_RC $DOOR_OUT"; fi; }
want_pass()    { door "$2" "${3:-}"; if [ "$DOOR_RC" -eq 0 ]; then pass "$1"; else fail "$1" "rc=$DOOR_RC $DOOR_OUT"; fi; }
want_refused e-bare-done-refused        '$HOME/x ~ ^done$'          "" "value-bearing"
want_refused e-bare-word-refused        '$HOME/x ~ ^finished run'   "" "value-bearing"
want_pass    e-equals-passes            '$HOME/x ~ ^ran status=fine'
want_pass    e-number-passes            '$HOME/x ~ ^ran n=[0-9]+ items'
want_pass    e-class-quantifier-passes  '$HOME/x ~ "verdict":"[A-Z]+"'
want_pass    e-capture-group-passes     '$HOME/x ~ ^ran (alpha)+'
want_refused f-missing-command-file     '$HOME/x ~ ^ran n=[0-9]+' 'bash "$LIFEHACK_CODE_ROOT/system/tools/gone-run.sh"' "gone-run.sh"
want_refused f-missing-home-file        '$HOME/x ~ ^ran n=[0-9]+' 'bash "$HOME/.claude/skills/ClaudeOps/desks/x/gone-run.sh"' "gone-run.sh"
want_pass    f-existing-file-passes     '$HOME/x ~ ^ran n=[0-9]+'

[ "$FAILS" -eq 0 ]
