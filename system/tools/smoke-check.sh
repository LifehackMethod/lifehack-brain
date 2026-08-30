#!/usr/bin/env bash
# smoke-check.sh — the cheapest question anyone can ask this repo: does it still start?
#
# WHY THIS EXISTS. The aggregate test runner (run-all-tests.sh) proves that the code
# which HAS tests behaves. This proves something dumber and, on the evidence, more
# urgent: that every tool can be INVOKED at all, and every hook can EXECUTE at all AND
# actually PARSE. Neither is covered by a test file, and both have been broken in this
# repo for weeks without anything noticing — a tool that crashes on import has no failing test, it has
# no test, and a hook missing its execute bit is a guard that silently protects nothing.
#
# THREE CHECKS, DELIBERATELY BORING:
#   1. every tool in system/tools/ answers --help without crashing
#   2. every hook in system/hooks/ is executable
#   3. every hook in system/hooks/ actually PARSES (bash -n / ast.parse) — the execute
#      bit says nothing about whether the interpreter can even read the file. A hook
#      with a syntax error is still executable, so check #2 alone passed GREEN on
#      2026-08-24 while guard_hook_sop_read.sh (unclosed if/else, the PreToolUse hook
#      for every Bash call) took the whole machine down. Check #3 exists to catch
#      exactly that shape again, and never folds "could not check" into "passed".
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
#         bash system/tools/smoke-check.sh <repo-root>   # point at a fixture repo for
#                                                          # testing this script itself —
#                                                          # never point it at a live repo
#                                                          # to "test" a real hook change.
#
# ── EXIT-CODE CONTRACT — four states, never folded into each other ──────────────────
#   0  PASS               every tool answered, every hook is executable and parses,
#                          nothing timed out, nothing was left unevaluated.
#   1  FAIL                a real crash, a real parse failure, or a genuinely broken
#                          hook. Checked first: a real failure always wins the verdict,
#                          even if something else also timed out or could not be
#                          checked in the same run.
#   3  TIMED-OUT-ONLY      no real failure, but at least one probe hit the ${TIMEOUT_S}s
#                          cap. THIS IS ITS OWN STATE, not folded into pass and not
#                          folded into fail. A probe that ran out of clock told you
#                          NOTHING about whether the tool underneath is broken —
#                          treating it as a fail invents evidence, and treating it as a
#                          pass (or silently ignoring it) discards a probe that never
#                          finished. Measured 2026-08-24: this exact boundary flipped
#                          between PASS and FAIL on sub-second timing margins across
#                          two machines and one machine under load — the verdict was
#                          non-deterministic, which is a worse failure than either
#                          fixed outcome. Mirrors NOCHECK's shape below, one line up
#                          the severity ladder because a timeout, unlike a skip, is at
#                          least suspicious.
#   2  NOCHECK-ONLY        no real failure, no timeout, but a hook's syntax could not
#                          be evaluated at all (unreadable file, unknown extension).
#                          Also never counted as a pass.
# If more than one non-PASS condition holds in the same run, FAIL > TIMED-OUT > NOCHECK
# — the exit code always reports the most serious thing that happened.
PY="${PY:-/usr/bin/python3}"   # PINNED 2026-08-28: bare python3 = Homebrew 3.14 (no third-party pkgs)
set -u

REPO="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
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

PASS=0; FAIL=0; NOHELP=0; UNSAFE=0; NOCHECK=0; TIMEDOUT=0
FAILED=""
NOCHECKED=""
TIMEDOUT_LIST=""

# ── check_script_syntax — mirrors install-guard-registrations.py's contract exactly
# (same function name/shape, same three-state return) so this repo has ONE dialect for
# "does this script parse", not two. .sh -> `bash -n` (parse only, never execute).
# .py -> `ast.parse` (parse only, never execute). Anything else -> an explicit
# could-not-check, never silently folded into "ok" — a script that was not checked is
# not a script that passed.
#
# Returns via globals SYNTAX_STATUS (ok|fail|unknown) and SYNTAX_DETAIL, because bash
# has no real return-a-tuple. Caller reads them immediately after calling.
check_script_syntax() {
  local path="$1" ext="${1##*.}"
  SYNTAX_STATUS=""; SYNTAX_DETAIL=""

  if [ ! -r "$path" ]; then
    SYNTAX_STATUS="unknown"; SYNTAX_DETAIL="could not read $path: permission denied"
    return
  fi

  case "$ext" in
    sh)
      local out rc
      out="$(bash -n "$path" 2>&1)"; rc=$?
      if [ "$rc" -eq 0 ]; then
        SYNTAX_STATUS="ok"
      else
        SYNTAX_STATUS="fail"
        SYNTAX_DETAIL="$(printf '%s' "$out" | tail -1)"
        [ -n "$SYNTAX_DETAIL" ] || SYNTAX_DETAIL="bash -n exited $rc"
      fi
      ;;
    py)
      local out rc
      out="$("$PY" -c 'import ast,sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        ast.parse(fh.read(), filename=sys.argv[1])
