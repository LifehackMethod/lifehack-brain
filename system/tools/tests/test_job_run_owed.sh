#!/usr/bin/env bash
# test_job_run_owed.sh -- "owed, not scheduled" (v2 spec item 8): a daily-or-longer row is owed once per calendar day (per N days),
# counted from the previous due point, not from a fixed age since the last success. Planted cases, each fake-clocked
# (LIFEHACK_FAKE_NOW), scratch manifest, scratch state root, TZ=UTC; real job-run.sh; nothing real is touched.
#   (a) a daytime catch-up, then the next day: day 2 runs on its first wake, no skipped day
#   (b) the Mac asleep through the due time (midnight): it runs once on wake
#   (c) three days closed: ONE run on wake, and the day after still runs
#   control: a row already run today does NOT run again on another wake the same day
#   sub-daily control: a 1 h row keeps the age rule (stands down at 30 min, runs at 59 min after grace)
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export TZ=UTC
REAL_ROOT="$ROOT"; ROOT="$T/code"; mkdir -p "$ROOT/system"
for e in "$REAL_ROOT"/*; do [ "${e##*/}" = system ] || ln -s "$e" "$ROOT/${e##*/}"; done
for e in "$REAL_ROOT"/system/*; do [ "${e##*/}" = jobs.md ] || ln -s "$e" "$ROOT/system/${e##*/}"; done
export JOB_SIM_DIR="$T/sim"; mkdir -p "$JOB_SIM_DIR" "$T/desk/tools/good"
export LIFEHACK_DESK_REPO="$T/desk" LIFEHACK_STATE_DIR="$T/state" HOME="$T/home"; mkdir -p "$HOME"
printf '#!/usr/bin/env bash\necho "ran n=1" > "$JOB_SIM_DIR/out"\n' > "$T/desk/tools/good/r.sh"
G="bash $T/desk/tools/good/r.sh"; CK='$JOB_SIM_DIR/out ~ ran n=[1-9]'
cat > "$ROOT/system/jobs.md" <<ROWS
\`\`\`jobs
tj-daily | yes | 86400 | does a thing | $CK | none | 0 | none | $G
tj-weekly | yes | 604800 | does a thing | $CK | none | 0 | none | $G
tj-hourly | yes | 3600 | does a thing | $CK | none | 0 | none | $G
\`\`\`
ROWS
export LIFEHACK_JOBS_FILE="$ROOT/system/jobs.md"
printf '#!/usr/bin/env bash\nexit 0\n' > "$T/notify.sh"; export JOB_RUN_NOTIFY="$T/notify.sh"
fails=0; ck() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got '$2' wanted '$3'"; fails=$((fails+1)); fi; }
D0="$(date -u -j -f %Y%m%d%H%M%S 20261110000000 +%s 2>/dev/null || date -u -d 2026-11-10T00:00:00 +%s)"   # day 1, 00:00 UTC
at() { echo $(( D0 + ($1 - 1) * 86400 + $2 * 3600 + ${3:-0} * 60 )); }   # at <day> <hour> [min]
wake() { # job epoch -> rc of one --if-overdue wake (0 ran, 75 stood down)
  LIFEHACK_FAKE_NOW="$2" bash "$ROOT/system/tools/job-run.sh" "$1" --if-overdue >/dev/null 2>&1; echo $?; }
reset() { rm -rf "$T/state"; }

# (a) daytime catch-up, then the next day
reset
ck "a: day 0 morning run (seed)"                        "$(wake tj-daily "$(at 0 7)")" 0
ck "a: day 1 morning missed, caught up at 15:00"        "$(wake tj-daily "$(at 1 15)")" 0
ck "a: day 2 first wake 07:30 RUNS (no skipped day)"    "$(wake tj-daily "$(at 2 7 30)")" 0

# (b) asleep through the due time: last run 23:30, lid shut over midnight, first wake 07:00
reset
ck "b: seed run day 1 23:30"                            "$(wake tj-daily "$(at 1 23 30)")" 0
ck "b: asleep through 00:00, first wake day 2 07:00 runs" "$(wake tj-daily "$(at 2 7)")" 0
ck "b: the next wake an hour later stands down"         "$(wake tj-daily "$(at 2 8)")" 75

# (c) three days closed: one run, and the day after still runs
reset
ck "c: seed run day 1 15:00"                            "$(wake tj-daily "$(at 1 15)")" 0
ck "c: closed days 2-4; wake day 4 10:00 runs ONCE"     "$(wake tj-daily "$(at 4 10)")" 0
ck "c: second wake day 4 11:00 stands down (not three)" "$(wake tj-daily "$(at 4 11)")" 75
ck "c: day 5 first wake runs"                           "$(wake tj-daily "$(at 5 8)")" 0

# control: already run today -> a later wake the same day does not run again
reset
ck "control: morning run"                               "$(wake tj-daily "$(at 3 6)")" 0
ck "control: wake 10:00 same day stands down"           "$(wake tj-daily "$(at 3 10)")" 75
ck "control: wake 23:59 same day stands down"           "$(wake tj-daily "$(at 3 23 59)")" 75

# weekly: owed 7 calendar days after the last success's day
reset
ck "weekly: seed day 1 15:00"                           "$(wake tj-weekly "$(at 1 15)")" 0
ck "weekly: day 7 stands down"                          "$(wake tj-weekly "$(at 7 9)")" 75
ck "weekly: day 8 runs"                                 "$(wake tj-weekly "$(at 8 7)")" 0

# sub-daily control: the age rule is unchanged
reset
ck "hourly: seed"                                       "$(wake tj-hourly "$(at 1 9)")" 0
ck "hourly: 30 min later stands down"                   "$(wake tj-hourly "$(at 1 9 30)")" 75
ck "hourly: 56 min later runs (grace)"                  "$(wake tj-hourly "$(at 1 9 56)")" 0

[ "$fails" -eq 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
