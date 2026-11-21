#!/usr/bin/env bash
# test_install_schedulers_own_agents.sh -- install-schedulers.sh on macOS (V2 cr9, 2026-11-21):
#   (a) a dry run (LIFEHACK_INSTALL_DRY_RUN=1) changes nothing: no bootout, no delete, no overwrite, no record,
#       and nothing at all under the real-default agents folder;
#   (b) a real install boots out and deletes ONLY its own agents (row names in the jobs list, on or off, plus the
#       labels it recorded writing last time); a foreign ai.lifehack.* agent survives, untouched and still loaded.
# Stubs only: a fake launchctl, a temp HOME and a temp LAUNCHAGENTS_DIR. Never the real ~/Library/LaunchAgents.
# INSTALL_SCHEDULERS_UNDER_TEST points the cases at another copy of the installer (used to show them failing first).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT="${INSTALL_SCHEDULERS_UNDER_TEST:-$ROOT/system/tools/install-schedulers.sh}"
T="$(mktemp -d "${TMPDIR:-/tmp}/tinstown.XXXXXX")"; trap 'rm -rf "$T"' EXIT
FAILS=0
pass() { echo "$1 PASS"; }
fail() { echo "$1 FAIL ${2:-}"; FAILS=$((FAILS+1)); }

mkdir -p "$T/code/system/tools" "$T/bin"
printf '#!/usr/bin/env bash\necho ran n=1 items\n' > "$T/code/system/tools/ok-run.sh"
cat > "$T/bin/launchctl" <<'STUB'
#!/bin/bash
if [ "$1" = list ]; then
  echo "PID	Status	Label"
  for l in $STUB_LOADED; do echo "-	0	$l"; done
  exit 0
fi
echo "launchctl $*" >> "$STUBLOG"
exit 0
STUB
chmod +x "$T/bin/launchctl"

ROW() { # name enabled -> a door-passing jobs row
  printf '%s | %s | 600 | o. | $HOME/x ~ ^ran n=[0-9]+ items | none | 0 | none | bash "$LIFEHACK_CODE_ROOT/system/tools/ok-run.sh"' "$1" "$2"
}
OLD='<?xml version="1.0"?><plist version="1.0"><dict><key>Label</key><string>OLD</string></dict></plist>'

# fresh <rows...>: new HOME, agents dir seeded with a managed jmine, a foreign other, an off-row joff
fresh() {
  rm -rf "$T/fakehm" "$T/la"; mkdir -p "$T/fakehm" "$T/la"; : > "$T/log"
  { printf '```jobs\n'; for r in "$@"; do printf '%s\n' "$r"; done; printf '```\n'; } > "$T/manifest.md"
  for n in jmine other joff; do printf '%s\n' "$OLD" > "$T/la/ai.lifehack.$n.plist"; done
}
# run [env...] -> runs the installer --install with the stubs; RC set
run() {
  env STUBLOG="$T/log" STUB_LOADED="ai.lifehack.jmine ai.lifehack.other ai.lifehack.joff" PATH="$T/bin:$PATH" \
    PULSE_CONFIG="$T/manifest.md" LIFEHACK_CODE_ROOT="$T/code" LIFEHACK_DESK_REPO="$T/nodesk" HOME="$T/fakehm" \
    LIFEHACK_TEST_OS_OVERRIDE=mac "$@" bash "$SCRIPT" --install >"$T/out" 2>"$T/err"
  RC=$?
}
same_old() { [ -f "$1" ] && [ "$(cat "$1")" = "$OLD" ]; }
REC="$T/fakehm/.config/lifehack/state/install-schedulers.managed"

