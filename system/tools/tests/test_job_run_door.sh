#!/usr/bin/env bash
# test_job_run_door.sh — 3.4b: job-run.sh refuses, at run time, a row that fails install-schedulers.sh --check-row.
# Real job-run.sh and real --check-row, scratch manifest + scratch state + scratch desk repo (LIFEHACK_DESK_REPO seam); notify stubbed, no network.
#   good row runs (0) · row failing the check refused (78, not 75, command never ran) · `|| true` in a runner refused · `|| true` on the row's command
#   refused · presence-grade / missing check refused · F7: a status tile named for another job refused at the door AND at run time (and the run-time
#   tile marker refuses a wrongly named tile) · OFF row stands down 75 · each refusal leaves one fire-journal line (hook job-run:check-row, event job-run)
#   · the live email-summary-write row passes --check-row.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
# A throwaway code root: every entry of the real one symlinked, except system/jobs.md, which is a real file here. The scripts run from it,
# so CODE_ROOT is this folder and its system/jobs.md is "the plugin's own list" (the origin rule compares real paths).
REAL_ROOT="$ROOT"; ROOT="$T/code"; mkdir -p "$ROOT/system"
for e in "$REAL_ROOT"/*; do [ "${e##*/}" = system ] || ln -s "$e" "$ROOT/${e##*/}"; done
for e in "$REAL_ROOT"/system/*; do [ "${e##*/}" = jobs.md ] || ln -s "$e" "$ROOT/system/${e##*/}"; done
export JOB_SIM_DIR="$T/sim"; mkdir -p "$JOB_SIM_DIR" "$T/desk/tools"/{good,swallow,tile,tilevar}
export LIFEHACK_DESK_REPO="$T/desk" LIFEHACK_STATE_DIR="$T/state" HOME="$T/home"; mkdir -p "$HOME"
printf '#!/usr/bin/env bash\necho "ran n=1" > "$JOB_SIM_DIR/out"\n' > "$T/desk/tools/good/r.sh"
printf '#!/usr/bin/env bash\npython3 safe_fetch.py http://x || true\necho "ran n=1" > "$JOB_SIM_DIR/out"\n' > "$T/desk/tools/swallow/r.sh"
export LHB_JOURNAL_PATH="$T/fire-journal.jsonl"
printf '#!/usr/bin/%s\nsource "$LIFEHACK_CODE_ROOT/system/tools/status-tile.lib.sh"\nwrite_status_tile "some-other-job" 0 3600 ok err\necho "ran n=1" > "$JOB_SIM_DIR/out"\n' env\ bash > "$T/desk/tools/tile/r.sh"
printf '#!/usr/bin/env bash\nSUBSYSTEM_NAME="tj-tilevar"\nsource "$LIFEHACK_CODE_ROOT/system/tools/status-tile.lib.sh"\nwrite_status_tile "$SUBSYSTEM_NAME" 0 3600 ok err\necho "ran n=1" > "$JOB_SIM_DIR/out"\n' > "$T/desk/tools/tilevar/r.sh"
G="bash $T/desk/tools/good/r.sh"; CK='$JOB_SIM_DIR/out ~ ran n=[1-9]'
cat > "$ROOT/system/jobs.md" <<ROWS
\`\`\`jobs
tj-good | yes | 3600 | does a thing | $CK | none | 0 | none | $G
tj-bad | yes | 3600 | does a thing | $CK | none | 0 | none | bash $T/desk/tools/swallow/r.sh
tj-inline | yes | 3600 | does a thing | $CK | none | 0 | none | $G || true
tj-presence | yes | 3600 | does a thing | \$JOB_SIM_DIR/out ~ ^.+\$ | none | 0 | none | $G
tj-notrow | yes | 3600 | does a thing | | none | 0 | none | $G
tj-tile | yes | 3600 | does a thing | $CK | none | 0 | none | bash $T/desk/tools/tile/r.sh
tj-tilevar | yes | 3600 | does a thing | $CK | none | 0 | none | bash $T/desk/tools/tilevar/r.sh
tj-off | no | 3600 | does a thing | $CK | none | 0 | none | bash $T/desk/tools/swallow/r.sh
\`\`\`
ROWS
export LIFEHACK_JOBS_FILE="$ROOT/system/jobs.md"
printf '#!/usr/bin/env bash\necho pushed >> "%s/notified"\n' "$T" > "$T/notify.sh"; export JOB_RUN_NOTIFY="$T/notify.sh"
fails=0; ck() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got '$2' wanted '$3'"; fails=$((fails+1)); fi; }
run() { bash "$ROOT/system/tools/job-run.sh" "$@" 2>"$T/stderr"; echo $?; }

ck "good row passes --check-row"                 "$(bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-good)" PASS
ck "good row runs (rc 0)"                         "$(run tj-good)" 0
rm -f "$T/notified"   # only the refusals are measured for pushes
for j in tj-bad tj-inline tj-presence tj-notrow tj-tile; do
  bash "$ROOT/system/tools/install-schedulers.sh" --check-row $j >/dev/null; ck "$j fails --check-row" "$?" 1
  rm -f "$JOB_SIM_DIR/out"
  ck "$j refused at run time (78)"                "$(run $j)" 78
  ck "$j: the command never ran"                  "$([ -e "$JOB_SIM_DIR/out" ] && echo ran || echo not-run)" not-run
  ck "$j: one REFUSED line on real stderr"        "$(grep -c '^\[job-run\] REFUSED' "$T/stderr")" 1
done
ck "a refused row also refused with --force"     "$(run tj-bad --force)" 78
# The scratch manifest IS the throwaway code root's system/jobs.md, so its rows are plugin-origin: the plugin variant. A personal-origin row (below) gets the personal one.
NEXT_STEP="Rulebook: \`system/sops/pr-sop.md\`. This job ships with the plugin: tell the person to report it. Don't edit plugin files, and don't copy the job under its own name to fix it."
NEXT_PERSONAL="Rulebook: \`system/sops/cron-jobs-sop.md\`, section \"Bring an existing job into line\". This job isn't in line yet: offer the person, in one short line, to bring it into line. Don't install it by hand."
ck "run-time refusal carries the next step (first and last line of the door output, so twice)" "$(grep -cF "door: $NEXT_STEP" "$T/stderr")" 2
ck "--check-row refusal ends with the next step"  "$(bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-bad | tail -1)" "$NEXT_STEP"
ck "--check-row refusal starts with the next step" "$(bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-bad | head -1)" "$NEXT_STEP"
# Origin by FILE: a manifest that is not the code root's own system/jobs.md (a worktree's jobs.md) is personal-origin, whatever block the row is in.
mkdir -p "$T/wt"; cp "$ROOT/system/jobs.md" "$T/wt/jobs.md"
ck "worktree-style LIFEHACK_JOBS_FILE refusal starts with the PERSONAL text" "$(LIFEHACK_JOBS_FILE="$T/wt/jobs.md" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-bad | head -1)" "$NEXT_PERSONAL"
ck "worktree-style LIFEHACK_JOBS_FILE refusal ends with the PERSONAL text" "$(LIFEHACK_JOBS_FILE="$T/wt/jobs.md" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-bad | tail -1)" "$NEXT_PERSONAL"
ck "PULSE_CONFIG at another file is personal-origin too" "$(env -u LIFEHACK_JOBS_FILE PULSE_CONFIG="$T/wt/jobs.md" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-bad | tail -1)" "$NEXT_PERSONAL"
ln -s "$ROOT/system/jobs.md" "$T/wt/link-to-plugin-jobs.md"
ck "a symlink to the code root's jobs.md is still plugin-origin (real paths)" "$(LIFEHACK_JOBS_FILE="$T/wt/link-to-plugin-jobs.md" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-bad | tail -1)" "$NEXT_STEP"
ck "no LIFEHACK_JOBS_FILE, LIFEHACK_CODE_ROOT at the throwaway root: plugin text" "$(env -u LIFEHACK_JOBS_FILE LIFEHACK_CODE_ROOT="$ROOT" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-bad | tail -1)" "$NEXT_STEP"
# Personal rows: a personal file joined over the scratch manifest (LIFEHACK_PERSONAL_JOBS_FILE seam; merged copy kept under the scratch dir).
export LIFEHACK_JOBS_MERGED_DIR="$T/merged"
cat > "$T/personal.md" <<ROWS
\`\`\`jobs
tj-pbad | yes | 3600 | does a thing | $CK | none | 0 | none | bash $T/desk/tools/swallow/r.sh
tj-good | yes | 7200 | does a thing | $CK | none | 0 | none | $G
\`\`\`
ROWS
ck "personal-origin refusal ends with the personal variant" "$(LIFEHACK_PERSONAL_JOBS_FILE="$T/personal.md" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-pbad 2>/dev/null | tail -1)" "$NEXT_PERSONAL"
ck "personal-origin refusal starts with the personal variant" "$(LIFEHACK_PERSONAL_JOBS_FILE="$T/personal.md" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-pbad 2>/dev/null | head -1)" "$NEXT_PERSONAL"
ck "plugin-origin refusal (shared row, personal file present) ends with the plugin variant" "$(LIFEHACK_PERSONAL_JOBS_FILE="$T/personal.md" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-bad 2>/dev/null | tail -1)" "$NEXT_STEP"
ck "no such row ends with the personal variant"   "$(LIFEHACK_PERSONAL_JOBS_FILE="$T/personal.md" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-nowhere 2>/dev/null | tail -1)" "$NEXT_PERSONAL"
ck "no such row starts with the personal variant" "$(LIFEHACK_PERSONAL_JOBS_FILE="$T/personal.md" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-nowhere 2>/dev/null | head -1)" "$NEXT_PERSONAL"
rm -f "$JOB_SIM_DIR/out"
ck "same-name personal copy of a passing shared row runs (rc 0)" "$(LIFEHACK_PERSONAL_JOBS_FILE="$T/personal.md" run tj-good)" 0
ck "...and the command really ran"                "$([ -e "$JOB_SIM_DIR/out" ] && echo ran || echo not-run)" ran
ck "...the clash warning was on the merged stream, last line PASS" "$(LIFEHACK_PERSONAL_JOBS_FILE="$T/personal.md" bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-good 2>&1 | sed -n '1p;$p' | tr '\n' ' ')" "[jobs_manifest] personal row 'tj-good' overrides the shared row of the same name PASS "
ck "refusal is a failed run: last-run says rc=78" "$(grep -c ' rc=78 ' "$LIFEHACK_STATE_DIR/jobs/tj-bad/last-run")" 1
ck "the door's reason is in the error file"       "$(cat "$LIFEHACK_STATE_DIR"/jobs/tj-bad/errors/* | grep -q "door: silenced" && echo yes || echo no)" yes
ck "each refusal left a fire-journal line (job-run:check-row / job-run)" "$(grep -c '"job-run:check-row"\|job-run:check-row' "$LHB_JOURNAL_PATH")" 6
ck "...with the event job-run"                    "$(grep 'job-run:check-row' "$LHB_JOURNAL_PATH" | grep -c 'job-run')" 6
ck "tile name rule: F7 reason names the job id"   "$(bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-tile | grep -c "status tile named 'some-other-job' but the job id is 'tj-tile'")" 1
ck "tile named by a variable set to the id passes the door" "$(bash "$ROOT/system/tools/install-schedulers.sh" --check-row tj-tilevar)" PASS
ck "tile-name variable job runs (rc 0)"           "$(run tj-tilevar)" 0
# the run-time tile marker: under job-run, write_status_tile refuses a tile named for another job (F7, defence beyond the static rule)
ck "run-time marker refuses a wrongly named tile" "$(LIFEHACK_JOB_RUN_ID=tj-a CODE_ROOT="$ROOT" bash -c 'source "$CODE_ROOT/system/tools/status-tile.lib.sh"; write_status_tile tj-b 0 60 ok err' 2>&1 >/dev/null | grep -c 'REFUSED status tile')" 1
ck "refusal left an errors/ file"                 "$([ -n "$(ls "$LIFEHACK_STATE_DIR/jobs/tj-bad/errors")" ] && echo yes || echo no)" yes
ck "OFF row (bad runner) still stands down 75"   "$(run tj-off)" 75
ck "live email-summary-write row passes --check-row" "$(LIFEHACK_JOBS_FILE= LIFEHACK_DESK_REPO= bash "$REAL_ROOT/system/tools/install-schedulers.sh" --check-row email-summary-write)" PASS
[ "$fails" -eq 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
