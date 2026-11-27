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
#      EXACTLY /next, /back, /lifehack-brain:next or /lifehack-brain:back (trimmed), not_the_person false (peer messages and task
#      notifications start with <cross-session-message / <task-notification — ups_triggers.py),
#      and a run marker found from the payload cwd. "/next please" is not the command. A peer or a
#      notification never moves a run. SB-10 (2026-11-25): the run is looked for in the payload cwd
#      first, then in the session's run pointer (system/tools/run_pointer.sh get, session id from the
#      payload), so /next and /back work from a window that is not in the run folder. An exact typed
#      /next or /back with no run found prints one tagged line ("no run is open in this window").
# REDIRECT: the runner's own refusals name the person's word ("only the person's typed /next moves
#      this step"); a failed step check says "not finished: <codes>" — the person types /next again.
# SIGNPOST: runner contract in system/parts/stage_runner.py header + RUNNER.md; the spec is the
#      run-pickup spec (G2). The AI-side rule lives in /next and /back's own text: no [RUN STEP]
#      line this turn means the mover did not run — tell the person.
# UPDATED: 2026-11-26 (round 2c waves: per_turn hands over the ANSWER-moment wave list and, after a typed /next or /back, handover() prints the
#      START-moment list of the step now begun; the lists come from lib/sb_waves.py via lib/sb_start.py; no new hook, no background writer).
#      2026-11-25 (also the plugin forms /lifehack-brain:next and :back, exact; round 2b B1/B5: the /skill-builder prompt starts or resumes the skill builder's run via
#      lib/sb_start.py; per-turn RUN line while it is live; /skill-builder catch-up; SB-10: run pointer second door; no-run line for an exact command).
#      2026-11-23 (Phase 4c fix pass: person.log for every person prompt,
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
sid = j.get("session_id") if isinstance(j.get("session_id"), str) else ""
ptext = prompt if isinstance(prompt, str) else ""
# B1 (round 2b): the skill builder cannot run without its runner. The person's own /skill-builder prompt starts (or resumes)
# the run here, in code, before the model sees the message. observe/note/wrap are observe_ups.sh's and are left alone.
NORUN = TAG + " NO RUN: %s. Stop. Tell the person this one line and do nothing else."
try:
    import sb_start
except Exception:
    sb_start = None
    if "/skill-builder" in ptext and not any(w in ptext for w in ("observe", "note", "wrap")):
        print(NORUN % "the run starter could not load")
        sys.exit(0)
sb_mode, sb_arg = sb_start.detect(ptext) if sb_start else (None, "")
try:
    import stage_runner
except BaseException as _e:  # a runner that cannot even load: the skill builder must stop; anything else fails as before
    if sb_mode in ("normal", "catchup"):
        print(NORUN % ("the step runner could not load (%s)" % type(_e).__name__))
        sys.exit(0)
    raise
if sb_mode == "normal":
    print("\n".join(sb_start.begin(stage_runner, hooks, cwd, sid, pid, sb_arg)))
    sys.exit(0)
if sb_mode == "catchup":
    print("\n".join(sb_start.catchup(stage_runner, hooks, sid, pid, sb_arg)))
    sys.exit(0)
try:
    found = stage_runner.find_run(cwd)  # reuse the runner's own marker walk, never a copy
except stage_runner.Damaged as e:
    print(TAG + " the run marker is damaged (%s); nothing ran; tell the person" % str(e)[:300])
    sys.exit(0)
# the plugin form is what the window autocompletes; same meaning, same exactness
STEP_CMDS = ("/next", "/back", "/lifehack-brain:next", "/lifehack-brain:back")
is_cmd = isinstance(prompt, str) and prompt.strip() in STEP_CMDS
if not found:
    # SB-10: the window's cwd is not the run folder. Second door: the session's run pointer, written
    # by the runner's start command (system/tools/run_pointer.sh over lib/flag.sh). cwd always wins first.
    env = dict(os.environ)
    sid = j.get("session_id")
    if isinstance(sid, str) and sid:
        env["CLAUDE_CODE_SESSION_ID"] = sid
    try:
        ptr = subprocess.run(["bash", os.path.join(hooks, "..", "tools", "run_pointer.sh"), "get"],
                             capture_output=True, text=True, env=env, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        ptr = ""
    if ptr and os.path.isdir(ptr):
        try:
            found = stage_runner.find_run(ptr)
        except stage_runner.Damaged as e:
            print(TAG + " the run marker is damaged (%s); nothing ran; tell the person" % str(e)[:300])
            sys.exit(0)
if not found:
    if is_cmd:  # the person typed the command but no run can be found: one plain line, nothing moves
        print(TAG + " no run is open in this window; nothing moved")
    sys.exit(0)  # no run here: silent for any other prompt
wd, run_dir = found
if not os.path.isabs(run_dir):
    run_dir = os.path.join(wd, run_dir)
# every person prompt is logged while a run is open (prompt_id and unix time, never the text)
try:
    with open(os.path.join(run_dir, "person.log"), "a", encoding="utf-8") as f:
        f.write("%s\t%d\n" % (pid, int(time.time())))
except OSError:
    pass
if not isinstance(prompt, str) or prompt.strip() not in STEP_CMDS:
    # the person's word, but not a step command: logged above, nothing moves. While a skill-builder run is live the
    # turn carries its state (B1.4), so the model cannot drift; observe/note/wrap turns belong to observe_ups.sh.
    if sb_start and sb_mode != "other":
        _l = sb_start.per_turn(stage_runner, hooks, cwd, sid, pid, ptext, j.get("transcript_path") if isinstance(j.get("transcript_path"), str) else "")
        if _l:
            print(TAG)
            print("\n".join(_l))
    sys.exit(0)
cmd = "back" if prompt.strip() in ("/back", "/lifehack-brain:back") else "next"
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
if cmd == "next" and q.returncode == 0 and sb_start:  # a catch-up run: stage the next finished step's file (code only)
    _l = sb_start.after_move(hooks, wd, run_dir, q.stdout + q.stderr, sid)
    if _l:
        print("\n".join(_l))
if q.returncode == 0 and sb_start and sb_mode != "other":  # 2c: the START-moment wave list of the step now begun (the mover already moved it: never held by a helper)
    _l = sb_start.handover(stage_runner, hooks, wd, sid, pid)
    if _l:
        print("\n".join(_l))
PY`
rc=$?
rm -f "$PAYLOAD_FILE" 2>/dev/null
case "$RESULT" in "") ;; *) printf '%s\n' "$RESULT" ;; esac
if [ "$rc" -ne 0 ]; then
  printf '%s the mover could not run (python failed, exit %s); tell the person\n' \
    '[RUN STEP — harness-injected, not user input]' "$rc"
fi
exit 0
