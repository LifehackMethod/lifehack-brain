#!/usr/bin/env python3
"""sb_start.py -- no runner, no run: the skill builder's runner is started by CODE (round 2b, B1) and the honest
catch-up (B5). Imported by system/hooks/run_step_hook.sh (the mover) on every person prompt; never run by the model.

WHY: in the first live run (2026-11-24) nothing told the model to start the step runner, so it never ran: no per-step
prompts, no back-room work, bars drawn by hand. Now the person's own `/skill-builder` prompt starts it, in code, before
the model sees the message. If it cannot start, the model is told one line and must stop.

WHAT: detect(prompt) -> (mode, arg): mode is None (not about the skill builder), "other" (observe / note / wrap: owned by
observe_ups.sh, this code does nothing), "normal" (the interview), or "catchup". begin() starts or resumes the run and
returns the lines to inject. catchup() starts a fresh run in an existing design folder from the step files already
written. per_turn() is the one-line run state for every later prompt (plus, from lib/sb_spec.py, the code-made bars, a bar mismatch and
the files read last turn, and, from lib/sb_waves.py, the ANSWER-moment wave list: the back-room helpers the AI runs in the turn).
begin()/catchup() also create the draft spec shell and flag the session for the spec reporter. handover() is the START-moment wave
list for a step that has just begun (called by the mover after /next and /back; begin() adds it for a fresh or resumed run).
after_move() prepares the next catch-up step file. The background writer is gone (2c): code hands over the list, the AI runs the
waves in the turn, code checks the receipts at Stop.
Every function returns lines to print; none raises (a failure is a NO RUN line). Nothing here writes a run record,
a pass, a person line or a handover: only stage_runner.py does that.
"""
# ── LLM CONTEXT ──────────────────────────────────────────────────────────────
# WHY: in the first live run (2026-11-24) nothing told the model to start the step runner, so the
#      run never happened: no per-step prompts, no back-room work, bars drawn by hand. This module
#      is the CODE path that starts the run from the person's own /skill-builder prompt, before
#      the model sees the message — the model never starts, moves or records a run of its own.
# GUARDS: Not a gate — never blocks a turn. Every function returns lines to inject or a single
#      "NO RUN" line; none raises. It starts stage_runner.py, which alone writes run records;
#      this code writes none. Observe/note/wrap words are handed off untouched to
#      observe_ups.sh.
# REDIRECT: Run mechanics live in system/parts/stage_runner.py (records, order, status); the
#      per-turn spec lines come from system/hooks/lib/sb_spec.py; the mover that calls this is
#      system/hooks/run_step_hook.sh. Prompt text for each step lives in
#      .claude/skills/skill-builder/prompts/.
# SIGNPOST: The rule that the runner is started by CODE and only the person's /next or /back
#      moves it is stated in the step prompts (step-1 §0) and SKILL.md — change the rule THERE;
#      this file only detects the command and relays stage_runner's output. Hook registration
#      goes through system/register/register.jsonl, never by hand.
# FAIL_POSTURE: degrade-safe — any failure becomes a one-line "NO RUN: (reason). Stop." the
#      model must relay and stop on; the turn is never wedged and no partial run state is left
#      for the model to clean up.
# ─────────────────────────────────────────────────────────────────────────────
import glob
import json
import os
import re
import subprocess
import sys
import time

TAG = "[RUN STEP — harness-injected, not user input]"
SKILL = "skill-builder"
MODE_WORDS = ("observe", "note", "wrap")
# ITEM 5 (2026-11-27): observe / note / wrap count ONLY when the person's prompt STARTS with the command (leading whitespace
# trimmed; the plugin form too). The same pattern as system/hooks/observe_ups.sh, so the two never disagree.
_MODE_LEAD = re.compile(r"\s*/(?:[A-Za-z0-9_-]+:)?skill-builder[ \t]+(observe|note|wrap)(?:[ \t]*[:\-\u2014][ \t\r\n]*|[ \t\r\n]+|$)")
_CMD = re.compile(r"(?:^|(?<=\s))/(?:[A-Za-z0-9_-]+:)?skill-builder(?![A-Za-z0-9_-])(?P<rest>[^\n]*)")


