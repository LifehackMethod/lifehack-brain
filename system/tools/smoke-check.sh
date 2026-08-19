#!/usr/bin/env bash
# smoke-check.sh — the cheapest question anyone can ask this repo: does it still start?
#
# WHY THIS EXISTS. The aggregate test runner (run-all-tests.sh) proves that the code
# which HAS tests behaves. This proves something dumber and, on the evidence, more
# urgent: that every tool can be INVOKED at all, and every hook can EXECUTE at all.
# Neither is covered by a test file, and both have been broken in this repo for weeks
# without anything noticing — a tool that crashes on import has no failing test, it has
# no test, and a hook missing its execute bit is a guard that silently protects nothing.
#
# TWO CHECKS, DELIBERATELY BORING:
#   1. every tool in system/tools/ answers --help without crashing
#   2. every hook in system/hooks/ is executable
#
# ⛔ IT IS SUPPOSED TO FAIL ON ITS FIRST RUN. A green first run means it is not looking.
#
# ── SAFETY: WHY RUNNING 38 UNKNOWN TOOLS HERE IS NOT RECKLESS ────────────────────
# Some tools in this folder reach the real world — planning-*.py and safe_tasks.py shell out
# to `gws`; safe_fetch.py and render_shot.sh open sockets. A previous helper running
# repo tooling with no data root pinned made LIVE Gmail and Google Tasks API calls and
# wrote into the operator's real Drive. The resolver was not broken; nothing had told it
# where to point. So this script does not merely hope --help exits early:
#   · LIFEHACK_ROOT is pinned INLINE on every invocation, never exported and trusted,
#     so a forgotten subshell cannot inherit its way back to the real brain root.
#   · a stub `gws` is placed FIRST on PATH, so a tool that ignores --help and runs
#     anyway cannot reach Google. The block is structural, not a guess about argparse.
#   · every invocation is wrapped in a hard timeout, so a tool that waits on input or
#     on the network cannot hang the sweep.
# Sandboxing the data root does NOT sandbox the network — the timeout is what bounds
# that, and it is why the stub exists rather than a comment saying "--help is safe".
#
# Usage:  bash system/tools/smoke-check.sh
set -u

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SCRATCH="${TMPDIR:-/tmp}/lifehack-smoke-check"
SANDBOX="$SCRATCH/brain-root"
STUB_BIN="$SCRATCH/stub-bin"
TIMEOUT_S=15

rm -rf "$SCRATCH"
mkdir -p "$SANDBOX" "$STUB_BIN"

# The stub. Anything that tries to reach Google gets this instead.
cat > "$STUB_BIN/gws" <<'STUB'
#!/bin/bash
# smoke-check stub — stands in for the real gws so no live API call can occur.
echo '{}'
exit 0
STUB
chmod 755 "$STUB_BIN/gws"

# Portable hard timeout. macOS ships no coreutils `timeout`; perl's alarm is always here.
#
# ⛔ `< /dev/null` IS LOAD-BEARING, NOT TIDINESS. Without it every tool inherits the
# sweep's own stdin -- which is the file list the loop is reading -- so the first tool
# that reads stdin EATS the remaining filenames and the sweep silently stops early.
# Measured while building this: 73 files on disk, 70 checks reported, and
# plan_git_check.py (a known crasher) scored GREEN because its line had been consumed.
# A sweep that quietly shrinks its own denominator is the precise failure this gate
# exists to catch, so it must not commit it.
run_bounded() {
  PATH="$STUB_BIN:$PATH" LIFEHACK_ROOT="$SANDBOX" \
    perl -e 'alarm shift; exec @ARGV or exit 127' "$TIMEOUT_S" "$@" 2>&1 < /dev/null
}

PASS=0; FAIL=0; NOHELP=0
FAILED=""

echo "═══ smoke check — can this repo still start? ═══"
echo "    sandbox root: $SANDBOX   (stub gws first on PATH; ${TIMEOUT_S}s cap per tool)"
echo

