#!/usr/bin/env bash
# test_job_run_door_mark.sh — the "outside the checker, by choice" mark (owner's ruling 2026-11-05).
# A PERSONAL row the door refuses, with `# outside the checker, by choice, YYYY-MM-DD` directly above it, passes --check-row (warning first,
# PASS last, rc 0) and runs under job-run.sh. Unmarked, plugin-origin or malformed-mark rows are still refused. Scratch HOME, scratch desk.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
# A throwaway code root: every entry of the real one symlinked, except system/jobs.md, which is a real file here. The scripts run from it,
# so CODE_ROOT is this folder and its system/jobs.md is "the plugin's own list" (the origin rule compares real paths).
REAL_ROOT="$ROOT"; ROOT="$T/code"; mkdir -p "$ROOT/system"
for e in "$REAL_ROOT"/*; do [ "${e##*/}" = system ] || ln -s "$e" "$ROOT/${e##*/}"; done
for e in "$REAL_ROOT"/system/*; do [ "${e##*/}" = jobs.md ] || ln -s "$e" "$ROOT/system/${e##*/}"; done
export JOB_SIM_DIR="$T/sim"; mkdir -p "$JOB_SIM_DIR" "$T/desk/tools"/{good,swallow}
export LIFEHACK_DESK_REPO="$T/desk" LIFEHACK_STATE_DIR="$T/state" HOME="$T/home" LIFEHACK_JOBS_MERGED_DIR="$T/merged"; mkdir -p "$HOME"
export LHB_JOURNAL_PATH="$T/fire-journal.jsonl"
printf '#!/usr/bin/env bash\necho "ran n=1" > "$JOB_SIM_DIR/out"\n' > "$T/desk/tools/good/r.sh"
printf '#!/usr/bin/env bash\npython3 safe_fetch.py http://x || true\necho "ran n=1" > "$JOB_SIM_DIR/out"\n' > "$T/desk/tools/swallow/r.sh"
G="bash $T/desk/tools/good/r.sh"; S="bash $T/desk/tools/swallow/r.sh"; CK='$JOB_SIM_DIR/out ~ ran n=[1-9]'
M="# outside the checker, by choice, 2026-11-05"
cat > "$ROOT/system/jobs.md" <<ROWS
\`\`\`jobs
tj-good | yes | 3600 | does a thing | $CK | none | 0 | none | $G
$M
tj-plugmarked | yes | 3600 | does a thing | $CK | none | 0 | none | $S
\`\`\`
ROWS
cat > "$T/personal.md" <<ROWS
\`\`\`jobs
$M
tj-pmarked | yes | 3600 | does a thing | $CK | none | 0 | none | $S
tj-punmarked | yes | 3600 | does a thing | $CK | none | 0 | none | $S
# outside the checker, by choice
tj-pnodate | yes | 3600 | does a thing | $CK | none | 0 | none | $S
# outside the checker, by choice, 2026-02-30
tj-pbaddate | yes | 3600 | does a thing | $CK | none | 0 | none | $S
# outside the checker, by choice, 2026-11-05 and more
tj-pextra | yes | 3600 | does a thing | $CK | none | 0 | none | $S
$M

tj-pgap | yes | 3600 | does a thing | $CK | none | 0 | none | $S
$M
tj-pgood | yes | 3600 | does a thing | $CK | none | 0 | none | $G
\`\`\`
ROWS
export LIFEHACK_JOBS_FILE="$ROOT/system/jobs.md" LIFEHACK_PERSONAL_JOBS_FILE="$T/personal.md"
printf '#!/usr/bin/env bash\ntrue\n' > "$T/notify.sh"; export JOB_RUN_NOTIFY="$T/notify.sh"
fails=0; ck() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got '$2' wanted '$3'"; fails=$((fails+1)); fi; }
IS="$ROOT/system/tools/install-schedulers.sh"
row() { bash "$IS" --check-row "$1" 2>/dev/null; echo "rc=$?"; }
OUT="$(row tj-pmarked)"
ck "marked personal refused row: first line is the warning" "$(printf '%s\n' "$OUT" | head -1 | grep -c '^outside the checker, by choice (2026-11-05): ')" 1
ck "...last line before rc is PASS"       "$(printf '%s\n' "$OUT" | tail -2 | head -1)" PASS
ck "...rc 0"                              "$(printf '%s\n' "$OUT" | tail -1)" rc=0
rm -f "$JOB_SIM_DIR/out"
bash "$ROOT/system/tools/job-run.sh" tj-pmarked --force >/dev/null 2>&1; ck "...runs under job-run.sh (rc 0)" "$?" 0
ck "...and the command really ran"        "$([ -e "$JOB_SIM_DIR/out" ] && echo ran || echo not-run)" ran
for j in tj-punmarked tj-pnodate tj-pbaddate tj-pextra tj-pgap; do
  ck "$j (no valid mark directly above) is refused" "$(row $j | tail -1)" rc=1
done
ck "unmarked row refused at run time (78)" "$(bash "$ROOT/system/tools/job-run.sh" tj-punmarked --force >/dev/null 2>&1; echo $?)" 78
ck "marked PLUGIN row is still refused with the plugin text" "$(bash "$IS" --check-row tj-plugmarked 2>/dev/null | tail -1 | cut -c1-39)" "Rulebook: \`system/sops/pr-sop.md\`. This"
ck "marked PLUGIN row refusal also starts with the plugin text" "$(bash "$IS" --check-row tj-plugmarked 2>/dev/null | head -1 | cut -c1-39)" "Rulebook: \`system/sops/pr-sop.md\`. This"
ck "marked plugin row: rc 1"              "$(row tj-plugmarked | tail -1)" rc=1
ck "passing shared row unaffected"        "$(bash "$IS" --check-row tj-good 2>/dev/null)" PASS
ck "passing personal row under a mark: plain PASS, no warning" "$(bash "$IS" --check-row tj-pgood 2>/dev/null)" PASS
# install plan: marked personal row installable with the warning; unmarked ones refused
PLAN="$(LAUNCHAGENTS_DIR="$T/la" bash "$IS" 2>&1)"
ck "plan: marked personal row listed"     "$(printf '%s\n' "$PLAN" | grep -c 'WOULD WRITE .*ai.lifehack.tj-pmarked.plist')" 1
ck "plan: one-line warning for it"        "$(printf '%s\n' "$PLAN" | grep -c 'WARNING tj-pmarked: outside the checker, by choice (2026-11-05): ')" 1
ck "plan: unmarked personal row refused"  "$(printf '%s\n' "$PLAN" | grep -c 'REFUSED tj-punmarked')" 1
ck "plan: marked plugin row refused"      "$(printf '%s\n' "$PLAN" | grep -c 'REFUSED tj-plugmarked')" 1
ck "plan: malformed marks refused"        "$(printf '%s\n' "$PLAN" | grep -c 'REFUSED tj-p\(nodate\|baddate\|extra\|gap\)')" 4
[ "$fails" -eq 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