def _blank(prompt):
    """Fences and backtick spans blanked to spaces (same length), like observe_ups.sh: a command shown in code is not typed."""
    bt = chr(96)
    s = re.sub(bt * 3 + r".*?" + bt * 3, lambda m: " " * len(m.group(0)), prompt, flags=re.S)
    return re.sub(bt + r"[^" + bt + r"\n]*" + bt, lambda m: " " * len(m.group(0)), s)


def detect(prompt):
    """(mode, arg). An observe/note/wrap command at the START of the prompt wins ("other"); a mode word mentioned anywhere else
    (pasted or quoted text) is ignored altogether, never routed to observe and never to the normal job; then catch-up; then the normal job."""
    if not isinstance(prompt, str) or "skill-builder" not in prompt:
        return None, ""
    if _MODE_LEAD.match(prompt):
        return "other", ""
    scan = _blank(prompt)
    found = []
    for m in _CMD.finditer(scan):
        rest = prompt[m.start("rest"):m.end("rest")].strip()
        first = (rest.split() or [""])[0].lower().rstrip(":-—")
        found.append((first, rest))
    if not found:
        return None, ""
    found = [(first, rest) for first, rest in found if first not in MODE_WORDS]   # a pasted mode mention is nothing
    if not found:
        return None, ""
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


def _spec_on(hooks, wd, sid):
    """2b-Y: a run is live in this session: create the draft spec shell if missing and flag the session for the spec reporter
    and writer (lib/sb_spec.py). Never raises."""
    try:
        import sb_spec
        sb_spec.activate(_plug(hooks), wd, sid)
    except Exception as e:
        print("sb_start.py: spec activate failed: %s: %s" % (type(e).__name__, str(e)[:200]), file=sys.stderr)


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


def _run_dir(stage_runner, wd):
    found = stage_runner.find_run(wd)
    if not found:
        raise OSError("no run marker in %s" % wd)
    return found[1] if os.path.isabs(found[1]) else os.path.join(found[0], found[1])


def waves_lines(stage_runner, hooks, wd, st, sid, pid, moment, prompt="", tp="", visit=True):
    """The wave list for this moment (lib/sb_waves.py). One plain line when it cannot be made; never raises."""
    try:
        import sb_waves
        return sb_waves.render(_plug(hooks), hooks, wd, _run_dir(stage_runner, wd), st, sid, pid, moment, prompt, tp, visit)
    except Exception as e:
        print("sb_start.py: wave list failed: %s: %s" % (type(e).__name__, str(e)[:200]), file=sys.stderr)
        return [TAG + " WAVE LIST UNAVAILABLE (%s). Say so to the person in one plain line and run no back-room helper from memory."
                % type(e).__name__]


def handover(stage_runner, hooks, wd, sid, pid):
    """The START-moment wave list for the step the run is now on (after a typed /next or /back moved it). [] when none."""
    try:
        rc, st = _status(hooks, wd, sid)
        if rc != 0 or not st or st.get("skill") != SKILL or st.get("abandoned"):
            return []
        return waves_lines(stage_runner, hooks, wd, st, sid, pid, "start")
    except Exception:
        return []


def per_turn(stage_runner, hooks, cwd, sid, pid="", prompt="", tp=""):
    """The run state for a later prompt while a skill-builder run is live; [] otherwise. Carries the bars and, when the person has
    just answered (a prompt that is not a slash command), the ANSWER-moment wave list."""
    try:
        a = active_run(stage_runner, hooks, cwd, sid)
        if not a:
            return []
        out = [_run_line(a[1], a[0])]
        try:  # 2b-Y B4: the bars from code, a bar mismatch, the files read last turn
            import sb_spec
            out += sb_spec.turn_lines(hooks, a[0], sid)
        except Exception as e:
            out.append("per-turn bars unavailable: %s" % type(e).__name__)
            print("sb_start.py: per-turn bars failed: %s: %s" % (type(e).__name__, str(e)[:200]), file=sys.stderr)
        if pid and isinstance(prompt, str) and prompt.strip() and not prompt.lstrip().startswith("/"):
            out += waves_lines(stage_runner, hooks, a[0], a[1], sid, pid, "answer", prompt, tp)
        return out
    except Exception:
        return []


