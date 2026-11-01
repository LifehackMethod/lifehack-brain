#!/bin/bash
# wait.lib.sh — card TR1.8 of the skill-tester-rig: the ONE recognised handshake helper. Source it; never run it.
#
#   wait_until <secs> <what> <cmd…>
#       Re-runs <cmd…> until it succeeds (the HANDSHAKE: a file, marker or state the other side writes). Returns 0
#       as soon as it does. If <secs> pass first it prints exactly `WAIT-TIMEOUT <what>` on stderr and returns 1,
#       so the caller FAILS the case by name. A silent give-up is impossible: there is no other way out.
#
# Rule (waits_scan.sh enforces it): no rig script may sleep to wait for something. A wait is wait_until, or a loop
# whose body prints WAIT-TIMEOUT on expiry; a sleep that only paces (the sentinel's write interval, a watchdog's
# own timer, a hang stand-in) carries `# pacing: <why>` on its line. This file's poll interval is the one sleep the
# scan recognises as part of a handshake helper.
wait_until() {
  local secs="$1" what="$2" end
  shift 2
  case "$secs" in ''|*[!0-9]*) echo "WAIT-TIMEOUT $what (bad deadline '$secs')" >&2; return 1 ;; esac
  end=$(( $(date +%s) + secs ))
  while ! "$@"; do
    if [ "$(date +%s)" -ge "$end" ]; then echo "WAIT-TIMEOUT $what" >&2; return 1; fi
    sleep 0.05
  done
  return 0
}
