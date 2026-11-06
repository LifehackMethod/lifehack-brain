#!/usr/bin/env bash
# test_job_run_fetch_hosts.sh -- job-run.sh adds the person's own allowed websites (<personal-code>/job-fetch-hosts.txt) to the plugin's list.
# Real job-run.sh, scratch manifest + state + personal folder under a throwaway HOME; the job only records SAFE_FETCH_ALLOWLIST. No network.
#   plugin hosts always present · a personal host is added after them · comments and blanks ignored · a missing personal file is fine
#   · an unreadable personal file is refused (78 through finish(): named on stderr, an errors/ file, last-run rc=78, the job never ran)
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
T="$(mktemp -d -t fetch-hosts)" || exit 1
trap 'chmod -R u+rwx "$T" 2>/dev/null; rm -rf "$T"' EXIT
export HOME="$T/home" LIFEHACK_STATE_DIR="$T/state" JOB_SIM_DIR="$T/sim" LIFEHACK_DESK_REPO="$T/pc"
mkdir -p "$HOME/.config/lifehack" "$JOB_SIM_DIR" "$T/pc/tools/hj"
printf '%s\n' "$T/pc" > "$HOME/.config/lifehack/personal-code"
printf '#!/usr/bin/env bash\necho "hosts=${SAFE_FETCH_ALLOWLIST:-none}" > "$JOB_SIM_DIR/out"\n' > "$T/pc/tools/hj/r.sh"
cat > "$T/jobs.md" <<ROWS
\`\`\`jobs
tj-hosts | yes | 3600 | records the hosts | \$JOB_SIM_DIR/out ~ hosts= | none | 0 | none | bash $T/pc/tools/hj/r.sh
\`\`\`
ROWS
export LIFEHACK_JOBS_FILE="$T/jobs.md"
printf '#!/usr/bin/env bash\nexit 0\n' > "$T/notify.sh"; export JOB_RUN_NOTIFY="$T/notify.sh"
fails=0; ck() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got '$2' wanted '$3'"; fails=$((fails+1)); fi; }
run() { rm -f "$JOB_SIM_DIR/out"; bash "$ROOT/system/tools/job-run.sh" tj-hosts --force 2>"$T/stderr" >/dev/null; echo $?; }
hosts() { cat "$JOB_SIM_DIR/out" 2>/dev/null; }
PLUGIN="$(grep -vE '^[[:space:]]*(#|$)' "$ROOT/system/tools/job-fetch-hosts.txt" | tr -d '[:blank:]' | paste -sd, -)"

ck "no personal file: runs"                       "$(run)" 0
ck "no personal file: exactly the plugin's list"  "$(hosts)" "hosts=$PLUGIN"

printf '# my sites\n\nnotes.example.org\n  api.example.net  \n' > "$T/pc/job-fetch-hosts.txt"
ck "personal file: runs"                          "$(run)" 0
ck "personal hosts follow the plugin's list"      "$(hosts)" "hosts=$PLUGIN,notes.example.org,api.example.net"

printf '# only comments\n\n' > "$T/pc/job-fetch-hosts.txt"
ck "comment-only personal file: runs"             "$(run)" 0
ck "comment-only personal file adds nothing"      "$(hosts)" "hosts=$PLUGIN"

printf 'notes.example.org\n' > "$T/pc/job-fetch-hosts.txt"; chmod 000 "$T/pc/job-fetch-hosts.txt"
if [ -r "$T/pc/job-fetch-hosts.txt" ]; then
  echo "skip unreadable-file cases (this user can read a mode 000 file)"
else
  ck "unreadable personal file: refused (78)"     "$(run)" 78
  ck "...the job never ran"                       "$([ -e "$JOB_SIM_DIR/out" ] && echo ran || echo not-run)" not-run
  ck "...stderr names the file"                   "$(grep -c "cannot be read: $T/pc/job-fetch-hosts.txt" "$T/stderr")" 1
  ck "...an errors/ file is written"              "$(ls "$LIFEHACK_STATE_DIR"/jobs/tj-hosts/errors/*.txt 2>/dev/null | wc -l | tr -d ' ')" 1
  ck "...last-run says rc=78"                     "$(grep -c ' rc=78 ' "$LIFEHACK_STATE_DIR/jobs/tj-hosts/last-run" 2>/dev/null)" 1
fi
chmod 644 "$T/pc/job-fetch-hosts.txt"
ck "readable again: runs"                         "$(run)" 0
ck "...and the host is back"                      "$(hosts)" "hosts=$PLUGIN,notes.example.org"
[ "$fails" -eq 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
