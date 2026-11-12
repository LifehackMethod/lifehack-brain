#!/bin/bash
# test_hook_runner.sh -- hook_runner.sh: syntax of the wrapper itself + the four behaviours.
# Run: bash system/hooks/tests/test_hook_runner.sh   (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
RUNNER="${HOOK_UNDER_TEST:-$HOOKS/hook_runner.sh}"
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export LIFEHACK_STATE_DIR="$T/state" LIFEHACK_HOOKS_LASTGOOD="$T/lg"

bash -n "$RUNNER" 2>/dev/null && ok || bad "syntax" "hook_runner.sh itself fails bash -n"
[ "$(wc -l < "$RUNNER")" -le 60 ] && ok || bad "tiny" "wrapper has grown past 60 lines -- keep it tiny"

# a sandbox "hooks dir" holding a COPY of the runner next to the hooks it launches
mk() { rm -rf "$T/h" "$T/lg" "$T/state"; mkdir -p "$T/h"; cp "$RUNNER" "$T/h/hook_runner.sh"; }
GOOD='#!/bin/bash
cat >/dev/null; echo GOOD-RAN; exit 0'
GATE='#!/bin/bash
cat >/dev/null; echo GATE-DENY >&2; exit 2'
L="<<<<<<<"; M="======="; R=">>>>>>>"   # built at run time so this file has no marker lines itself
BROKEN="#!/bin/bash
if true; then
$L HEAD
echo x
$M
echo y
$R branch
"
SYNTAX='#!/bin/bash
if true; then echo x'

echo "── good hook runs unchanged; stdin and exit code pass through ──"
mk; printf '%s\n' "$GOOD" > "$T/h/g.sh"
out=$(echo '{}' | bash "$T/h/hook_runner.sh" g.sh 2>&1); rc=$?
[ "$rc" = 0 ] && [ "$out" = "GOOD-RAN" ] && ok || bad "good-runs" "rc=$rc out=$out"
printf '%s\n' "$GATE" > "$T/h/d.sh"
echo '{}' | bash "$T/h/hook_runner.sh" d.sh >/dev/null 2>&1; [ $? = 2 ] && ok || bad "gate-exit-2" "a good gate's deny exit code was not passed through"
n=$(ls "$T/lg"/g.sh.2* 2>/dev/null | wc -l); n=$((n+0))
[ "$n" = 1 ] && ok || bad "snapshot" "expected 1 last-good snapshot, got $n"
echo '{}' | bash "$T/h/hook_runner.sh" g.sh >/dev/null 2>&1
n=$(ls "$T/lg"/g.sh.2* 2>/dev/null | wc -l); n=$((n+0)); [ "$n" = 1 ] && ok || bad "snapshot-dedupe" "unchanged hook re-snapshotted ($n)"

echo "── broken hook + good copy -> restored and runs ──"
for kind in BROKEN SYNTAX; do
  mk; printf '%s\n' "$GATE" > "$T/h/d.sh"
  echo '{}' | bash "$T/h/hook_runner.sh" d.sh >/dev/null 2>&1      # takes the snapshot
  printf '%s\n' "${!kind}" > "$T/h/d.sh"                           # now break the live file
  bash -n "$T/h/d.sh" 2>/dev/null && [ "$kind" = SYNTAX ] && { bad "fixture" "SYNTAX fixture parses"; }
  out=$(echo '{}' | bash "$T/h/hook_runner.sh" d.sh 2>&1); rc=$?
  [ "$rc" = 2 ] && echo "$out" | grep -q GATE-DENY && ok || bad "restored-runs-$kind" "rc=$rc out=$out"
  echo "$out" | grep -q 'RESTORED' && ok || bad "loud-$kind" "no RESTORED alert on stderr"
  [ -s "$T/state/hooks-alerts.log" ] && [ -s "$T/state/hooks-alert.json" ] && ok || bad "alert-files-$kind" "alert log/tile not written"
  ls "$T/lg"/d.sh.broken.* >/dev/null 2>&1 && ok || bad "quarantine-$kind" "broken copy not kept"
  bash -n "$T/h/d.sh" && ok || bad "live-fixed-$kind" "live file still broken after restore"
done
echo "── a broken COPY is never used as the restore source ──"
mk; printf '%s\n' "$GOOD" > "$T/h/g.sh"; echo '{}' | bash "$T/h/hook_runner.sh" g.sh >/dev/null 2>&1
printf '%s\n' "$BROKEN" > "$T/lg/g.sh.29990101T000000Z"; printf '%s\n' "$BROKEN" > "$T/h/g.sh"
out=$(echo '{}' | bash "$T/h/hook_runner.sh" g.sh 2>&1); rc=$?
[ "$rc" = 0 ] && echo "$out" | grep -q GOOD-RAN && ok || bad "skip-bad-copy" "rc=$rc out=$out"

echo "── broken hook + NO good copy -> FAILS CLOSED ──"
for kind in BROKEN SYNTAX; do
  mk; printf '%s\n' "${!kind}" > "$T/h/d.sh"
  out=$(echo '{}' | bash "$T/h/hook_runner.sh" d.sh 2>&1); rc=$?
  [ "$rc" = 2 ] && echo "$out" | grep -q 'FAILING CLOSED' && ok || bad "closed-$kind" "rc=$rc out=$out"
done
mk; echo '{}' | bash "$T/h/hook_runner.sh" nothere.sh >/dev/null 2>&1; [ $? = 2 ] && ok || bad "closed-missing" "missing hook did not fail closed"
echo '{}' | bash "$T/h/hook_runner.sh" ../x.sh >/dev/null 2>&1; [ $? = 2 ] && ok || bad "closed-traversal" "path-ish name accepted"
echo '{}' | bash "$T/h/hook_runner.sh" >/dev/null 2>&1; [ $? = 2 ] && ok || bad "closed-noarg" "no-arg did not fail closed"

echo "── args reach the hook ──"
mk; printf '#!/bin/bash\ncat >/dev/null; echo "ARGS:$*"\n' > "$T/h/a.sh"
out=$(echo '{}' | bash "$T/h/hook_runner.sh" a.sh record x 2>&1); [ "$out" = "ARGS:record x" ] && ok || bad "args" "$out"

echo "$pass passed, $fail failed"; [ "$fail" = 0 ]
