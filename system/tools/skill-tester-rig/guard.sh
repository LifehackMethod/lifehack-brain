#!/bin/bash
# guard.sh — card TR1.7 of the skill-tester-rig: the OS write guard (macOS sandbox-exec). bash 3.2 + BSD tools.
#
# The guard turns "the rig could not have written this" from a claim into a kernel-enforced property: run.sh
# re-executes ITSELF under `sandbox-exec -f <profile>`, so every process of the run (runner, budget.sh, the actor,
# code steps, checks, seam.sh, and later the real `claude` and its hooks) inherits the profile. Nothing is
# configured per tool.
#
#   guard.sh available                          exit 0 if sandbox-exec exists AND can run a trivial profile
#   guard.sh profile <tag> <scratch> <rig> <standin> [<extra-deny-root>...]
#                                               print the SBPL profile (see PROFILE below) to stdout
#   guard.sh denials <tag> <start> <barrier-path>
#                                               read the macOS unified log for this run's denials. <start> is local
#                                               time 'YYYY-MM-DD HH:MM:SS'. The caller has just attempted a write to
#                                               <barrier-path> (denied, tagged); this polls the log until that
#                                               denial appears (proof that the log is readable AND flushed past every
#                                               earlier denial of the run), then prints one denied path per line
#                                               (unique, sorted; the kernel's resolved path).
#                                               exit 0 ok · 4 CANNOT-READ (log unreadable, or the barrier never showed
#                                               within GUARD_LOG_WAIT seconds, default 15)
#
# PROFILE (order matters: in SBPL the LAST matching rule wins; verified empirically 2026-10-31 on macOS 27.0 —
# a deny on a subpath placed BEFORE the scratch allow is overridden by it, placed AFTER it bites):
#   (allow default)                          reads, exec, network, IPC unchanged: the guard is a WRITE guard only
#   (deny file-write* (with message TAG))    every write, everywhere, refused and logged with this run's TAG
#   (allow file-write* ...)                  ONLY:
#       <scratch>  (subpath)    the canonical ~/lifehack-scratch/skill-tester-rig: run dirs, seeds, plans, stage,
#                               judge-cache, budget, STATUS.md, seam snapshots, the run's TMPDIR (run.sh points
#                               TMPDIR at <scratch>/tmp/<run>, so the system temp dir needs NO allowance)
#       /dev/null  (literal)    every `>/dev/null` / `2>/dev/null` in the rig
#       /dev/tty   (literal)    bash probes the controlling tty at start (seen denied for every bash: file-write-data)
#       /dev/dtracehelper (literal)  dyld registers DTrace probes at EVERY process start (seen denied for bash, python,
#                               touch, rm, mkdir); without it each exec logs a denial (noise, and a false SEAM-DENIED)
#       /dev/fd    (subpath)    bash process substitution via /dev/fd/N
#       /private/tmp (literal, the DIRECTORY only) + /private/tmp/sh-thd-<digits> (regex)
#                               bash 3.2 here-documents IGNORE TMPDIR: bash access(W_OK)-probes /tmp and creates
#                               /tmp/sh-thd-<n> (unlinked at once). With /tmp denied, bash falls back to the CWD (seen:
#                               denials for <cwd>/sh-thd-<n>), or the here-doc fails and a `while read; done <<EOF`
#                               loop silently runs ZERO times (seen: a run that did no step and exited 0). The literal
#                               allows writes to the /tmp directory vnode only (root-owned, sticky: a user process
#                               cannot chmod/rename it); no other file under /tmp is writable
#     (found empirically: a fake run under a deny-all profile, then `log show` for every file-write denial; the rig
#      wrote nothing else. No /private/var/folders allowance is needed once TMPDIR is redirected.)
#   (deny file-write* (subpath <standin>) (with message TAG))   AFTER the allow: the notes stand-in is inside
#                               scratch but is SEAM SCOPE (the sentinel's playground), so the rig may never write it
#   (deny file-write* (subpath <rig>) (with message TAG))       the rig's own code is never a write target (catches a
#                               __pycache__ or a self-edit; in staging the rig lives under scratch)
#   (deny file-write* <extra-deny-root>... (with message TAG))  every seam root (state root, skill roots, hooks.json):
#                               redundant with the default deny when they lie outside scratch, decisive when a test
#                               points one inside it
set -u

