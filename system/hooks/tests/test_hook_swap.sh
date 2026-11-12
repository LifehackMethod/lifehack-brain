#!/bin/bash
# test_hook_swap.sh -- system/tools/hook_swap.sh: refuses bad candidates, keeps last-good, swaps atomically.
# Run: bash system/hooks/tests/test_hook_swap.sh   (exit 0 = all pass)
HOOKS="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$HOOKS/../.." && pwd)"
SWAP="$REPO/system/tools/hook_swap.sh"
[ -f "$SWAP" ] || { echo "CANNOT RUN: no $SWAP"; exit 1; }
pass=0; fail=0
ok()  { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "  FAIL [$1]: $2"; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export LIFEHACK_HOOKS_LASTGOOD="$T/lg" LIFEHACK_STATE_DIR="$T/state"
L="<<<<<<<"
# the store is per live folder: <lg>/<cksum of the real live path>/
LGD() { echo "$T/lg/$(printf '%s' "$(cd "$T/live" && pwd -P)" | cksum | cut -d' ' -f1)"; }
# worktree-ish layout: $T/wt/system/hooks/<hook>.sh + tests/, live dir $T/live
fresh() { rm -rf "$T/wt" "$T/live" "$T/lg"; mkdir -p "$T/wt/system/hooks/tests" "$T/live"
  printf '#!/bin/bash\necho OLD\n' > "$T/live/h.sh"; chmod 755 "$T/live/h.sh"
  printf '#!/bin/bash\necho NEW\n' > "$T/wt/system/hooks/h.sh"
  printf '#!/bin/bash\n[ "$(bash "${HOOK_UNDER_TEST:-x}")" = NEW ]\n' > "$T/wt/system/hooks/tests/test_h.sh"; }
swap() { bash "$SWAP" --live-dir "$T/live" "$@" 2>&1; }

bash -n "$SWAP" && ok || bad syntax "hook_swap.sh fails bash -n"
bash "$SWAP" --help >/dev/null 2>&1 && ok || bad help "--help must exit 0 (smoke-check probes it)"

echo "── good candidate: tested, last-good kept, swapped ──"
fresh; out=$(swap "$T/wt/system/hooks/h.sh"); rc=$?
[ $rc = 0 ] && [ "$(bash "$T/live/h.sh")" = NEW ] && ok || bad swap "rc=$rc $out"
n=$(ls "$(LGD)"/h.sh.2* 2>/dev/null | wc -l); n=$((n+0)); [ "$n" = 1 ] && [ "$(bash "$(ls "$(LGD)"/h.sh.2*)")" = OLD ] && ok || bad lastgood "last-good missing or not the OLD file"
ls -a "$T/live" | grep -q 'swap' && bad temp "temp swap file left behind" || ok

echo "── refusals leave the live file untouched ──"
fresh; printf '#!/bin/bash\nif true; then\n' > "$T/wt/system/hooks/h.sh"
out=$(swap "$T/wt/system/hooks/h.sh"); rc=$?; [ $rc = 1 ] && [ "$(bash "$T/live/h.sh")" = OLD ] && ok || bad syntaxerr "rc=$rc"
fresh; printf '#!/bin/bash\n%s HEAD\necho NEW\n' "$L" > "$T/wt/system/hooks/h.sh"
out=$(swap "$T/wt/system/hooks/h.sh"); rc=$?; [ $rc = 1 ] && [ "$(bash "$T/live/h.sh")" = OLD ] && ok || bad markers "rc=$rc"
fresh; printf '#!/bin/bash\necho WRONG\n' > "$T/wt/system/hooks/h.sh"
out=$(swap "$T/wt/system/hooks/h.sh"); rc=$?; [ $rc = 1 ] && [ "$(bash "$T/live/h.sh")" = OLD ] && ok || bad testfail "failing test must refuse, rc=$rc"
fresh; rm "$T/wt/system/hooks/tests/test_h.sh"
out=$(swap "$T/wt/system/hooks/h.sh"); rc=$?; [ $rc = 1 ] && [ "$(bash "$T/live/h.sh")" = OLD ] && ok || bad notest "missing test must refuse, rc=$rc"
out=$(swap --no-test "$T/wt/system/hooks/h.sh"); rc=$?; [ $rc = 0 ] && [ "$(bash "$T/live/h.sh")" = NEW ] && ok || bad nofn "--no-test rc=$rc"
fresh; out=$(swap "$T/live/h.sh"); [ $? = 2 ] && ok || bad self "candidate==live must be refused"

echo "── a broken CURRENT live file is not saved as last-good ──"
fresh; printf '#!/bin/bash\nif true; then\n' > "$T/live/h.sh"
swap "$T/wt/system/hooks/h.sh" >/dev/null; n=$(ls "$(LGD)"/h.sh.2* 2>/dev/null | wc -l); n=$((n+0))
[ "$n" = 0 ] && [ "$(bash "$T/live/h.sh")" = NEW ] && ok || bad brokenlive "n=$n"

echo "── retention: newest 10 kept ──"
fresh; mkdir -p "$(LGD)"; for i in 01 02 03 04 05 06 07 08 09 10 11 12; do printf '#!/bin/bash\n:\n' > "$(LGD)/h.sh.202001${i}T000000Z"; done
swap "$T/wt/system/hooks/h.sh" >/dev/null; n=$(ls "$(LGD)"/h.sh.2* | wc -l); n=$((n+0)); [ "$n" = 10 ] && ok || bad prune "kept $n"

echo "── the swap command itself is not blocked by the hook-SOP guard ──"
printf '{"tool_name":"Bash","tool_input":{"command":"bash system/tools/hook_swap.sh /tmp/wt/system/hooks/guard_x.sh"},"session_id":"nosuch-%s"}' "$$" \
  | bash "$HOOKS/guard_hook_sop_read.sh" >/dev/null 2>&1; [ $? = 0 ] && ok || bad sopguard "guard_hook_sop_read blocks hook_swap.sh"

echo "$pass passed, $fail failed"; [ "$fail" = 0 ]
