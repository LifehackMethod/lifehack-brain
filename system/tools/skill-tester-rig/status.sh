#!/bin/bash
# status.sh — write the skill-tester-rig STATUS.md (card TR0.1).
#
# Usage:
#   status.sh <rung> <run-id> <step> <cost-so-far> <last-event>
#   status.sh selftest
#
# Writes $SKILL_TESTER_SCRATCH/STATUS.md (default ~/lifehack-scratch/skill-tester-rig/STATUS.md)
# atomically (temp file + mv). Elapsed is measured from a per-run start stamp
# ($SCRATCH/.start-<run-id>, epoch seconds) created on the first call for that run.
# Portable: macOS bash 3.2 + BSD tools. Never writes to Google Drive (ruling 6).

set -u

usage() {
  echo "usage: status.sh <rung> <run-id> <step> <cost-so-far> <last-event> | status.sh selftest" >&2
}

fmt_elapsed() {
  # seconds -> HhMMmSSs
  local s=$1
  printf '%dh%02dm%02ds' $((s / 3600)) $(((s % 3600) / 60)) $((s % 60))
}

write_status() {
  if [ "$#" -ne 5 ]; then
    echo "status.sh: expected 5 args, got $#" >&2
    usage
    return 2
  fi
  local rung=$1 run_id=$2 step=$3 cost=$4 event=$5
  local f
  for f in "$rung" "$run_id" "$step" "$cost"; do
    if [ -z "$f" ]; then
      echo "status.sh: empty argument not allowed (rung/run-id/step/cost)" >&2
      return 2
    fi
  done
  case "$run_id" in
    */* | .* ) echo "status.sh: run-id must not contain '/' or start with '.'" >&2; return 2 ;;
  esac
  case "$cost" in
    *[!0-9.]* | *.*.* | .) echo "status.sh: cost-so-far must be a number (got '$cost')" >&2; return 2 ;;
  esac

  local scratch="${SKILL_TESTER_SCRATCH:-$HOME/lifehack-scratch/skill-tester-rig}"
  case "$scratch" in
    *GoogleDrive* | *CloudStorage* ) echo "status.sh: refusing Drive path '$scratch' (ruling 6)" >&2; return 3 ;;
  esac
  mkdir -p "$scratch" || { echo "status.sh: cannot create $scratch" >&2; return 3; }

  local now stamp start
  now=$(date +%s)
  stamp="$scratch/.start-$run_id"
  if [ ! -s "$stamp" ]; then
    echo "$now" > "$stamp" || { echo "status.sh: cannot write $stamp" >&2; return 3; }
  fi
  start=$(cat "$stamp")
  case "$start" in
    '' | *[!0-9]*) echo "status.sh: corrupt start stamp $stamp" >&2; return 3 ;;
  esac
  local elapsed=$((now - start))
  [ "$elapsed" -lt 0 ] && elapsed=0

  local updated tmp
  updated=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  tmp=$(mktemp "$scratch/.STATUS.md.XXXXXX") || { echo "status.sh: mktemp failed" >&2; return 3; }
  {
    echo "# skill-tester-rig STATUS"
    echo
    echo "- rung: $rung"
    echo "- run-id: $run_id"
    echo "- step: $step"
    echo "- elapsed: $(fmt_elapsed "$elapsed") ($elapsed s)"
    echo "- cost-so-far: \$$cost"
    echo "- last-event: $event"
    echo "- updated-at: $updated"
  } > "$tmp" || { rm -f "$tmp"; echo "status.sh: write failed" >&2; return 3; }
  mv -f "$tmp" "$scratch/STATUS.md" || { rm -f "$tmp"; echo "status.sh: mv failed" >&2; return 3; }
  return 0
}

selftest() {
  local self="$0" dir rc fail=0
  dir=$(mktemp -d "${TMPDIR:-/tmp}/status-selftest.XXXXXX") || { echo "SELFTEST FAIL: mktemp"; return 1; }

  # Ruling 12: watch the checks refuse bad input first.
  SKILL_TESTER_SCRATCH="$dir" /bin/bash "$self" R0 run1 >/dev/null 2>&1; rc=$?
  if [ "$rc" -ne 0 ]; then echo "refused missing args (rc=$rc): ok"; else echo "FAIL: missing args accepted"; fail=1; fi
  SKILL_TESTER_SCRATCH="$dir" /bin/bash "$self" R0 run1 s1 abc "ev" >/dev/null 2>&1; rc=$?
  if [ "$rc" -ne 0 ]; then echo "refused non-numeric cost (rc=$rc): ok"; else echo "FAIL: bad cost accepted"; fail=1; fi
  SKILL_TESTER_SCRATCH="$dir" /bin/bash "$self" R0 ../x s1 0 "ev" >/dev/null 2>&1; rc=$?
  if [ "$rc" -ne 0 ]; then echo "refused path-traversal run-id (rc=$rc): ok"; else echo "FAIL: bad run-id accepted"; fail=1; fi
  if [ -e "$dir/STATUS.md" ]; then echo "FAIL: STATUS.md written by a refused call"; fail=1; fi

  # Field check must itself fail on a broken file before we trust it.
  printf '# skill-tester-rig STATUS\n- rung: R0\n' > "$dir/broken.md"
  if check_fields "$dir/broken.md" 2>/dev/null; then echo "FAIL: field check passed a broken file"; fail=1
  else echo "field check refused broken STATUS: ok"; fi

  # Good path.
  SKILL_TESTER_SCRATCH="$dir" /bin/bash "$self" R1 run-st step-1 0.00 "started" || { echo "FAIL: good call rc=$?"; fail=1; }
  SKILL_TESTER_SCRATCH="$dir" /bin/bash "$self" R1 run-st step-2 0.42 "step 1 done" || { echo "FAIL: second call rc=$?"; fail=1; }
  if check_fields "$dir/STATUS.md"; then echo "fields present: ok"; else fail=1; fi
  grep -q '^- step: step-2$' "$dir/STATUS.md" || { echo "FAIL: step not updated"; fail=1; }
  grep -q '^- cost-so-far: \$0.42$' "$dir/STATUS.md" || { echo "FAIL: cost not updated"; fail=1; }
  [ -s "$dir/.start-run-st" ] || { echo "FAIL: start stamp missing"; fail=1; }
  ls "$dir"/.STATUS.md.* >/dev/null 2>&1 && { echo "FAIL: temp file left behind"; fail=1; }

  rm -rf "$dir"
  if [ "$fail" -eq 0 ]; then echo "SELFTEST OK"; return 0; fi
  echo "SELFTEST FAIL"; return 1
}

check_fields() {
  local file=$1 k missing=0
  for k in rung run-id step elapsed cost-so-far last-event updated-at; do
    if ! grep -q "^- $k: ." "$file"; then echo "missing field: $k" >&2; missing=1; fi
  done
  return $missing
}

if [ "${1:-}" = "selftest" ] && [ "$#" -eq 1 ]; then
  selftest; exit $?
fi
write_status "$@"; exit $?
