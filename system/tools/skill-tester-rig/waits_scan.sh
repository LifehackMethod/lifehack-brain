#!/bin/bash
# waits_scan.sh — card TR1.8 of the skill-tester-rig: no test may pass by giving up. bash 3.2 + python3, pure code.
# ENTRY POINT (run by hand, and by selftest-all.sh --waits).
#
#   waits_scan.sh [DIR]          scan every *.sh / *.py under DIR (default: this rig folder). Last line exactly:
#                                  WAITS-SCAN OK files=<n> sleeps=<s> pacing=<p> handshake=<h> loops=<l>
#                                or WAITS-SCAN REFUSED <k> (one `REFUSED <file>:<line> <rule>: <code>` line above each)
#   waits_scan.sh --selftest     watched failing (ruling 12): plants, in a temp COPY of the rig, a bare sleep, a poll
#                                loop with no WAIT-TIMEOUT path (k1's old silent give-up, verbatim shape), a pacing tag
#                                used to dodge a poll loop, and a python time.sleep; the scan must refuse each, by
#                                file, and pass the clean copy. Last line 'SELFTEST waits-scan OK'.
#
# RULES (comments are stripped before matching; a heredoc body is scanned like code, because it runs as code):
#   R1 a `sleep` (shell) or `time.sleep(` (python) is allowed only if
#        (a) it is the poll interval inside wait.lib.sh's wait_until (the recognised handshake helper), or
#        (b) its line carries `# pacing: <why>` (pacing only: the sentinel's cadence, a watchdog's own timer, a hang
#            stand-in, a hold's deadline) — and it is NOT inside a loop (rule R2 decides loops), or
#        (c) it sits inside a loop whose body has a `WAIT-TIMEOUT` failure path (an inline handshake loop).
#   R2 a loop (shell while/until … done; python while + its indented block) whose body sleeps is a POLL LOOP and must
#      contain `WAIT-TIMEOUT` in its body, unless its header line carries `# pacing-loop: <why>` (a loop that only
#      paces, e.g. the sentinel's write cadence). A pacing tag on a sleep inside a poll loop does NOT excuse the loop.
#   Every pacing / pacing-loop exception is printed, so a reader sees each one.
# Writes nothing except, for --selftest, a temp copy under ~/lifehack-scratch/skill-tester-rig/selftest-waits/.
set -u
export PYTHONDONTWRITEBYTECODE=1
RIG="$(cd "$(dirname "$0")" && pwd)"