# ── 1. every tool answers --help ────────────────────────────────────────────────
# ⚠ RECURSES. The first draft globbed system/tools/*.py only and MISSED
# cowork-ingest/filer_review.py, a known-crashing tool one directory down. A sweep whose
# denominator is shallower than the territory reports a green it did not earn.
echo "── tools: system/tools/**/*.{py,sh} --help"
TOOLS_SEEN=0
while IFS= read -r f <&3; do
  TOOLS_SEEN=$((TOOLS_SEEN + 1))
  name="${f#"$REPO"/system/tools/}"
  [ "$name" = "smoke-check.sh" ] && continue   # do not recurse into ourselves

  case "$f" in
    *.py) out="$(run_bounded python3 "$f" --help)"; rc=$? ;;
    *)    out="$(run_bounded bash    "$f" --help)"; rc=$? ;;
  esac

  # ⛔ WHAT COUNTS AS A CRASH -- and why this is narrower than it first was.
  # The first draft matched any 'Error'/'No such file' string and flagged four safe_*
  # tools that were behaving correctly: they take a FILENAME, so they read '--help' as a
  # missing file and print one clean handled line at rc 0. That is not a crash, and
  # calling it one would make this gate exactly the dishonest checker it exists to catch.
  # A real crash is an UNHANDLED fault: the interpreter prints a traceback, or cannot
  # open the file at all. Match that signature and nothing else.
  if printf '%s' "$out" | grep -qE "Traceback \(most recent call last\)|can't open file"; then
    first="$(printf '%s\n' "$out" | grep -E '^[A-Za-z_.]*(Error|Exception)' | tail -1 | cut -c1-96)"
    [ -n "$first" ] || first="$(printf '%s\n' "$out" | tail -1 | cut -c1-96)"
    echo "  ✘ $name — $first"
    FAIL=$((FAIL + 1)); FAILED="$FAILED $name"
  elif [ "$rc" -eq 142 ] || [ "$rc" -eq 124 ]; then
    echo "  ✘ $name — TIMED OUT after ${TIMEOUT_S}s (waiting on input or the network?)"
    FAIL=$((FAIL + 1)); FAILED="$FAILED $name(timeout)"
  elif printf '%s' "$out" | grep -qE "Cannot access file --help|No such file or directory: '--help'"; then
    # Not a fault: the tool has no --help convention and read the flag as a path.
    # Reported, never counted as broken -- a real gap, but a different and smaller one.
    NOHELP=$((NOHELP + 1))
    echo "  · $name — no --help convention (treats it as a filename); not a crash"
    PASS=$((PASS + 1))
  else
    PASS=$((PASS + 1))

    # ── SUBCOMMANDS. A tool can answer bare --help perfectly and still crash on every
    # subcommand it has. Measured here: filer_review.py --help is clean, while
    # `filer_review.py show --help` dies with ValueError: unsupported format character
    # 'p' -- an unescaped % in a help string. Checking only the top level would have
    # scored that tool GREEN while every real invocation of it fails.
    # argparse advertises its subcommands as a {a,b,c} choices group; read them back
    # out of the help text and probe each one.
    # ⚠ The comma group is OPTIONAL. Requiring it (…)+ missed `{show}` -- a tool with
    # exactly ONE subcommand -- which is the very tool this check was added for.
    subs="$(printf '%s' "$out" | grep -oE '\{[a-z0-9_-]+(,[a-z0-9_-]+)*\}' | head -1 | tr -d '{}' | tr ',' ' ')"
    for sub in $subs; do
      case "$f" in
        *.py) sout="$(run_bounded python3 "$f" "$sub" --help)" ;;
        *)    sout="$(run_bounded bash    "$f" "$sub" --help)" ;;
      esac
      if printf '%s' "$sout" | grep -qE "Traceback \(most recent call last\)|can't open file"; then
        sfirst="$(printf '%s\n' "$sout" | grep -E '^[A-Za-z_.]*(Error|Exception)' | tail -1 | cut -c1-96)"
        echo "  ✘ $name $sub — $sfirst"
        FAIL=$((FAIL + 1)); FAILED="$FAILED $name:$sub"
      else
        PASS=$((PASS + 1))
      fi
    done
  fi
done 3<<EOF
$(find "$REPO/system/tools" -type f \( -name '*.py' -o -name '*.sh' \) | sort)
EOF

# The denominator, stated out loud. If these two disagree the sweep was truncated and
# every "ok" above is worthless -- so say so and fail, rather than reporting a green.
TOOLS_ON_DISK=$(find "$REPO/system/tools" -type f \( -name '*.py' -o -name '*.sh' \) | wc -l | tr -d ' ')
if [ "$TOOLS_SEEN" -ne "$TOOLS_ON_DISK" ]; then
  echo "  ✘ SWEEP TRUNCATED — $TOOLS_SEEN of $TOOLS_ON_DISK tools reached. Results above are NOT trustworthy."
  FAIL=$((FAIL + 1)); FAILED="$FAILED sweep-truncated"
else
  echo "  ($TOOLS_SEEN of $TOOLS_ON_DISK tools reached)"
fi

# ── 2. every hook is executable ─────────────────────────────────────────────────
echo
echo "── hooks: system/hooks/*.sh executable bit"
for h in "$REPO"/system/hooks/*.sh; do
  [ -e "$h" ] || continue
  name="$(basename "$h")"
  if [ -x "$h" ]; then
    PASS=$((PASS + 1))
  else
    mode="$(git -C "$REPO" ls-files -s "system/hooks/$name" 2>/dev/null | awk '{print $1}')"
    echo "  ✘ $name — NOT EXECUTABLE (git mode ${mode:-unknown}); a guard that cannot run protects nothing"
    FAIL=$((FAIL + 1)); FAILED="$FAILED $name(mode)"
  fi
done

echo
echo "─────────────────────────────────────"
echo "SMOKE: $PASS ok · $FAIL broken · $NOHELP without a --help convention (not counted as broken)"
if [ "$FAIL" -eq 0 ]; then
  echo "SMOKE: PASS — every tool starts and every hook can execute."
  exit 0
fi
echo "SMOKE: FAIL —$FAILED"
exit 1