except SyntaxError as exc:
    bad_line = (exc.text or "").strip()
    print(f"{exc.msg} at {sys.argv[1]}:{exc.lineno}: {bad_line}")
    sys.exit(1)
except (ValueError, RecursionError) as exc:
    print(f"could not parse {sys.argv[1]}: {exc}")
    sys.exit(2)
' "$path" 2>&1)"; rc=$?
      if [ "$rc" -eq 0 ]; then
        SYNTAX_STATUS="ok"
      elif [ "$rc" -eq 2 ]; then
        SYNTAX_STATUS="unknown"; SYNTAX_DETAIL="$out"
      else
        SYNTAX_STATUS="fail"; SYNTAX_DETAIL="$out"
      fi
      ;;
    *)
      SYNTAX_STATUS="unknown"
      SYNTAX_DETAIL="no syntax checker for extension .$ext on $path"
      ;;
  esac
}

# ⛔ TOOLS THAT DO NOT MERELY MISREAD --help AS A FILENAME (the NOHELP case below) BUT
# ACTUALLY RUN THEIR REAL WORK ON IT — never probe these with a live invocation.
#   pulse.sh: `MODE="${1:-run}"` treats ANY unrecognized first arg (including "--help")
#     as *not* "--status", so every guard below reads "not in status mode" and the RUN
#     path dispatches real scheduled jobs. Measured: this silently bumped the operator's
#     real _pulse-state.json timestamps before the sandbox root was pinned everywhere
#     it needed to be, and even sandboxed it walks the full job manifest until the
#     15s cap kills it mid-job — the TIMEOUT this loop would otherwise report is real,
#     not idle, work being cut off, and safe only because LIFEHACK_ROOT + the gws stub
#     are already pinned above.
#   system/tools/*-run.sh (the whole family): these are pulse-config.md's scheduled-job
#     wrappers — bash "$LIFEHACK_CODE_ROOT/system/tools/<name>-run.sh" is the ONLY call
#     shape pulse.sh ever makes, so none of them was ever given argument parsing, let
#     alone a --help convention. Every one checked runs its real body unconditionally on
#     ANY invocation. Measured while building this sandboxing: `archivist-audit-run.sh
#     --help`, run through this very probe, launched a real `claude -p ... --dangerously-
#     skip-permissions` subprocess — safe here only because it inherited the pinned
#     LIFEHACK_ROOT sandbox above, not because the tool itself checked anything. Treat
#     the whole *-run.sh family as job wrappers, never as probeable CLIs, until each one
#     is given its own --help/--status guard (a separate, larger fix, not done here).
#   gws-reauth.sh: no --help handling at all (main body runs unconditionally on any
#     invocation). It nohup's `gws auth login --full`, prints/writes a real consent URL,
#     then runs a fixed ~30s polling loop waiting for that URL to be consumed — a loop
#     the stub `gws` on PATH can never satisfy, so every probe would burn the full
#     ${TIMEOUT_S}s cap waiting on something that structurally cannot happen here.
#   test_architecture_reachability_run.py: not a CLI tool at all but a test module whose
#     own docstring documents a ~90s reachability walk and which sets its own 180s
#     subprocess timeout internally — `main()` ignores argv entirely, so `--help` runs
#     the full suite exactly like a bare invocation. Never built to fit inside a 15s
#     sweep; belongs in run-all-tests.sh's slower lane, not here.
#   verify-hooks.sh: no --help handling — it prints a note that it takes no positional
#     arg ("Ignoring: --help") and then runs its FULL guard fire-test suite over
#     organism/label_manifest.yaml unconditionally. Measured 2026-08-24: ~21s wall time,
#     already over this file's own ${TIMEOUT_S}s cap, so it is not a probe that
#     sometimes clears the cap under load — it structurally cannot fit inside it. Same
#     shape as the *-run.sh family above (no arg parsing, runs real work on any
#     invocation), added explicitly rather than by glob because its name does not match
#     the *-run.sh pattern.
UNSAFE_TO_PROBE="pulse.sh gws-reauth.sh test_architecture_reachability_run.py verify-hooks.sh"

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

  unsafe_hit=0
  case " $UNSAFE_TO_PROBE " in
    *" $name "*) unsafe_hit=1 ;;
  esac
  # *-run.sh, at any depth: pulse-config.md's scheduled-job wrappers, never given a
  # --help/--status guard (see UNSAFE_TO_PROBE comment above) — glob-matched, not
  # hand-listed, so a newly ported wrapper is unsafe by default until proven otherwise.
  case "$name" in
    *-run.sh) unsafe_hit=1 ;;
  esac
  if [ "$unsafe_hit" -eq 1 ]; then
    UNSAFE=$((UNSAFE + 1))
    echo "  · $name — SKIPPED: --help is not safe to probe (runs real work instead of answering it; see UNSAFE_TO_PROBE above)"
    continue
  fi

  case "$f" in
    *.py) out="$(run_bounded "$PY" "$f" --help)"; rc=$? ;;
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
    # ⭐ ITS OWN STATE — see the exit-code contract at the top of this file. A probe that
    # hit the wall clock proved NOTHING about whether the tool underneath is broken:
    # folding it into FAIL invents evidence of a crash that was never observed; folding
    # it into PASS (or silently dropping it) discards a probe that never finished. Both
    # were tried by an earlier draft of this gate and both were wrong — this is the
    # timeout-equivalent of UNSAFE_TO_PROBE and NOCHECK below: counted, named, never
    # silently absorbed into a state it did not earn.
    echo "  ⏱ $name — TIMED OUT after ${TIMEOUT_S}s (waiting on input or the network? or just slow under load — this run's timing is not evidence either way)"
    TIMEDOUT=$((TIMEDOUT + 1)); TIMEDOUT_LIST="$TIMEDOUT_LIST $name"
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
        *.py) sout="$(run_bounded "$PY" "$f" "$sub" --help)" ;;
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

