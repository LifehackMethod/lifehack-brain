#!/usr/bin/env python3
"""sb_start.py -- no runner, no run: the skill builder's runner is started by CODE (round 2b, B1) and the honest
catch-up (B5). Imported by system/hooks/run_step_hook.sh (the mover) on every person prompt; never run by the model.

WHY: in the first live run (2026-11-24) nothing told the model to start the step runner, so it never ran: no per-step
prompts, no back-room work, bars drawn by hand. Now the person's own `/skill-builder` prompt starts it, in code, before
the model sees the message. If it cannot start, the model is told one line and must stop.

WHAT: detect(prompt) -> (mode, arg): mode is None (not about the skill builder), "other" (observe / note / wrap: owned by
observe_ups.sh, this code does nothing), "normal" (the interview), or "catchup". begin() starts or resumes the run and
returns the lines to inject. catchup() starts a fresh run in an existing design folder from the step files already
written. per_turn() is the one-line run state for every later prompt. after_move() prepares the next catch-up step file.
Every function returns lines to print; none raises (a failure is a NO RUN line). Nothing here writes a run record,
a pass, a person line or a handover: only stage_runner.py does that.
"""
import json
import os
import re
import subprocess
import sys
import time

TAG = "[RUN STEP — harness-injected, not user input]"
SKILL = "skill-builder"
MODE_WORDS = ("observe", "note", "wrap")
_CMD = re.compile(r"(?:^|(?<=\s))/(?:[A-Za-z0-9_-]+:)?skill-builder(?![A-Za-z0-9_-])(?P<rest>[^\n]*)")


def _blank(prompt):
    """Fences and backtick spans blanked to spaces (same length), like observe_ups.sh: a command shown in code is not typed."""
    bt = chr(96)
    s = re.sub(bt * 3 + r".*?" + bt * 3, lambda m: " " * len(m.group(0)), prompt, flags=re.S)
    return re.sub(bt + r"[^" + bt + r"\n]*" + bt, lambda m: " " * len(m.group(0)), s)


def detect(prompt):
    """(mode, arg). Any observe/note/wrap command anywhere wins ("other"); then catch-up; then the normal job."""
    if not isinstance(prompt, str) or "skill-builder" not in prompt:
        return None, ""
    scan = _blank(prompt)
    found = []
    for m in _CMD.finditer(scan):
        rest = prompt[m.start("rest"):m.end("rest")].strip()
        first = (rest.split() or [""])[0].lower().rstrip(":-—")
        found.append((first, rest))
    if not found:
        return None, ""
    for first, rest in found:
        if first in MODE_WORDS:
            return "other", ""
    for first, rest in found:
        if first in ("catch-up", "catchup"):
            return "catchup", rest.split(None, 1)[1].strip() if len(rest.split(None, 1)) > 1 else ""
    rest = found[0][1]
    tok = (rest.split() or [""])[0]
    # a skill name is a kebab word with a hyphen (monthly-budget); any other word is just speech ("/skill-builder to ...")
    name = tok if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", tok) else ""
    return "normal", name


def _plug(hooks):
    return os.path.realpath(os.path.join(hooks, "..", ".."))


def _runner(hooks):
    return os.path.join(hooks, "..", "parts", "stage_runner.py")


def _card(hooks):
    plug = _plug(hooks)
    for rel in (".claude/skills/skill-builder/card.json", "skills/skill-builder/card.json"):
        p = os.path.join(plug, rel)
        if os.path.isfile(p):
            return p
    return ""


def _run(hooks, args, sid):
    env = dict(os.environ)
    if sid:
        env["CLAUDE_CODE_SESSION_ID"] = sid
    return subprocess.run([sys.executable, _runner(hooks)] + args, capture_output=True, text=True, env=env, timeout=90)


def _status(hooks, wd, sid):
    """(rc, dict or None) of `status --json` at wd."""
    p = _run(hooks, ["status", "--json", "--workdir", wd], sid)
    try:
        return p.returncode, json.loads(p.stdout)
    except ValueError:
        return p.returncode, None