available() {
  [ -x /usr/bin/sandbox-exec ] || return 1
  /usr/bin/sandbox-exec -p '(version 1)(allow default)' /usr/bin/true >/dev/null 2>&1
}

sbq() { printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"; }   # SBPL string literal

profile() {
  local tag="$1" scratch="$2" rig="$3" standin="$4"; shift 4
  local t; t="$(sbq "$tag")"
  echo "(version 1)"
  echo ";; skill-tester-rig write guard (guard.sh). Last matching rule wins."
  echo "(allow default)"
  echo "(deny file-write* (with message $t))"
  echo "(allow file-write*"
  echo "  (subpath $(sbq "$scratch"))"
  echo "  (literal \"/dev/null\") (literal \"/dev/tty\") (literal \"/dev/dtracehelper\") (subpath \"/dev/fd\")"
  echo "  (literal \"/private/tmp\") (regex #\"^/private/tmp/sh-thd-[0-9]+\$\"))"
  echo "(deny file-write* (subpath $(sbq "$standin")) (with message $t))"
  echo "(deny file-write* (subpath $(sbq "$rig")) (with message $t))"
  local r
  for r in "$@"; do
    [ -n "$r" ] || continue
    if [ -d "$r" ]; then echo "(deny file-write* (subpath $(sbq "$r")) (with message $t))"
    else echo "(deny file-write* (literal $(sbq "$r")) (with message $t))"; fi
  done
}

denials() {
  local tag="$1" start="$2" barrier="$3" wait="${GUARD_LOG_WAIT:-15}" i=0 out
  [ "${GUARD_TEST_NO_LOG:-}" = 1 ] && return 4        # test knob (selftest fail-first only): the log is "unreadable"
  while :; do
    out="$(/usr/bin/log show --start "$start" --style ndjson \
            --predicate "sender == \"Sandbox\" AND eventMessage CONTAINS \"$tag\"" 2>/dev/null)" || out=""
    if printf '%s\n' "$out" | python3 -I -B -c '
import json, re, sys
tag, barrier = sys.argv[1], sys.argv[2]
rx = re.compile(r"Sandbox: .*?\(\d+\) deny\(\d+\) file-write[a-z-]* (.*)$")
paths, seen_barrier = set(), False
for line in sys.stdin:
    try:
        m = json.loads(line).get("eventMessage") or ""
    except Exception:
        continue
    first, _, rest = m.partition("\n")
    if rest.strip() != tag:
        continue
    r = rx.search(first)
    if not r:
        continue
    p = r.group(1)
    if p == barrier:
        seen_barrier = True
        continue
    paths.add(p)
if not seen_barrier:
    sys.exit(4)
for p in sorted(paths):
    print(p)
' "$tag" "$barrier"; then return 0; fi
    i=$((i+1)); [ "$i" -ge "$wait" ] && return 4
    sleep 1
  done
}

case "${1:-}" in
  available) available ;;
  profile) [ $# -ge 5 ] || { echo "usage: guard.sh profile <tag> <scratch> <rig> <standin> [deny-root...]" >&2; exit 2; }
           shift; profile "$@" ;;
  denials) [ $# = 4 ] || { echo "usage: guard.sh denials <tag> <start> <barrier>" >&2; exit 2; }
           denials "$2" "$3" "$4" ;;
  *) echo "usage: guard.sh available | profile ... | denials <tag> <start> <barrier>" >&2; exit 2 ;;
esac