# ── 1) dry run: every plist stays, unchanged; no bootout; no record ──
fresh "$(ROW jmine yes)" "$(ROW joff off)"
run LAUNCHAGENTS_DIR="$T/la" LIFEHACK_INSTALL_DRY_RUN=1
same_old "$T/la/ai.lifehack.jmine.plist" && same_old "$T/la/ai.lifehack.other.plist" && same_old "$T/la/ai.lifehack.joff.plist" \
  && pass "d1-dry-run-leaves-every-plist" || fail "d1-dry-run-leaves-every-plist" "rc=$RC; left: $(ls "$T/la" | tr '\n' ' ')"
grep -q bootout "$T/log" && fail "d2-dry-run-no-bootout" "$(cat "$T/log")" || pass "d2-dry-run-no-bootout"
[ ! -e "$REC" ] && pass "d3-dry-run-no-record" || fail "d3-dry-run-no-record"
grep -q "would delete: $T/la/ai.lifehack.jmine.plist" "$T/out" && pass "d4-dry-run-says-what-it-would-delete" \
  || fail "d4-dry-run-says-what-it-would-delete" "$(head -c 300 "$T/out")"

# ── 2) dry run at the real-default folder (LAUNCHAGENTS_DIR unset; HOME is temp): nothing is created there ──
fresh "$(ROW jmine yes)"
run LIFEHACK_INSTALL_DRY_RUN=1
[ ! -e "$T/fakehm/Library/LaunchAgents" ] && pass "d5-dry-run-never-writes-default-folder" \
  || fail "d5-dry-run-never-writes-default-folder" "$(ls -R "$T/fakehm/Library" 2>&1 | head -5)"

# ── 3) real install: only its own agents ──
fresh "$(ROW jmine yes)" "$(ROW joff off)"
run LAUNCHAGENTS_DIR="$T/la"
[ "$RC" -eq 0 ] && pass "r0-install-ok" || fail "r0-install-ok" "rc=$RC err=$(head -c 200 "$T/err")"
same_old "$T/la/ai.lifehack.other.plist" && pass "r1-foreign-plist-survives" || fail "r1-foreign-plist-survives"
grep -q "bootout gui/[0-9]*/ai.lifehack.other" "$T/log" && fail "r2-foreign-agent-not-booted-out" "$(cat "$T/log")" \
  || pass "r2-foreign-agent-not-booted-out"
{ [ -f "$T/la/ai.lifehack.jmine.plist" ] && ! same_old "$T/la/ai.lifehack.jmine.plist" \
    && grep -q 'job-run.sh' "$T/la/ai.lifehack.jmine.plist"; } && pass "r3-managed-row-rewritten" || fail "r3-managed-row-rewritten"
grep -q "bootout gui/[0-9]*/ai.lifehack.jmine" "$T/log" && pass "r4-managed-agent-booted-out" || fail "r4-managed-agent-booted-out" "$(cat "$T/log")"
[ ! -e "$T/la/ai.lifehack.joff.plist" ] && pass "r5-off-row-agent-removed" || fail "r5-off-row-agent-removed"
grep -qx "ai.lifehack.jmine" "$REC" 2>/dev/null && pass "r6-record-lists-what-it-wrote" || fail "r6-record-lists-what-it-wrote"

# ── 4) an agent it recorded writing, whose row has since left the list, is removed (and leaves the record) ──
mkdir -p "$(dirname "$REC")"; printf 'ai.lifehack.jmine\nai.lifehack.gone\n' > "$REC"
printf '%s\n' "$OLD" > "$T/la/ai.lifehack.gone.plist"; : > "$T/log"
run LAUNCHAGENTS_DIR="$T/la"
[ ! -e "$T/la/ai.lifehack.gone.plist" ] && ! grep -qx ai.lifehack.gone "$REC" && same_old "$T/la/ai.lifehack.other.plist" \
  && pass "r7-recorded-agent-removed-foreign-kept" || fail "r7-recorded-agent-removed-foreign-kept" "$(ls "$T/la" | tr '\n' ' ')"

[ "$FAILS" -eq 0 ] || echo "$FAILS case(s) FAILED"
exit "$FAILS"
