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
[ "$(wc -l < "$RUNNER")" -le 100 ] && ok || bad "tiny" "wrapper has grown past 100 lines -- keep it small"

# the store is per hooks folder: <lg>/<cksum of the real folder path>/
LGD() { echo "$T/lg/$(printf '%s' "$(cd "${1:-$T/h}" && pwd -P)" | cksum | cut -d' ' -f1)"; }
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
n=$(ls "$(LGD)"/g.sh.2* 2>/dev/null | wc -l); n=$((n+0))
[ "$n" = 1 ] && ok || bad "snapshot" "expected 1 last-good snapshot, got $n"
echo '{}' | bash "$T/h/hook_runner.sh" g.sh >/dev/null 2>&1
n=$(ls "$(LGD)"/g.sh.2* 2>/dev/null | wc -l); n=$((n+0)); [ "$n" = 1 ] && ok || bad "snapshot-dedupe" "unchanged hook re-snapshotted ($n)"

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
  ls "$(LGD)"/d.sh.broken.* >/dev/null 2>&1 && ok || bad "quarantine-$kind" "broken copy not kept"
  bash -n "$T/h/d.sh" && ok || bad "live-fixed-$kind" "live file still broken after restore"
done
echo "── a broken COPY is never used as the restore source ──"
mk; printf '%s\n' "$GOOD" > "$T/h/g.sh"; echo '{}' | bash "$T/h/hook_runner.sh" g.sh >/dev/null 2>&1
printf '%s\n' "$BROKEN" > "$(LGD)/g.sh.20200101T000000Z"; printf '%s\n' "$BROKEN" > "$T/h/g.sh"
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

echo "── review item 9: a weaker copy from ANOTHER folder is never restored into this one ──"
rm -rf "$T/h" "$T/h2" "$T/lg" "$T/state"; mkdir -p "$T/h" "$T/h2"; cp "$RUNNER" "$T/h/hook_runner.sh"; cp "$RUNNER" "$T/h2/hook_runner.sh"
WEAK='#!/bin/bash
cat >/dev/null; exit 0'
printf '%s\n' "$WEAK" > "$T/h2/d.sh"; echo '{}' | bash "$T/h2/hook_runner.sh" d.sh >/dev/null 2>&1   # weak copy saved from folder 2
printf '%s\n' "$GATE" > "$T/h/d.sh"                                                                  # folder 1 holds the strict gate, never run yet
printf '%s\n' "$SYNTAX" > "$T/h/d.sh"
out=$(echo '{}' | bash "$T/h/hook_runner.sh" d.sh 2>&1); rc=$?
[ "$rc" = 2 ] && echo "$out" | grep -q 'FAILING CLOSED' && ok || bad "cross-folder" "weak copy from another folder was used: rc=$rc out=$out"
[ "$(LGD "$T/h")" != "$(LGD "$T/h2")" ] && ok || bad "cross-folder-keys" "two folders share one store"

echo "── review item 9: a planted far-future copy never wins; store is mode 700 ──"
mk; printf '%s\n' "$GATE" > "$T/h/d.sh"; echo '{}' | bash "$T/h/hook_runner.sh" d.sh >/dev/null 2>&1
printf '%s\n' "$WEAK" > "$(LGD)/d.sh.29991231T000000Z"; printf '%s\n' "$WEAK" > "$(LGD)/d.sh.not-a-date"
printf '%s\n' "$SYNTAX" > "$T/h/d.sh"
out=$(echo '{}' | bash "$T/h/hook_runner.sh" d.sh 2>&1); rc=$?
[ "$rc" = 2 ] && echo "$out" | grep -q GATE-DENY && ok || bad "planted-future" "planted copy won: rc=$rc out=$out"
perm=$(stat -f %Lp "$(LGD)" 2>/dev/null || stat -c %a "$(LGD)"); [ "$perm" = 700 ] && ok || bad "store-mode" "store is mode $perm, want 700"

echo "── review item 9: store does not grow without bound ──"
mk; for i in $(seq 1 15); do printf '#!/bin/bash\ncat >/dev/null; echo V%s\n' "$i" > "$T/h/g.sh"; echo '{}' | bash "$T/h/hook_runner.sh" g.sh >/dev/null 2>&1; sleep 1; done
n=$(ls "$(LGD)"/g.sh.2* | wc -l); n=$((n+0)); [ "$n" -le 10 ] && [ "$n" -ge 2 ] && ok || bad "store-growth" "kept $n copies after 15 versions"

echo "── review item 9: in a git clone the restore comes from HEAD, not from the store ──"
mk; printf '%s\n' "$GATE" > "$T/h/d.sh"
if git -C "$T/h" init -q 2>/dev/null && git -C "$T/h" add d.sh && git -C "$T/h" -c user.email=t@t -c user.name=t commit -qm x 2>/dev/null; then
  echo '{}' | bash "$T/h/hook_runner.sh" d.sh >/dev/null 2>&1
  printf '%s\n' "$WEAK" > "$(LGD)/d.sh.20200101T000000Z"; touch -t 203001010000 "$(LGD)/d.sh.20200101T000000Z"   # newest-looking planted copy
  printf '%s\n' "$SYNTAX" > "$T/h/d.sh"
  out=$(echo '{}' | bash "$T/h/hook_runner.sh" d.sh 2>&1); rc=$?
  [ "$rc" = 2 ] && echo "$out" | grep -q GATE-DENY && echo "$out" | grep -q 'git HEAD' && ok || bad "git-head" "rc=$rc out=$out"
else bad "git-head-fixture" "could not build a git fixture"; fi

echo "── review item 9: stdin really reaches the hook; JSON decision output passes through ──"
mk; printf '#!/bin/bash\nIN=$(cat); printf "{\\"decision\\":\\"block\\",\\"echo\\":%%s}\\n" "$(printf %%s "$IN" | wc -c | tr -d " ")"; exit 2\n' > "$T/h/j.sh"
out=$(printf 'abcdefghij' | bash "$T/h/hook_runner.sh" j.sh 2>/dev/null); rc=$?
[ "$rc" = 2 ] && [ "$out" = '{"decision":"block","echo":10}' ] && ok || bad "stdin-json" "rc=$rc out=$out"

echo "── review item 9: the restore alert is written for the session-start brief ──"
mk; printf '%s\n' "$GATE" > "$T/h/d.sh"; echo '{}' | bash "$T/h/hook_runner.sh" d.sh >/dev/null 2>&1
printf '%s\n' "$SYNTAX" > "$T/h/d.sh"; echo '{}' | bash "$T/h/hook_runner.sh" d.sh >/dev/null 2>&1
grep -q '"hook":"d.sh"' "$T/state/hooks-alert.json" 2>/dev/null && ok || bad "alert-json" "hooks-alert.json missing or wrong"

echo "$pass passed, $fail failed"; [ "$fail" = 0 ]