# ---------------------------------------------------------------- ITEM 1: resume like /ingest
# The state of a run lives in its design folder, not in the session id. A bare /skill-builder with no run found by cwd or by the
# session pointer looks for UNFINISHED runs in the design folders and ASKS (one line); nothing moves until the person answers.
# The offer is written to ~/.claude/run/resume-offer/offer-<sid>.json and is good for exactly the NEXT person prompt: a reply that
# is exactly yes / pick up / start new (or a number when several are listed) acts on it; any other prompt drops it.

OFFER_TTL = 24 * 3600
YES_WORDS = ("yes", "y", "pick up", "pick it up", "yes pick up", "yes please")
NEW_WORDS = ("start new", "new", "start a new one")


def _offer_dir():
    return os.path.join(os.path.expanduser("~"), ".claude", "run", "resume-offer")


def _offer_path(sid):
    return os.path.join(_offer_dir(), "offer-%s.json" % re.sub(r"[^A-Za-z0-9_-]", "_", sid or "nosession"))


def _taken_path(sid, pid):
    return _offer_path(sid)[:-5] + ".taken-" + re.sub(r"[^A-Za-z0-9_-]", "_", pid or "none")


def _sweep_taken(sid, keep=""):
    try:
        pre = os.path.basename(_offer_path(sid))[:-5] + ".taken-"
        for f in os.listdir(_offer_dir()):
            if f.startswith(pre) and os.path.join(_offer_dir(), f) != keep:
                os.unlink(os.path.join(_offer_dir(), f))
    except OSError:
        pass


def drop_offer(sid):
    """Forget a pending offer (the person typed something that is not an answer). Never raises."""
    try:
        os.unlink(_offer_path(sid))
    except OSError:
        pass


def _save_offer(sid, runs):
    os.makedirs(_offer_dir(), exist_ok=True)
    tmp = _offer_path(sid) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"t": time.time(), "runs": runs}, f)
    os.replace(tmp, _offer_path(sid))


def _design_name(wd):
    n = os.path.basename(os.path.normpath(wd))
    return n[len("packet-"):] if n.startswith("packet-") else n


def unfinished_runs(stage_runner, hooks, brain, sid, limit=40):
    """Unfinished skill-builder runs in the design folders under the notes folder, most recent first (read-only: find_run,
    status). Each: {wd, name, step, total, damaged, holding}. A run the runner reports DAMAGED (a changed card mid-run) is
    listed with damaged=True and is never repaired here. Real design folders win; _holding-* folders come back only when
    nothing else exists."""
    cands = []
    for pat in (os.path.join(brain, "drafts", "builds", "*"), os.path.join(brain, "state", "projects", "*", "packet-*")):
        for d in glob.glob(pat):
            m = os.path.join(d, stage_runner.MARKER)
            if os.path.isdir(d) and os.path.isfile(m):
                try:
                    cands.append((os.path.getmtime(m), d))
                except OSError:
                    pass
    cands.sort(reverse=True)
    out = []
    for _, wd in cands[:limit]:
        try:
            found = stage_runner.find_run(wd)
        except Exception:
            found = None
        if not found or os.path.realpath(found[0]) != os.path.realpath(wd):
            continue
        run_dir = found[1] if os.path.isabs(found[1]) else os.path.join(found[0], found[1])
        try:
            when = os.path.getmtime(os.path.join(run_dir, "record.jsonl"))
        except OSError:
            when = 0
        item = {"wd": wd, "name": _design_name(wd), "step": None, "total": None, "damaged": False, "updated": False,
                "holding": os.path.basename(wd).startswith("_holding-"), "when": when}
        rc, st = _status(hooks, wd, sid)
        if rc == 0 and st:
            if st.get("skill") != SKILL or st.get("complete") or st.get("abandoned"):
                continue
            item["step"], item["total"] = st.get("index"), st.get("total")
        elif rc in (stage_runner.DAMAGED, stage_runner.CARDCHANGED):
            try:   # best effort, read-only: whose run is it and where was it
                with open(os.path.join(wd, stage_runner.MARKER), encoding="utf-8") as f:
                    card_path = json.load(f).get("card", "")
                if os.path.basename(os.path.dirname(card_path)) != SKILL:
                    continue
                state = stage_runner.derive(stage_runner.load_record(run_dir))
                if state["complete"] or state["cur"] == "COMPLETE" or state["abandoned"]:
                    continue
                card = stage_runner.load_card(state["card"])
                idx = stage_runner.stage_index(card, state["cur"])
                item["step"], item["total"] = (idx + 1 if idx >= 0 else None), len(card["stages"])
            except Exception:  # allow-silence: display-only step number; the run is still listed (step shown as unknown)
                pass
            if rc == stage_runner.CARDCHANGED:
                item["updated"] = True   # the card changed since the run started: the person's yes can refresh it (the runner's `refresh`)
            else:
                item["damaged"] = True
        else:
            continue
        out.append(item)
    out.sort(key=lambda r: r["when"], reverse=True)
    real = [r for r in out if not r["holding"]]
    return real or out