# ── 2. every hook is executable, AND every hook actually PARSES ─────────────────
# ⛔ 2026-08-24: `guard_hook_sop_read.sh` (the PreToolUse hook for EVERY Bash call on
# this machine) shipped with an unclosed if/else. `[ -x ]` was true the whole time —
# the execute bit says nothing about whether bash can PARSE the file — so this loop
# used to print PASS while a hook that could not even be sourced sat live in
# .claude/settings.json. THE EXECUTE-BIT CHECK BELOW IS KEPT; IT CATCHES A DIFFERENT
# FAILURE (mode bits) THAN THE PARSE CHECK DOES (syntax). Neither replaces the other.
echo
echo "── hooks: system/hooks/*.{sh,py} — executable bit AND syntax"
for h in "$REPO"/system/hooks/*.sh "$REPO"/system/hooks/*.py; do
  [ -e "$h" ] || continue
  name="$(basename "$h")"

  if [ -x "$h" ]; then
    PASS=$((PASS + 1))
  else
    mode="$(git -C "$REPO" ls-files -s "system/hooks/$name" 2>/dev/null | awk '{print $1}')"
    echo "  ✘ $name — NOT EXECUTABLE (git mode ${mode:-unknown}); a guard that cannot run protects nothing"
    FAIL=$((FAIL + 1)); FAILED="$FAILED $name(mode)"
  fi

  check_script_syntax "$h"
  case "$SYNTAX_STATUS" in
    ok)
      PASS=$((PASS + 1))
      ;;
    fail)
      echo "  ✘ $name — DOES NOT PARSE: $SYNTAX_DETAIL"
      FAIL=$((FAIL + 1)); FAILED="$FAILED $name(parse)"
      ;;
    unknown)
      echo "  · $name — COULD NOT CHECK SYNTAX: $SYNTAX_DETAIL"
      NOCHECK=$((NOCHECK + 1)); NOCHECKED="$NOCHECKED $name"
      ;;
  esac
done

echo
echo "─────────────────────────────────────"
echo "SMOKE: $PASS ok · $FAIL broken · $TIMEDOUT timed out (own state — not counted as broken, NOT counted as passed) · $NOHELP without a --help convention (not counted as broken) · $UNSAFE skipped as unsafe to probe (not counted as broken) · $NOCHECK hook(s) could not be syntax-checked (not counted as broken, NOT counted as passed)"
# See the exit-code contract at the top of this file: FAIL > TIMED-OUT > NOCHECK > PASS.
if [ "$FAIL" -gt 0 ]; then
  echo "SMOKE: FAIL —$FAILED"
  exit 1
fi
if [ "$TIMEDOUT" -gt 0 ]; then
  echo "SMOKE: TIMED-OUT — no real failures found, but $TIMEDOUT probe(s) hit the ${TIMEOUT_S}s cap and never reported:$TIMEDOUT_LIST — this is NOT a pass. Re-run to see if it clears; a probe that times out on every run is a real finding (raise it, don't silence it)."
  exit 3
fi
if [ "$NOCHECK" -gt 0 ]; then
  echo "SMOKE: COULD-NOT-EVALUATE — no failures found, but $NOCHECK hook(s) could not be syntax-checked:$NOCHECKED — this is NOT a pass."
  exit 2
fi
echo "SMOKE: PASS — every tool starts, every hook has its execute bit set, and every hook actually PARSES (bash -n / ast.parse — not merely executable, not merely present), and nothing timed out."
exit 0