def _fail(reason):
    reason = " ".join(str(reason).split())[:300]
    return [TAG + " NO RUN: " + reason + ". Stop. Tell the person this one line and do nothing else."]


def _run_line(st, wd):
    return "%s RUN: step %s of %s (%s), folder (%s)" % (TAG, st.get("index"), st.get("total"), st.get("stage"), wd)


def _brain(hooks):
    try:
        p = subprocess.run([sys.executable, os.path.join(_plug(hooks), "shared", "brain_root.py"), "--quiet"],
                           capture_output=True, text=True, timeout=20)
        b = (p.stdout.strip().splitlines() or [""])[0]
        return b if p.returncode == 0 and b and os.path.isdir(b) else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _set_pointer(hooks, wd, sid):
    try:
        env = dict(os.environ)
        if sid:
            env["CLAUDE_CODE_SESSION_ID"] = sid
        subprocess.run(["bash", os.path.join(hooks, "..", "tools", "run_pointer.sh"), "set", wd],
                       capture_output=True, text=True, env=env, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass


def _get_pointer(hooks, sid):
    try:
        env = dict(os.environ)
        if sid:
            env["CLAUDE_CODE_SESSION_ID"] = sid
        return subprocess.run(["bash", os.path.join(hooks, "..", "tools", "run_pointer.sh"), "get"],
                              capture_output=True, text=True, env=env, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _log_person(run_dir, pid):
    try:
        with open(os.path.join(run_dir, "person.log"), "a", encoding="utf-8") as f:
            f.write("%s\t%d\n" % (pid, int(time.time())))
    except OSError:
        pass


def _emit(path_hint, body, budget=3500):
    seen = re.search(r"RUN-[0-9A-Z]{6}", body or "")
    first = "full prompt: %s; code word: %s" % (path_hint, seen.group(0) if seen else "none issued")
    body = (body or "").strip()
    if len(body) > budget:
        body = body[:budget] + "\nfull instructions in " + path_hint
    return [first, body]


def active_run(stage_runner, hooks, cwd, sid):
    """(wd, status) of a live skill-builder run seen from this window (cwd first, then the session pointer), or None."""
    for start in (cwd, _get_pointer(hooks, sid)):
        if not start or not os.path.isdir(start):
            continue
        try:
            found = stage_runner.find_run(start)
        except Exception:
            continue
        if not found:
            continue
        wd = found[0]
        rc, st = _status(hooks, wd, sid)
        if rc == 0 and st and st.get("skill") == SKILL and not st.get("complete") and not st.get("abandoned"):
            return wd, st
    return None


def per_turn(stage_runner, hooks, cwd, sid):
    """The one-line run state for a later prompt while a skill-builder run is live; [] otherwise."""
    try:
        a = active_run(stage_runner, hooks, cwd, sid)
        return [_run_line(a[1], a[0])] if a else []
    except Exception:
        return []


def begin(stage_runner, hooks, cwd, sid, pid, name):
    """The normal job: status first; resume an active run, otherwise start. Returns the lines to inject."""
    try:
        card = _card(hooks)
        if not card:
            return _fail("the skill builder's card.json was not found next to the plugin")
        notes = []
        a = active_run(stage_runner, hooks, cwd, sid)
        if a:
            wd = a[0]
        else:
            brain = _brain(hooks)
            if not brain:
                return _fail("your notes folder is not set, so there is nowhere to keep the design folder")
            base = os.path.join(brain, "drafts", "builds")
            if name:
                wd = os.path.join(base, name)
            else:
                wd = os.path.join(base, "_holding-" + (sid or "nosession")[:8])
                notes.append(TAG + " HOLDING FOLDER: no skill name was given yet, so this run uses a holding folder named for "
                             "this session. A live run folder cannot be moved (the runner records its path), so it stays "
                             "the design folder; say its path to the person once the skill has a name.")
            try:
                os.makedirs(wd, exist_ok=True)
            except OSError as e:
                return _fail("could not create the design folder %s (%s)" % (wd, e))
        rc, st = _status(hooks, wd, sid)
        if rc == 0 and st and st.get("skill") == SKILL and not st.get("complete") and not st.get("abandoned"):
            try:
                found = stage_runner.find_run(wd)
            except Exception as e:
                return _fail("the run record there is damaged (%s)" % e)
            if found:
                _log_person(found[1] if os.path.isabs(found[1]) else os.path.join(found[0], found[1]), pid)
            p = _run(hooks, ["resume", "--choice", "continue", "--workdir", wd], sid)
            verb = "resume"
        elif rc == 5 or (rc == 0 and st and (st.get("complete") or st.get("abandoned"))):
            p = _run(hooks, ["start", "--card", card, "--workdir", wd], sid)
            verb = "start"
        else:
            return _fail("the step runner could not read the run in %s (it said exit %s: %s)"
                         % (wd, rc, "damaged or unreadable record"))
        if p.returncode != 0:
            first = (p.stdout + p.stderr).strip().splitlines()
            return _fail("the step runner would not %s (exit %s: %s)" % (verb, p.returncode, first[0] if first else "no message"))
        rc2, st2 = _status(hooks, wd, sid)
        if rc2 != 0 or not st2:
            return _fail("the step runner %s ran but its status could not be read afterwards" % verb)
        _set_pointer(hooks, wd, sid)
        path = os.path.join(wd, "runs", st2.get("run") or "", "stage", "%02d.prompt.md" % int(st2.get("index") or 1))
        return [_run_line(st2, wd)] + notes + _emit(path, p.stdout + p.stderr)
    except Exception as e:  # never raise into the prompt hook
        return _fail("the runner start failed (%s)" % type(e).__name__)


# ---------------------------------------------------------------- B5: the honest catch-up

def _words(text, drop):
    body = "\n".join(l for l in text.splitlines() if not re.match(r"^(#+ |Code word:)", l))
    return len(body.split())


def catchup(stage_runner, hooks, sid, pid, arg):
    """`/skill-builder catch-up <N> <design folder>`: a session already under way, with no run. Starts a FRESH run in the
    folder; the step files already written there (out/step-1.md .. out/step-N.md) are staged so their checks pass; the
    person then types /next once per finished step and the runner moves only on those typed turns. Nothing is written
    that claims a step moved (no person line, pass or handover): verify would flag it, and it would be forged."""
    try:
        m = re.match(r"^(\d)\s+(.+)$", arg.strip(), re.S)
        if not m or not 1 <= int(m.group(1)) <= 5:
            return _fail("catch-up needs the number of finished steps (1 to 5) and the design folder, like: "
                         "/skill-builder catch-up 3 /path/to/design-folder")
        n = int(m.group(1))
        folder = os.path.abspath(os.path.expanduser(m.group(2).strip().strip("\"'")))
        if not os.path.isdir(folder):
            return _fail("catch-up: %s is not a folder" % folder)
        card_path = _card(hooks)
        if not card_path:
            return _fail("the skill builder's card.json was not found next to the plugin")
        card = json.load(open(card_path, encoding="utf-8"))
        stages = card["stages"]
        rc, st = _status(hooks, folder, sid)
        if rc == 0 and st and not st.get("complete") and not st.get("abandoned"):
            return _fail("catch-up: a run is already active in %s; catch-up only starts a fresh run" % folder)
        bodies = {}
        for i in range(1, n + 1):
            src = os.path.join(folder, "out", "step-%d.md" % i)
            if not os.path.isfile(src) or not os.path.getsize(src):
                return _fail("catch-up stopped before starting: %s is missing or empty; write step %d's output there first "
                             "(it is not made up for you)" % (src, i))
            text = open(src, encoding="utf-8").read()
            chk = stages[i - 1].get("checks", {})
            lines = [l.rstrip() for l in text.splitlines()]
            miss = [h for h in chk.get("headings", []) if h not in lines]
            if miss:
                return _fail("catch-up stopped before starting: step %d's file lacks the heading(s) %s" % (i, ", ".join(miss)))
            if _words(text, None) < chk.get("min_words", 0):
                return _fail("catch-up stopped before starting: step %d's file has fewer than %d words" % (i, chk["min_words"]))
            bodies[i] = "\n".join(l for l in text.splitlines() if not l.startswith("Code word:")).rstrip() + "\n"
        p = _run(hooks, ["start", "--card", card_path, "--workdir", folder], sid)
        if p.returncode != 0:
            first = (p.stdout + p.stderr).strip().splitlines()
            return _fail("the step runner would not start (exit %s: %s)" % (p.returncode, first[0] if first else "no message"))
        rc2, st2 = _status(hooks, folder, sid)
        if rc2 != 0 or not st2:
            return _fail("the run started but its status could not be read afterwards")
        found = stage_runner.find_run(folder)
        run_dir = found[1] if os.path.isabs(found[1]) else os.path.join(found[0], found[1])
        os.makedirs(os.path.join(run_dir, "catchup"), exist_ok=True)
        for i, b in bodies.items():
            with open(os.path.join(run_dir, "catchup", "step-%d.md" % i), "w", encoding="utf-8") as f:
                f.write(b)
        code = re.search(r"RUN-[0-9A-Z]{6}", p.stdout)
        out1 = os.path.join(run_dir, stages[0]["out"])
        os.makedirs(os.path.dirname(out1), exist_ok=True)
        with open(out1, "w", encoding="utf-8") as f:
            f.write(bodies[1] + "\nCode word: %s\n" % (code.group(0) if code else ""))
        _set_pointer(hooks, folder, sid)
        chk = _run(hooks, ["check", "--workdir", folder], sid)
        ok = chk.returncode == 0
        return [_run_line(st2, folder),
                "%s CATCH-UP %s: a fresh run started in %s; step files 1 to %d were staged from the folder's own record "
                "(step 1's check: %s). Tell the person exactly this and nothing else: type /next %d times, one per finished "
                "step (the runner moves only on your typed /next; the last one lands you in step %d). Do not write any step "
                "file, record or code word yourself and do not start step 1 again."
                % (TAG, "READY" if ok else "STAGED BUT STEP 1 DOES NOT PASS YET", folder, n,
                   "PASS" if ok else "FAIL: " + " ".join(chk.stdout.split())[:200], n, n + 1)]
    except Exception as e:
        return _fail("catch-up failed (%s: %s)" % (type(e).__name__, str(e)[:120]))


def after_move(hooks, wd, run_dir, runner_out, sid):
    """After a typed /next moved the run: if the new step has a staged catch-up file, write it with the new code word
    (code only; the person's turn already moved the step). Returns lines to print."""
    try:
        cu = os.path.join(run_dir, "catchup")
        if not os.path.isdir(cu):
            return []
        rc, st = _status(hooks, wd, sid)
        if rc != 0 or not st or st.get("complete"):
            return []
        i = int(st.get("index") or 0)
        src = os.path.join(cu, "step-%d.md" % i)
        word = re.search(r"RUN-[0-9A-Z]{6}", runner_out or "")
        card = json.load(open(_card(hooks), encoding="utf-8"))
        out = os.path.join(run_dir, card["stages"][i - 1]["out"])
        if not os.path.isfile(src) or not word or os.path.exists(out):
            return []
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(open(src, encoding="utf-8").read() + "\nCode word: %s\n" % word.group(0))
        return [TAG + " CATCH-UP: step %d was finished before this run; its file is in place with the new code word. "
                "The person types /next again to move on. Do not rewrite it." % i]
    except Exception:
        return []