DAMAGED_NOTE = "its record is damaged, so it cannot be picked up"
UPDATED_NOTE = "the skill was updated since you started"


def _where(r):
    return ("step %s of %s" % (r["step"], r["name"])) if r.get("step") else ("%s (step not known)" % r["name"])


def _carry(r):
    return "carry on with the new version%s" % ((" from step %s" % r["step"]) if r.get("step") else "")


def _offer_lines(runs):
    ask = TAG + " RESUME OFFER: an unfinished run was found, so no new run was started. Show the person exactly the text between " \
        "the markers, word for word, then STOP and wait for their answer. Start nothing, move nothing, run no helper, write nothing. "
    if len(runs) == 1:
        r = runs[0]
        if r["damaged"]:
            text = "You left off at %s, but %s. Start new? (start new)" % (_where(r), DAMAGED_NOTE)
        elif r.get("updated"):
            text = "You left off at %s: %s; %s? (yes / start new)" % (_where(r), UPDATED_NOTE, _carry(r))
        else:
            text = "You left off at %s. Pick up? (yes / start new)" % _where(r)
        return [ask + "[[" + text + "]]"]
    rows = []
    for i, r in enumerate(runs, 1):
        note = (" (%s)" % DAMAGED_NOTE) if r["damaged"] else ((" (%s; %s)" % (UPDATED_NOTE, _carry(r))) if r.get("updated") else "")
        rows.append("%d. %s%s" % (i, _where(r), note))
    text = "You have %d unfinished runs, most recent first:\n%s\nType the number to pick one up, or start new." % (len(runs), "\n".join(rows))
    return [ask + "[[" + text + "]]"]


def _norm_reply(prompt):
    t = " ".join((prompt or "").lower().split())
    return t.rstrip(".!")


def offer_reply(stage_runner, hooks, cwd, sid, pid, prompt):
    """The person's next prompt after a resume offer. None: no offer was waiting (the caller carries on as usual). A list of
    lines (maybe empty): the offer was handled and the caller must print them and stop. One offer answers one prompt: it is
    consumed whatever the person typed; only an exact yes / pick up / start new (or a listed number) acts on it."""
    try:
        taken = _taken_path(sid, pid)
        if pid and os.path.exists(taken):
            return []   # the twin copy of this hook already handled this very prompt
        mine = taken if pid else _offer_path(sid) + ".taken-x"
        try:
            os.replace(_offer_path(sid), mine)   # atomic: of two racing copies only one gets the offer
        except OSError:
            return [] if (pid and os.path.exists(taken)) else None   # lost the race to the twin copy: it handles the prompt
        _sweep_taken(sid, keep=mine)
        try:
            with open(mine, encoding="utf-8") as f:
                offer = json.load(f)
            runs = offer["runs"]
            fresh = time.time() - float(offer["t"]) < OFFER_TTL and isinstance(runs, list) and runs
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if not fresh:
            return None
        t = _norm_reply(prompt)
        pick = None
        if t in NEW_WORDS:
            return begin(stage_runner, hooks, cwd, sid, pid, "", fresh=True)
        if t in YES_WORDS:
            if len(runs) == 1:
                pick = runs[0]
            else:
                _save_offer(sid, runs)
                return [TAG + " RESUME OFFER: the person said yes but %d runs were listed. Tell them in one line to type the number of "
                        "the run to pick up (or start new). Start nothing." % len(runs)]
        else:
            m = re.fullmatch(r"(\d+)(?:\s+(?:yes|pick up))?", t) if len(runs) > 1 else None
            if m and 1 <= int(m.group(1)) <= len(runs):
                pick = runs[int(m.group(1)) - 1]
        if pick is None:
            return None   # not an answer: the offer is gone, the prompt goes on as an ordinary one
        if pick.get("damaged"):
            _save_offer(sid, runs)
            return [TAG + " RESUME OFFER: that run cannot be picked up: %s. Tell the person this in one line and offer "
                    "start new. Start nothing and do not touch the run." % DAMAGED_NOTE]
        return begin(stage_runner, hooks, cwd, sid, pid, "", pick=pick["wd"])
    except Exception as e:
        return _fail("the resume answer failed (%s)" % type(e).__name__)


