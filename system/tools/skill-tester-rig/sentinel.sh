#!/bin/bash
# sentinel.sh — card TR1.7 of the skill-tester-rig: the SENTINEL WRITER. bash 3.2 + python3, pure code.
#
# A throwaway process that plays "another window writing into the notes folder" — but ONLY into the scratch
# stand-in, never the real notes folder. It runs OUTSIDE the write guard (bite.sh starts it beside the runs), so
# every one of its writes must come out of a guarded run as SEAM-AMBIENT, never SEAM-LEAK, never SEAM-DENIED.
#
#   sentinel.sh run [--seed N] [--for SECS]     loop until killed (or SECS elapsed): every 1–3 s (uniform, seeded)
#                                               create, edit or delete one file in the stand-in; log each write
#   sentinel.sh selftest                        last line 'SELFTEST sentinel OK'
#
# Stand-in : ${SEAM_STANDIN:-~/lifehack-scratch/skill-tester-rig/notes-standin}   (must resolve inside the canonical
#            scratch ~/lifehack-scratch/skill-tester-rig and never on a cloud drive; anything else is refused, exit 2)
# Log      : ${SENTINEL_LOG:-~/lifehack-scratch/skill-tester-rig/sentinel.log}  one line per write, appended and
#            flushed AFTER the write landed:  <epoch.ms>\t<ADDED|CHANGED|REMOVED>\t<absolute realpath>
#            (the op names are seam.sh's, so a SEAM-AMBIENT <op> <path> line can be matched to it)
# Determinism: the op sequence, file names, contents and sleeps are a pure function of --seed (default 1729).
# The sentinel only ever touches files named sentinel-NN.md inside the stand-in (at most 8 at once).
set -u
CANON="$HOME/lifehack-scratch/skill-tester-rig"
STANDIN="${SEAM_STANDIN:-$CANON/notes-standin}"
LOG="${SENTINEL_LOG:-$CANON/sentinel.log}"

cmd_run() {
  local seed=1729 dur=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --seed) seed="${2:-}"; shift 2 ;;
      --for) dur="${2:-}"; shift 2 ;;
      *) echo "sentinel: unknown argument '$1'" >&2; exit 2 ;;
    esac
  done
  case "$seed$dur" in ''|*[!0-9]*) echo "sentinel: --seed/--for must be integers" >&2; exit 2 ;; esac
  exec python3 -I -B - "$STANDIN" "$LOG" "$CANON" "$seed" "$dur" <<'PY'
import os, random, signal, sys, time
standin, log, canon, seed, dur = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
canon_r = os.path.realpath(canon)
st = os.path.realpath(standin)
if not (st + "/").startswith(canon_r + "/") or st == canon_r or "CloudStorage" in st or "Google" in st:
    sys.stderr.write("sentinel: REFUSED stand-in %s (must be inside %s, never a cloud drive)\n" % (st, canon_r))
    sys.exit(2)
os.makedirs(st, exist_ok=True)
r = random.Random(seed)
stop = [False]
signal.signal(signal.SIGTERM, lambda *a: stop.__setitem__(0, True))
signal.signal(signal.SIGINT, lambda *a: stop.__setitem__(0, True))
lf = open(log, "a", buffering=1)
def note(op, p):
    lf.write("%.3f\t%s\t%s\n" % (time.time(), op, p)); lf.flush(); os.fsync(lf.fileno())
t_end = time.time() + dur if dur else None
n = 0
while not stop[0] and (t_end is None or time.time() < t_end):  # pacing-loop: the sentinel's write cadence (what it simulates)
    nap = r.uniform(1.0, 3.0)
    t = time.time() + nap
    while not stop[0] and time.time() < t:  # pacing-loop: one nap, checked for SIGTERM every 0.1 s
        time.sleep(min(0.1, max(0.0, t - time.time())))  # pacing: the write interval; controls handshake on the LOG
    if stop[0]:
        break
    have = sorted(f for f in os.listdir(st) if f.startswith("sentinel-") and f.endswith(".md"))
    roll = r.random()
    if not have or (roll < 0.45 and len(have) < 8):
        free = [i for i in range(100) if "sentinel-%02d.md" % i not in have]
        p = os.path.join(st, "sentinel-%02d.md" % r.choice(free))
        with open(p, "w") as f:
            f.write("sentinel seed=%d write=%d %s\n" % (seed, n, r.getrandbits(64)))
        note("ADDED", p)
    elif roll < 0.80:
        p = os.path.join(st, r.choice(have))
        with open(p, "a") as f:
            f.write("edit %d %s\n" % (n, r.getrandbits(64)))
        note("CHANGED", p)
    else:
        p = os.path.join(st, r.choice(have))
        os.unlink(p)
        note("REMOVED", p)
    n += 1
lf.close()
PY
}

cmd_selftest() {
  local T rc bad=""
  T="$CANON/selftest/sentinel.$$"; mkdir -p "$T/standin"
  # 1. determinism: two runs, same seed, same op/name sequence
  SEAM_STANDIN="$T/standin" SENTINEL_LOG="$T/a.log" bash "$0" run --seed 7 --for 7 2>/dev/null
  rm -rf "$T/standin"; mkdir -p "$T/standin"
  SEAM_STANDIN="$T/standin" SENTINEL_LOG="$T/b.log" bash "$0" run --seed 7 --for 7 2>/dev/null
  [ -s "$T/a.log" ] || bad="$bad no-writes"
  [ "$(cut -f2- "$T/a.log" | head -2)" = "$(cut -f2- "$T/b.log" | head -2)" ] || bad="$bad not-deterministic"
  # 2. every logged path is inside the stand-in and the op set is seam's
  awk -F'\t' -v d="$(cd "$T/standin" && pwd -P)/" 'index($3, d)!=1 || $2!~/^(ADDED|CHANGED|REMOVED)$/{x=1} END{exit x}' "$T/b.log" || bad="$bad bad-log-line"
  # 3. cadence 1–3 s: at most 7 writes in 7 s, at least 2
  n=$(wc -l < "$T/b.log" | tr -d ' '); { [ "$n" -ge 2 ] && [ "$n" -le 7 ]; } || bad="$bad cadence-$n"
  # 4. refusals: a stand-in outside the canonical scratch, and the real Drive, are refused (exit 2)
  SEAM_STANDIN="$HOME/lifehack-scratch/not-the-rig" SENTINEL_LOG="$T/c.log" bash "$0" run --for 1 2>/dev/null; rc=$?
  [ "$rc" = 2 ] || bad="$bad outside-not-refused($rc)"
  rmdir "$HOME/lifehack-scratch/not-the-rig" 2>/dev/null
  rm -rf "$T"
  if [ -z "$bad" ]; then echo "SELFTEST sentinel OK"; return 0; fi
  echo "SELFTEST sentinel FAILED:$bad"; return 1
}

case "${1:-}" in
  run) shift; cmd_run "$@" ;;
  selftest) cmd_selftest ;;
  *) echo "usage: sentinel.sh run [--seed N] [--for SECS] | selftest" >&2; exit 2 ;;
esac