scan() {
  python3 -I -B - "$1" <<'PY'
import os, re, sys
root = sys.argv[1]
SLEEP_SH = re.compile(r"(^|[\s;&|({`'\"])sleep(\s|$)")
SLEEP_PY = re.compile(r"\btime\.sleep\s*\(")
PACE = re.compile(r"#\s*pacing:\s*\S")
PACE_LOOP = re.compile(r"#\s*pacing-loop:\s*\S")

def strip_comment(line, py):
    """code part of a line: drop a trailing # comment that is outside quotes (naive, good enough for this rig)."""
    q = None
    for i, ch in enumerate(line):
        if q:
            if ch == q and line[i - 1] != "\\":
                q = None
        elif ch in "'\"":
            q = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t;"):
            if not py and i > 0 and line[i - 1] == "$":
                continue
            return line[:i]
    return line

files, refused, sleeps, pacing, hs, loops = 0, [], 0, [], 0, 0
for d, dirs, fs in os.walk(root):
    dirs[:] = sorted(x for x in dirs if x not in ("__pycache__", ".git"))
    for f in sorted(fs):
        if not (f.endswith(".sh") or f.endswith(".py")):
            continue
        p = os.path.join(d, f); rel = os.path.relpath(p, root)
        if rel == "waits_scan.sh":      # the scanner itself: its patterns and planted fixtures are data, not waits
            print("EXEMPT waits_scan.sh (the scanner's own patterns and planted fixtures; it never waits)"); continue
        py = f.endswith(".py")
        try:
            raw = open(p, encoding="utf-8", errors="replace").read().split("\n")
        except OSError as e:
            refused.append("%s:0 unreadable: %s" % (rel, e)); continue
        files += 1
        code = [strip_comment(l, py) for l in raw]
        # python heredocs inside .sh files and .py files both use python rules for time.sleep; shell rules for sleep
        is_sleep = [bool(SLEEP_PY.search(c)) or (not py and bool(SLEEP_SH.search(c))) for c in code]
        # loops: (start, end) inclusive line ranges
        rng = []
        for i, c in enumerate(code):
            s = c.strip()
            if re.match(r"while\b.*:\s*$", s) and (py or "python" in "".join(code[max(0, i - 40):i])):
                ind = len(c) - len(c.lstrip())
                j = i + 1
                while j < len(code) and (not code[j].strip() or len(code[j]) - len(code[j].lstrip()) > ind):
                    j += 1
                rng.append((i, j - 1))
            elif not py and re.search(r"(^|[\s;&|(])(while|until)\s", re.sub(r"'[^']*'|\"[^\"]*\"", "", c)):
                depth, seen, j = 0, False, i
                while j < len(code):
                    t = re.sub(r"'[^']*'|\"[^\"]*\"", "", code[j])
                    for w in re.findall(r"(?<![\w-])(do|done)(?![\w-])", t):
                        if w == "do": depth += 1; seen = True
                        else: depth -= 1
                    if seen and depth <= 0: break
                    j += 1
                    if j - i > 200: break
                rng.append((i, min(j, len(code) - 1)))
        in_wait_lib = rel == "wait.lib.sh"
        for (a, b) in rng:
            body = range(a, b + 1)
            if not any(is_sleep[k] for k in body):
                continue
            loops += 1
            if PACE_LOOP.search(raw[a]):
                pacing.append("%s:%d pacing-loop: %s" % (rel, a + 1, raw[a].split("pacing-loop:", 1)[1].strip()))
            elif in_wait_lib or any("WAIT-TIMEOUT" in raw[k] for k in body):
                pass
            else:
                refused.append("%s:%d R2 poll loop with no WAIT-TIMEOUT failure path: %s" % (rel, a + 1, raw[a].strip()[:120]))
        for i, s in enumerate(is_sleep):
            if not s:
                continue
            sleeps += 1
            inside = [(a, b) for (a, b) in rng if a <= i <= b]
            if in_wait_lib and inside:
                hs += 1; continue
            if inside:
                if any(PACE_LOOP.search(raw[a]) for (a, b) in inside) or all(any("WAIT-TIMEOUT" in raw[k] for k in range(a, b + 1)) for (a, b) in inside):
                    if PACE.search(raw[i]):
                        pacing.append("%s:%d pacing: %s" % (rel, i + 1, raw[i].split("pacing:", 1)[1].strip()))
                    else:
                        hs += 1
                    continue
                refused.append("%s:%d R1 sleep inside a poll loop with no WAIT-TIMEOUT path: %s" % (rel, i + 1, raw[i].strip()[:120]))
                continue
            if PACE.search(raw[i]):
                pacing.append("%s:%d pacing: %s" % (rel, i + 1, raw[i].split("pacing:", 1)[1].strip()))
                continue
            refused.append("%s:%d R1 bare sleep (no handshake, no '# pacing: <why>'): %s" % (rel, i + 1, raw[i].strip()[:120]))
for x in pacing:
    print("PACING " + x)
for x in refused:
    print("REFUSED " + x)
if refused:
    print("WAITS-SCAN REFUSED %d" % len(refused)); sys.exit(1)
print("WAITS-SCAN OK files=%d sleeps=%d pacing=%d handshake=%d loops=%d" % (files, sleeps, len(pacing), hs, loops))
PY
}

selftest() {
  local T bad="" out
  T="$HOME/lifehack-scratch/skill-tester-rig/selftest-waits/$(date +%s)-$$"
  mkdir -p "$T" || { echo "SELFTEST waits-scan FAILED: cannot create $T"; return 1; }
  cp -Rp "$RIG" "$T/rig" && find "$T/rig" -name __pycache__ -prune -exec rm -rf {} +
  out="$(scan "$T/rig")" || bad="$bad clean-copy-refused"
  printf '%s\n' "$out" | tail -1 | grep -q '^WAITS-SCAN OK ' || bad="$bad clean-copy-not-OK"
  plant() {  # plant <name> <expected-rule> : write $T/rig/<name> from stdin, scan, require a refusal naming it
    cat > "$T/rig/$1"
    out="$(scan "$T/rig")"
    if printf '%s\n' "$out" | grep -q "^REFUSED $1:[0-9]* $2 " && printf '%s\n' "$out" | tail -1 | grep -q '^WAITS-SCAN REFUSED '; then
      echo "  ok   planted $1 -> refused ($2)"
    else echo "  FAIL planted $1 was not refused by $2"; printf '%s\n' "$out" | sed 's/^/       | /'; bad="$bad $1"; fi
    rm -f "$T/rig/$1"
  }
  printf '#!/bin/bash\necho start\nsleep 2\necho done\n' | plant planted-bare-sleep.sh R1
  printf '#!/bin/bash\ni=0; while [ $i -lt 200 ] && [ ! -f /x/ready ]; do sleep 0.1; i=$((i+1)); done\necho carry on\n' | plant planted-silent-giveup.sh R2
  printf '#!/bin/bash\nwhile [ ! -f /x/ready ]; do\n  sleep 0.1   # pacing: a dodge\ndone\n' | plant planted-pacing-dodge.sh R2
  printf 'import time\ntime.sleep(1)\n' | plant planted_sleep.py R1
  rm -rf "$T"
  if [ -z "$bad" ]; then echo "SELFTEST waits-scan OK"; return 0; fi
  echo "SELFTEST waits-scan FAILED:$bad"; return 1
}

case "${1:-}" in
  --selftest) selftest ;;
  -h|--help) sed -n '2,24p' "$0" ;;
  *) scan "${1:-$RIG}" ;;
esac
