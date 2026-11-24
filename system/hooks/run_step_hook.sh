#!/bin/sh
# Registered 2026-11-24 through system/register/register.jsonl + generate.py (run pickup, spec G6).
# LHB fire-journal (B4.1): observes only; never alters this hook's decision/exit/stdout/stderr.
_lhb_src="$0"; case "$_lhb_src" in */*) _lhb_dir="${_lhb_src%/*}" ;; *) _lhb_dir=. ;; esac
if [ -r "$_lhb_dir/lib/journal.sh" ]; then . "$_lhb_dir/lib/journal.sh"; else lhb_journal_fire() { :; }; fi
trap 'lhb_journal_fire "$?" "run_step_hook.sh" "UserPromptSubmit" "" 2>/dev/null || true' EXIT
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: /next and /back are files, not commands — nothing ran behind them, so no runner skill could
#      move a talk step (spec run-pickup, id run-pickup-spec-2026-11-23). This hook is the MOVER:
#      when the PERSON types exactly /next or /back, it runs the step runner's person-turn, then
#      advance/back with that turn id, and prints the handover. One person turn moves at most one step.
# GUARDS: UserPromptSubmit, empty matcher (every prompt). Doors, in order: the sh prefilter only
#      proceeds when the raw stdin contains /next or /back; python then requires the prompt to be
#      EXACTLY /next or /back (trimmed), not_the_person false (peer messages and task
#      notifications start with <cross-session-message / <task-notification — ups_triggers.py),
#      and a run marker found from the payload cwd. "/next please" is not the command. A peer or a
#      notification never moves a run.
# REDIRECT: the runner's own refusals name the person's word ("only the person's typed /next moves
#      this step"); a failed step check says "not finished: <codes>" — the person types /next again.
# SIGNPOST: runner contract in system/parts/stage_runner.py header + RUNNER.md; the spec is the
#      run-pickup spec (G2). The AI-side rule lives in /next and /back's own text: no [RUN STEP]
#      line this turn means the mover did not run — tell the person.
# UPDATED: 2026-11-23 (Phase 4c fix pass: person.log for every person prompt,
#      mover.log written before person-turn, damaged-marker line, capped failure
#      output naming the stage prompt file, empty-payload line, journal.sh sourced
#      a tagged line for a payload missing prompt_id or cwd (phase 4e),
#      journal.sh sourced only when readable).
# FAIL_POSTURE: degrade-safe (never moves the run on a failure; always says what failed).
#      Every branch exits 0 (a prompt hook's non-zero exit is silenced, not surfaced);
#      every failure prints a [RUN STEP ...] tagged line. Plain stdout, never systemMessage.
# ─────────────────────────────────────────────────────────────────────────────
payload=`cat`
case "$payload" in
  "") printf '%s the mover got an empty payload; nothing ran\n' \
    '[RUN STEP — harness-injected, not user input]'
     exit 0 ;;
  *) ;;  # every prompt reaches the python door: the mover logs each person prompt (A3)
esac
DIR=`CDPATH= cd -- "$(dirname -- "$0")" && pwd`
PAYLOAD_FILE=`mktemp "${TMPDIR:-/tmp}/mover-payload.XXXXXX"`
printf '%s' "$payload" > "$PAYLOAD_FILE"
RESULT=`python3 - "$DIR" "$PAYLOAD_FILE" <<'PY'
import json, os, re, subprocess, sys, time
TAG = "[RUN STEP — harness-injected, not user input]"
hooks = sys.argv[1]
sys.path.insert(0, os.path.join(hooks, "lib"))
sys.path.insert(0, os.path.abspath(os.path.join(hooks, "..", "parts")))
from ups_triggers import not_the_person
try:
    with open(sys.argv[2], encoding="utf-8") as f:
        j = json.load(f)
except Exception:
    j = {}
prompt = j.get("prompt") if isinstance(j, dict) else None
pid = j.get("prompt_id"); cwd = j.get("cwd")
if not isinstance(pid, str) or not pid or not isinstance(cwd, str) or not cwd:
    print(TAG + " the payload had no prompt_id or no cwd; nothing ran; tell the person")
    sys.exit(0)
if not_the_person(prompt if isinstance(prompt, str) else ""):
    sys.exit(0)  # a peer message or a task notification is never the person
import stage_runner
try:
    found = stage_runner.find_run(cwd)  # reuse the runner's own marker walk, never a copy
except stage_runner.Damaged as e:
    print(TAG + " the run marker is damaged (%s); nothing ran; tell the person" % str(e)[:300])
    sys.exit(0)
if not found:
    sys.exit(0)  # no run here: silent
wd, run_dir = found
if not os.path.isabs(run_dir):
    run_dir = os.path.join(wd, run_dir)
# every person prompt is logged while a run is open (prompt_id and unix time, never the text)
try:
    with open(os.path.join(run_dir, "person.log"), "a", encoding="utf-8") as f:
        f.write("%s\t%d\n" % (pid, int(time.time())))
except OSError:
    pass
if not isinstance(prompt, str) or prompt.strip() not in ("/next", "/back"):
    sys.exit(0)  # the person's word, but not a step command: logged above, nothing moves
cmd = "back" if prompt.strip() == "/back" else "next"
runner = os.path.abspath(os.path.join(hooks, "..", "parts", "stage_runner.py"))
def run(args):
    return subprocess.run([sys.executable, runner] + args, capture_output=True, text=True)
def header():
    """Where the CURRENT step's full prompt lives (the runner masks the code word in that file, so the
    word itself is taken from the runner's full output in emit(), before any cap)."""
    path = "the stage prompt file for this step"
    s_ = run(["status", "--json", "--workdir", wd])
    try:
        idx = int(json.loads(s_.stdout).get("index"))
        cand = os.path.join(run_dir, "stage", "%02d.prompt.md" % idx)
        if os.path.exists(cand):
            path = cand
    except (ValueError, TypeError, OSError):
        pass
    return path
def cap(t, path, budget=4000):
    """The runner's output, capped to the budget; the truncation note names the CURRENT stage prompt file."""
    t = (t or "").strip()
    m = re.search(r"RUN-[0-9A-Z]{6}", t)
    if len(t) > budget:
        t = t[:max(budget, 500)] + "\nfull instructions in " + path
    return t, (m.group(0) if m else None)
def emit(body):
    """First line: the full prompt's path and the CURRENT code word, taken from the whole runner output
    BEFORE the cap, so a cut-off body can never lose it. Then the (capped) body."""
    path = header()
    seen = re.search(r"RUN-[0-9A-Z]{6}", body or "")
    first = "full prompt: %s; code word: %s" % (path, seen.group(0) if seen else "none issued")
    text, _ = cap(body, path, 4000 - len(first) - len(path) - 30)
    print(first)
    print(text)
try:  # tamper-evidence: log the turn BEFORE person-turn, so a mover that dies mid-call
    with open(os.path.join(run_dir, "mover.log"), "a", encoding="utf-8") as f:
        f.write(pid + "\n")                       # still leaves its line (verify reads this)
except OSError:
    pass
p = run(["person-" + "turn", "--turn", pid, "--cmd", cmd, "--workdir", wd])
if p.returncode != 0:
    print(TAG)
    emit(p.stdout + p.stderr)
    sys.exit(0)
q = run(["advance" if cmd == "next" else "back", "--turn", pid, "--workdir", wd])
print(TAG)
emit(q.stdout + q.stderr)
PY`
rc=$?
rm -f "$PAYLOAD_FILE" 2>/dev/null
case "$RESULT" in "") ;; *) printf '%s\n' "$RESULT" ;; esac
if [ "$rc" -ne 0 ]; then
  printf '%s the mover could not run (python failed, exit %s); tell the person\n' \
    '[RUN STEP — harness-injected, not user input]' "$rc"
fi
exit 0