def begin(stage_runner, hooks, cwd, sid, pid, name, pick=None, fresh=False):
    """The normal job: status first; resume an active run, otherwise start. Returns the lines to inject.
    pick: the design folder of an unfinished run the person said yes to (resume it, never start one). fresh: the person said
    start new (always a new run, never over an unfinished one)."""
    try:
        try:
            import sb_spec
            if not sb_spec.claim("begin", sid, pid):
                return []   # the twin copy of this hook (same prompt) is starting or resuming the run; one run only
        except ImportError:
            pass
        card = _card(hooks)
        if not card:
            return _fail("the skill builder's card.json was not found next to the plugin")
        notes = []
        drop_offer(sid)
        a = None if (pick or fresh) else active_run(stage_runner, hooks, cwd, sid)
        if a:
            wd = a[0]
        elif pick:
            wd = pick
        else:
            brain = _brain(hooks)
            if not brain:
                return _fail("your notes folder is not set, so there is nowhere to keep the design folder")
            base = os.path.join(brain, "drafts", "builds")
            if not name and not fresh:
                runs = unfinished_runs(stage_runner, hooks, brain, sid)
                if runs:
                    _save_offer(sid, [{k: r[k] for k in ("wd", "name", "step", "total", "damaged", "updated")} for r in runs])
                    return _offer_lines(runs)
            if name:
                wd = os.path.join(base, name)
            else:
                wd = os.path.join(base, "_holding-" + (sid or "nosession")[:8])
                if fresh:   # an explicit start new is always a NEW run: never the folder of one already in progress
                    n = 1
                    while os.path.isfile(os.path.join(wd, stage_runner.MARKER)):
                        n += 1
                        wd = os.path.join(base, "_holding-%s-%d" % ((sid or "nosession")[:8], n))
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
        elif rc == stage_runner.CARDCHANGED and pick:
            # ITEM 2 wired in: the person said yes to "carry on with the new version?": the runner pins the new card and carries on
            # at the SAME step (its `refresh`; it refuses, writing nothing, if the open step is gone from the new card)
            try:
                found = stage_runner.find_run(wd)
            except Exception as e:
                return _fail("the run record there is damaged (%s)" % e)
            if found:
                _log_person(found[1] if os.path.isabs(found[1]) else os.path.join(found[0], found[1]), pid)
            p = _run(hooks, ["refresh", "--choice", "continue", "--workdir", wd], sid)
            verb = "refresh"
        elif rc == 5 or (rc == 0 and st and (st.get("complete") or st.get("abandoned"))):
            p = _run(hooks, ["start", "--card", card, "--workdir", wd], sid)
            verb = "start"
        elif rc == stage_runner.CARDCHANGED:
            return _fail("the skill was updated since the run in %s started, so it was not touched; the person must say yes to "
                         "carrying on with the new version first" % wd)
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
        _spec_on(hooks, wd, sid)
        path = os.path.join(wd, "runs", st2.get("run") or "", "stage", "%02d.prompt.md" % int(st2.get("index") or 1))
        return [_run_line(st2, wd)] + notes + _emit(path, p.stdout + p.stderr) + waves_lines(stage_runner, hooks, wd, st2, sid, pid, "start", visit=(verb == "start"))   # a resume is not a new visit: it lists only what is still undone
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
        _spec_on(hooks, folder, sid)
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
