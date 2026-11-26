#!/usr/bin/env python3
"""sb_spec.py -- the skill builder's back room in code (round 2b, Y): the spec REPORTER (B2), the spec WRITER's mechanics
(B3) and the BARS from code (B4). Imported by observe_ups.sh (the one-line report) and sb_start.py (the per-turn bars);
run as `python3 sb_spec.py stop <sid>` by end_of_turn_checks.sh (the cheap Stop check), and as `build-prompt` / `apply` by
spec_write.sh (the detached writer). No AI in this file: the model call itself is spec_write.sh's `run_model small`.

WHY: in the first live run the draft spec never existed, the person saw no sign of it, and the page and completion bars
were typed by hand. Now code creates the draft spec at run start, counts it with scripts/completion.py (ONE counter),
says on screen and to the model after every turn whether it moved, hands over the bars it computed, and checks the reply.

State (all under ~/.claude/run/observe/, per session; never in the plugin or the person's notes):
  spec-sess-<sid>.flag   wd=<run folder>      present = a skill-builder run is live in this session (the only file test
                                              the Stop and prompt hooks make; removed when the run is complete/abandoned)
  spec-state-<sid>.json  hash and size of draft-spec.md at the last report (the baseline for "changed / not changed this turn"),
                       plus "decided": did the person's prompt at that report look like a decision (DECISION_RE)
  spec-given-<sid>.json  the bar lines handed to the model this turn (the Stop check compares the reply with them)
  spec-offset-<sid>      transcript byte offset the writer has read to; spec-write-<sid>.pid  one writer at a time
  spec-mismatch-<sid>.txt / spec-read-<sid>.txt / spec-fail-<sid>.txt   one-shot notes for the next turn's line
  spec-saved-<sid>.txt   the writer's done-marker (2f), consumed to .shown after the SAVED line shows once
  spec-questions-<sid>.pid / .txt   the fresh questioner (2f): its pid, then its questions file
In the run folder: draft-spec.md (WRITTEN ONLY BY THE WRITER during a run) and spec-evidence.md (its quoted evidence).
"""
import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import time

SKILL = "skill-builder"
FORM_REL = os.path.join("system", "templates", "skill-spec-form", "skill-spec-form-v2.md")
HEADER = (
    "> **Saved by code's gated writer** (system/hooks/lib/spec_write.sh, brief 2f, 2026-11-25) after every round, from "
    "what the person just decided, and brought fully up to date by step 5's spec updater; the main window never writes "
    "this file. Only lines the round gives evidence for are filled; each new line ends with the inferred mark unless "
    "the person said or approved it; a confirmed line is never deleted, and a replaced line is kept beneath marked "
    "(superseded <date>). Evidence, quoted, is in spec-evidence.md beside this file.\n\n"
)
MAX_EDITS = 12
BLANK_SPAN = re.compile(r"<\[(?:ask|builder|after build)\][^<>]*>")
MARK_RE = re.compile(r"\s*(\[inferred\]|\[hypothesis\]|\[stale\]|\[builder's choice\]|\(D\d+\))")
PAGE_RE = re.compile(r"·\s*(?:page \d+ of \d+|all \d+ pages done)")
FIG_RE = re.compile(r"[▰▱]{10} \d+% ·")
# Decision words in the PERSON'S prompt (2c task 4): one place, cheap detection only -- the ⚠ spec-line check
# fires only when the person's words look like a decision AND the spec did not change this turn.
DECISION_RE = re.compile(r"(?i)\b(lock|locked|locks|locking|approve|approved|approves|approving|"
    r"agree|agreed|agrees|yes|go with|going with|decided|decide|decides|rule|ruled|ruling|"
    r"that'?s it|keep that|keep it|settled)\b")


# ------------------------------------------------------------------ paths and small helpers

def od():
    return os.path.join(os.path.expanduser("~"), ".claude", "run", "observe")


def _p(kind, sid, ext=""):
    return os.path.join(od(), "spec-%s-%s%s" % (kind, sid, ext))


def flag_path(sid):
    return os.path.join(od(), "spec-sess-%s.flag" % sid)


def _read(path, default=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return default


def _write_atomic(path, text):
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _json(path):
    try:
        return json.loads(_read(path) or "null")
    except ValueError:
        return None


def _log(what, e):
    """A failure is never silent: one tagged line on stderr and in ~/.claude/run/observe/spec-errors.log."""
    msg = "sb_spec.py: %s failed: %s: %s" % (what, type(e).__name__, " ".join(str(e).split())[:200])
    print(msg, file=sys.stderr)
    try:
        os.makedirs(od(), exist_ok=True)
        with open(os.path.join(od(), "spec-errors.log"), "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
    except OSError:
        pass  # allow-silence: the log itself is unwritable and the line is already on stderr; nothing further to say
    return msg


def _rm(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _plug(hooks):
    return os.path.realpath(os.path.join(hooks, "..", ".."))


def _skill_scripts(plug):
    for rel in (".claude/skills/skill-builder/scripts", "skills/skill-builder/scripts"):
        p = os.path.join(plug, rel)
        if os.path.isdir(p):
            return p
    return ""


def _load(plug, name):
    d = _skill_scripts(plug)
    if not d:
        raise ImportError("the skill builder's scripts folder was not found")
    spec = importlib.util.spec_from_file_location("sbs_" + name, os.path.join(d, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def claim(kind, sid, pid):
    """True for the FIRST caller per (kind, session, prompt). A window that loads the plugin AND has the repo's own settings
    registers a hook twice, and both copies run on one prompt; the second must not start a second run or print a second line."""
    if not pid or not sid:
        return True
    try:
        os.makedirs(od(), exist_ok=True)
        mine = "spec-lock-%s-%s-%s" % (kind, sid, re.sub(r"[^A-Za-z0-9_-]", "_", pid))
        for f in os.listdir(od()):   # one lock per kind and session: the previous prompt's lock goes, this prompt's stays
            if f.startswith("spec-lock-%s-%s-" % (kind, sid)) and f != mine:
                _rm(os.path.join(od(), f))
        fd = os.open(os.path.join(od(), mine), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        return False
    except OSError as e:
        _log("claim lock", e)
        return True


def flag_wd(sid):
    for line in _read(flag_path(sid)).splitlines():
        if line.startswith("wd="):
            return line[3:].strip()
    return ""


def _pid_alive(path):
    try:
        os.kill(int(_read(path).strip()), 0)
        return True
    except (ValueError, OSError):
        return False


# ------------------------------------------------------------------ the draft spec, the flag

def ensure_spec(plug, wd):
    """Create <wd>/draft-spec.md from the spec form v2 when missing (the first-fill shell). True when the file exists."""
    path = os.path.join(wd, "draft-spec.md")
    if os.path.isfile(path):
        return True
    form = _read(os.path.join(plug, FORM_REL))
    if not form:
        return False
    try:
        _write_atomic(path, HEADER + form)
        return True
    except OSError:
        return False


def _state_of(plug, wd):
    text = _read(os.path.join(wd, "draft-spec.md"))
    # 2d: the line says only "changed this turn / not changed this turn" by hash; the slot counting is dropped
    # (it misread a merged layout: 21 slots in 222 lines). The counts are not kept.
    return {"hash": hashlib.sha1(text.encode("utf-8", "replace")).hexdigest(), "size": len(text)}


def activate(plug, wd, sid):
    """A skill-builder run is live in this session: make the draft spec, set the flag, take the baseline. Never raises."""
    try:
        if not sid or os.environ.get("SPEC_WRITER_RUNNING"):   # a writer's own nested model session is never a run
            return
        os.makedirs(od(), exist_ok=True)
        ensure_spec(plug, wd)
        _write_atomic(flag_path(sid), "wd=%s\nat=%d\n" % (wd, int(time.time())))
        _write_atomic(_p("state", sid, ".json"), json.dumps(_state_of(plug, wd)))
    except Exception as e:
        _log("activate (draft spec / flag)", e)


def deactivate(sid):
    for kind, ext in (("sess", ".flag"), ("state", ".json"), ("given", ".json"), ("offset", ""), ("mismatch", ".txt"),
                      ("read", ".txt"), ("fail", ".txt"), ("turn", ".json"), ("write", ".pid"), ("saved", ".txt"),
                      ("saved", ".txt.shown"), ("questions", ".pid"), ("questions", ".txt"), ("questions", ".txt.shown")):
        _rm(_p(kind, sid, ext))


def run_active(hooks, wd, sid):
    try:
        import sb_start
        rc, st = sb_start._status(hooks, wd, sid)
        return bool(rc == 0 and st and st.get("skill") == SKILL and not st.get("complete") and not st.get("abandoned"))
    except Exception as e:
        _log("run status check", e)
        return False


# ------------------------------------------------------------------ B2: the reporter line

def report(hooks, sid, pid="", prompt=""):
    """The ONE line for the next prompt, or None (no live run). Compares the draft spec with the baseline of the
    last report. 2c task 4: a prompt that looks like a decision (DECISION_RE) is stored in the state; if the NEXT
    report still finds the spec unchanged, the line warns loudly -- the person decided and nothing was written."""
    try:
        if not claim("report", sid, pid):
            return None   # the twin copy of this hook (same prompt) already reported
        wd = flag_wd(sid)
        if not wd or not os.path.isdir(wd) or not run_active(hooks, wd, sid):
            deactivate(sid)
            return None
        plug = _plug(hooks)
        ensure_spec(plug, wd)
        now = _state_of(plug, wd)
        prev = _json(_p("state", sid, ".json"))
        state = dict(now)
        state["decided"] = bool(DECISION_RE.search(prompt)) if prompt else False
        try:
            _write_atomic(_p("state", sid, ".json"), json.dumps(state))
        except OSError:
            pass
        g = gate(sid, window=20, who="screen")
        if g and g[0]:
            return g[0]   # 2f: WAIT or SAVED replaces the changed/not-changed line while the gate holds
        extra = ""
        fail = _read(_p("fail", sid, ".txt")).strip()
        if fail:
            extra = " · the writer did not run: %s" % fail[:160]
            _rm(_p("fail", sid, ".txt"))
        if not prev or prev.get("hash") == now["hash"]:
            line = "📋 Spec: not changed this turn" + extra
            if prev and prev.get("decided"):
                line = "⚠ You decided something this turn; the spec did not change. " + line
            return line
        return "📋 Spec: changed this turn" + extra
    except Exception as e:
        return "📋 Spec line unavailable: %s" % _log("spec report", e)[:160]


# ------------------------------------------------------------------ 2f: the gate

GATE_WAIT_SCREEN = "📋 Spec: WAIT — saving your answers from the last round; nothing lost."
GATE_WAIT_MODEL = ("GATE: WAIT — saving your answers from the last round. Ask no new questions, findings or reviewers, "
                   "and launch no helper that reads the spec, until the SAVED line appears.")
GATE_Q_FAILED = ("QUESTIONS: the fresh read failed — say so in one line and ask no new numbered questions this round.")


GATE_QTEXT_CAP = 6000


def gate(sid, consume=True, window=0, who=""):
    """(screen line, model line) from the gate markers (2f), or (None, None) when neither applies — the caller then
    shows today's changed/not-changed line. Writer or questioner pid alive -> WAIT. Done-marker present -> SAVED, with
    the questioner's text carried IN the model line (B1: the model never has to open a file that is about to be renamed);
    the marker (and the questions file) is renamed .shown after the line has been produced once. A marker that starts
    with FAILED is the loud 'could not save' line and releases no questions. `who` ('screen' or 'model') names the
    caller when `window` is set: the second hook of one prompt replays the first's pair ONCE, and each caller sees it at
    most once (S3: a later prompt never replays an old SAVED line)."""
    try:
        if _pid_alive(_p("write", sid, ".pid")) or _pid_alive(_p("questions", sid, ".pid")):
            return GATE_WAIT_SCREEN, GATE_WAIT_MODEL
        mk = _p("saved", sid, ".txt")
        marker = _read(mk).strip()
        cache = _p("gate-seen", sid, ".json")
        if not marker:
            if window and who:
                try:
                    c = json.loads(_read(cache) or "{}")
                    if c.get("pair") and who not in (c.get("seen") or []) and time.time() - c.get("t", 0) <= window:
                        c["seen"] = list(c.get("seen") or []) + [who]
                        _write_atomic(cache, json.dumps(c))
                        return tuple(c["pair"])
                except Exception:  # allow-silence: no usable replay cache just means no SAVED line is replayed
                    pass
            return None, None
        qf = _p("questions", sid, ".txt")
        q = _read(qf).strip()
        if marker.startswith("FAILED"):
            reason = marker[len("FAILED"):].lstrip(": ").strip()
            screen = "📋 Spec: ⚠ COULD NOT SAVE — %s. Your answers are kept; the next turn tries again." % reason
            model = ("GATE: COULD NOT SAVE — %s. Say so to the person in one line, with the reason. Ask no new numbered "
                     "questions, findings or reviewers this round; the answers are kept and the next turn retries." % reason)
            q = ""
            if consume:
                _rm(_p("fail", sid, ".txt"))
        else:
            screen = "📋 Spec: SAVED — %s" % marker
            if q and not q.startswith("NONE (the fresh read failed)"):
                model = ("GATE: SAVED — %s. QUESTIONS (from code): show these under # QUESTIONS exactly as written, in "
                         "order. Never invent questions from this conversation.\n%s"
                         % (marker, q[:GATE_QTEXT_CAP]))
            else:
                model = "GATE: SAVED — %s. %s" % (marker, GATE_Q_FAILED)
        if consume:
            try:
                os.replace(mk, mk + ".shown")
            except OSError:
                pass
            if q:
                try:
                    os.replace(qf, qf + ".shown")
                except OSError:
                    pass
        if consume and window:
            try:
                _write_atomic(cache, json.dumps({"t": time.time(), "pair": [screen, model], "seen": [who] if who else []}))
            except OSError:
                pass
        return screen, model
    except Exception as e:
        _log("spec gate", e)
        return None, None


# ------------------------------------------------------------------ B4: bars from code, read list, mismatch

def bar_lines(plug, wd):
    """The lines the model must print exactly: each page-bar section in pages.json, then the completion figure."""
    out = []
    try:
        pb = _load(plug, "page_bar")
        data = _json(os.path.join(wd, "pages.json")) or {}
        for name, sec in (data.get("sections") or {}).items():
            try:
                out.append("PAGE BAR (from code, section %s; print it only on screens of that section): %s" % (name, pb.render(sec)))
            except Exception as e:
                _log("page bar section %s" % name, e)
                out.append("PAGE BAR (from code, section %s): unavailable (%s); show no bar" % (name, type(e).__name__))
    except Exception as e:
        _log("page bars", e)
        out.append("PAGE BAR (from code): unavailable (%s); show no page bar" % type(e).__name__)
    try:
        fig = _load(plug, "completion").figure_line(_read(os.path.join(wd, "draft-spec.md")))
        out.append("FIGURE (from code): %s" % fig if fig else "FIGURE (from code): none this turn (no figure line, keep the heading)")
    except Exception as e:
        _log("completion figure", e)
        out.append("FIGURE (from code): unavailable (%s); show no figure line" % type(e).__name__)
    return out


def _bar_values(lines):
    vals = []
    for l in lines:
        m = re.match(r"^(?:PAGE BAR|FIGURE) \(from code[^)]*\):\s*(.+)$", l)
        if m and not m.group(1).startswith("none this turn"):
            vals.append(m.group(1).strip())
    return vals


def turn_lines(hooks, wd, sid):
    """Lines appended to the per-turn RUN line (sb_start.per_turn): the bars, a bar mismatch, the files read last turn."""
    out = []
    try:
        g = gate(sid, window=20, who="model")
        if g and g[1]:
            out.append(g[1])   # 2f: WAIT / SAVED + QUESTIONS, the same lines the screen shows
    except Exception as e:
        out.append("spec gate unavailable: %s" % _log("spec gate", e)[:160])
    try:
        plug = _plug(hooks)
        bl = bar_lines(plug, wd)
        out += bl
        try:
            _write_atomic(_p("given", sid, ".json"), json.dumps(_bar_values(bl)))
        except OSError:
            pass
        out.append("Print these bar lines exactly as given, never typed from memory; if one is missing, show no bar.")
        mm = _read(_p("mismatch", sid, ".txt")).strip()
        if mm:
            out.append("BAR MISMATCH: %s Tell the person in one line, then print the given lines exactly." % mm)
            _rm(_p("mismatch", sid, ".txt"))
        rd = _read(_p("read", sid, ".txt")).strip()
        out.append("READ LAST TURN (by code, from the transcript's tool calls): %s" % (rd or "no files"))
    except Exception as e:
        out.append("per-turn bars unavailable: %s" % _log("turn lines", e)[:160])
    return out


def _strip(s):
    return s.strip().strip("`_>| ").strip()


def _transcript_entries(tp):
    try:
        raw = open(tp, "rb").read()
    except OSError:
        return []
    out = []
    for line in raw.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def _text_of(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _is_prompt(d):
    if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
        return False
    txt = _text_of((d.get("message") or {}).get("content")).strip()
    return bool(txt) and not txt.startswith(("[harness-injected", "<command-", "<local-command", "<system-reminder>"))


_BASH_READ = re.compile(r"(?:^|[;&|]\s*)(?:cat|head|tail|less|sed(?:\s+-n\s+'[^']*')?)\s+(?:-\S+\s+)*(\"[^\"]+\"|'[^']+'|[^\s;&|<>]+)")


def files_read_last_turn(entries):
    last = max([i for i, d in enumerate(entries) if _is_prompt(d)] or [-1])
    seen = []
    for d in entries[last + 1:]:
        if d.get("type") != "assistant":
            continue
        c = (d.get("message") or {}).get("content")
        for b in c if isinstance(c, list) else []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            inp = b.get("input") or {}
            paths = []
            if b.get("name") == "Read" and isinstance(inp.get("file_path"), str):
                paths.append(inp["file_path"])
            elif b.get("name") == "Bash" and isinstance(inp.get("command"), str):
                paths += [m.strip("\"'") for m in _BASH_READ.findall(inp["command"])]
            for p in paths:
                label = "/".join(p.rstrip("/").split("/")[-2:])
                if label and label not in seen:
                    seen.append(label)
    return seen


def stop_check(hooks, sid, payload_text):
    """Cheap Stop step: (1) does a bar in the reply match what code gave or gives now? (2) which files were read this turn?"""
    try:
        wd = flag_wd(sid)
        if not wd:
            return
        plug = _plug(hooks)
        j = json.loads(payload_text)
        reply = j.get("last_assistant_message") or ""
        accepted = [_strip(a) for a in (_json(_p("given", sid, ".json")) or [])]
        accepted += [_strip(a) for a in _bar_values(bar_lines(plug, wd))]
        bad = []
        for line in reply.splitlines():
            s = _strip(line)
            is_page = bool(PAGE_RE.search(s) and re.search(r"[✅▶⬜]", s))
            if is_page or FIG_RE.search(s):
                if not any(s == a or s.endswith(a) for a in accepted if a):
                    bad.append((is_page, s))
        if bad:
            is_page, s = bad[0]
            want = [a for a in accepted if a and (bool(PAGE_RE.search(a)) == is_page)]
            _write_atomic(_p("mismatch", sid, ".txt"), "the last reply showed '%s' but code gave %s." % (
                s[:140], ("'%s'" % want[0][:140]) if want else "no such bar this turn"))
        else:
            _rm(_p("mismatch", sid, ".txt"))
        names = files_read_last_turn(_transcript_entries(j.get("transcript_path") or ""))
        _write_atomic(_p("read", sid, ".txt"), ", ".join(names[:8]) + (" (+%d more)" % (len(names) - 8) if len(names) > 8 else ""))
    except Exception as e:
        _log("stop check (bars / files read)", e)


# ------------------------------------------------------------------ B3: the writer's mechanics

def _turns(tp, offset):
    """(list of (who, text), new offset) from the transcript since offset: person and assistant text only."""
    SR = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
    try:
        size = os.path.getsize(tp)
        start = int(offset) if str(offset).isdigit() and int(offset) <= size else None
        with open(tp, "rb") as f:
            if start:
                f.seek(start)
            raw = f.read()
        raw = raw[:raw.rfind(b"\n") + 1]
        new_off = (start or 0) + len(raw)
    except OSError:
        return [], None
    turns = []
    for line in raw.split(b"\n"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        t = d.get("type")
        if t not in ("user", "assistant") or d.get("isMeta") or d.get("isSidechain"):
            continue
        txt = SR.sub("", _text_of((d.get("message") or {}).get("content"))).strip()
        if not txt or txt.startswith(("[harness-injected", "<command-", "<local-command")):
            continue
        turns.append(("PERSON" if t == "user" else "SKILL", txt))
    if start is None:   # first review: just the last turn, from the last person message
        last_u = max([i for i, (w, _) in enumerate(turns) if w == "PERSON"] or [0])
        turns = turns[last_u:]
    return turns, new_off


_WRITER_BRIEF_RELS = (".claude/skills/skill-builder/prompts/subagents/spec-writer.md",
                      "skills/skill-builder/prompts/subagents/spec-writer.md")


def _writer_brief(plug):
    for rel in _WRITER_BRIEF_RELS:
        p = os.path.join(plug, rel)
        if os.path.isfile(p):
            return p
    return ""
PACKET_CAP = 20000


def _packet_brief(wd):
    """The packet files the writer appends to, capped (the writer never sees the conversation)."""
    parts, total = [], 0
    for name in ("notes.md", "rulings.md", "research.md"):
        t = _read(os.path.join(wd, name))
        if not t:
            parts.append("=== %s (absent or empty) ===" % name)
            continue
        if total + len(t) > PACKET_CAP:
            t = t[:max(0, PACKET_CAP - total)] + "\n(packet cut for length)"
        total += len(t)
        parts.append("=== %s (current) ===\n%s" % (name, t))
    return "\n\n".join(parts)


def build_prompt(plug, payload_file, prompt_file, wd, sid):
    """Writes the writer's launch prompt: the brief file (prompts/subagents/spec-writer.md, everything above its test
    card) plus the draft spec, the packet and the round's turns. Returns 'OK <new offset>' or 'FAIL <reason>'."""
    if not wd or not os.path.isabs(wd) or not os.path.isdir(wd):
        return "FAIL no run folder (%r)" % (wd,)
    try:
        bp = _writer_brief(plug)
        brief = _read(bp) if bp else ""
        if "— TEST CARD —" in brief:
            brief = brief.split("— TEST CARD —")[0].rstrip()
        if not brief:
            return "FAIL the writer brief is missing (prompts/subagents/spec-writer.md)"
        p = json.loads(_read(payload_file))
    except ValueError as e:
        return "FAIL payload not JSON: %s" % e
    tp = p.get("transcript_path") or ""
    turns, new_off = _turns(tp, _read(_p("offset", sid)).strip())
    if not turns:
        lam = p.get("last_assistant_message") or ""
        turns = [("SKILL", lam or "(no text found for this turn)")]
        new_off = None
    body = "\n\n".join("%s: %s" % (w, t) for w, t in turns)
    cap = int(os.environ.get("SPEC_TRANSCRIPT_CAP", "20000"))
    if len(body) > cap:
        body = "(earlier text cut)\n" + body[-cap:]
    spec = _read(os.path.join(wd, "draft-spec.md"))
    if not spec:
        return "FAIL the draft spec is missing or empty (%s)" % os.path.join(wd, "draft-spec.md")
    if len(spec) > 90000:
        spec = spec[:90000] + "\n(spec cut for length)"
    packet = _packet_brief(wd)
    prompt = ("At most %d records in your reply, `---` between records, and END-WRITE on its own last line.\n\n%s"
              "\n\n=== THE DRAFT SPEC (current) ===\n%s\n\n%s\n\n=== THE ROUND\u2019S TURNS (the only evidence) ===\n%s\n"
              % (MAX_EDITS, brief, spec, packet, body))
    # the nested model session runs the same hooks: no literal slash-command may appear in its prompt
    _write_atomic(prompt_file, prompt.replace("/skill-builder", "skill-builder"))
    try:
        _write_atomic(_p("turn", sid, ".json"), json.dumps({"person": [t for w, t in turns if w == "PERSON"], "all": body}))
    except OSError:
        pass
    return "OK %s" % (new_off if new_off is not None else "")


def _norm(s):
    return " ".join(s.split()).lower()


REC_KEYS = ("SLOT", "VALUE", "BY", "EVIDENCE", "CONFIRM", "REPLACE", "NEW",
            "SAID", "RULED", "RESEARCH", "BY-HAND", "REFINEMENT", "DEFERRED", "STALE", "UNSTALE")
_HEAD_KEYS = ("SLOT", "CONFIRM", "REPLACE", "SAID", "RULED", "RESEARCH", "BY-HAND",
              "REFINEMENT", "DEFERRED", "STALE", "UNSTALE")
_KEY_RE = re.compile(r"^(%s):\s*(.*)$" % "|".join(REC_KEYS))


def _parse(reply):
    """The writer's records (brief 2f): spec records (SLOT/CONFIRM/REPLACE) and packet records (SAID...UNSTALE)."""
    recs, cur = [], {}
    for raw in reply.splitlines():
        line = raw.strip()
        if line.endswith("END-WRITE"):   # the marker on its own line or glued to the end of a line: both end the reply
            line = line[:-len("END-WRITE")].strip()
            if line and line != "---":
                m0 = _KEY_RE.match(line)
                if m0:
                    cur[m0.group(1)] = m0.group(2).strip()
            if cur:
                recs.append(cur)
            cur = {}
            continue
        if line == "---":
            if cur:
                recs.append(cur)
            cur = {}
            continue
        m = _KEY_RE.match(line)
        if m:
            if m.group(1) in _HEAD_KEYS and any(k in cur for k in _HEAD_KEYS):
                recs.append(cur)
                cur = {}
            cur[m.group(1)] = m.group(2).strip()
    if cur:
        recs.append(cur)
    return recs


def _clean_value(v):
    v = MARK_RE.sub("", v)
    v = v.replace("<", "‹").replace(">", "›")
    return " ".join(v.split())


PACKET_HOME = {
    "SAID": ("notes.md", "SAID"),
    "BY-HAND": ("notes.md", "BY HAND"),
    "REFINEMENT": ("notes.md", "STEP-PROMPT REFINEMENTS"),
    "DEFERRED": ("notes.md", "DEFERRED WORK"),
    "STALE": ("notes.md", "STALE"),
    "UNSTALE": ("notes.md", "STALE"),
    "RULED": ("rulings.md", "RULED"),
    "RESEARCH": ("research.md", "RESEARCH"),
}
_STALE_TS = re.compile(r"^\s*-\s*\[[^\]]+\]\s*")


def _append_under(text, heading, line):
    """`line` added at the END of `heading`'s section (a heading matched at any # level, name equal); a heading the
    packet does not use yet is created at the end of the file. Returns the new text."""
    lines = text.split("\n")
    hi = None
    for k, l in enumerate(lines):
        m = re.match(r"^#{1,6}\s+(.+?)\s*$", l.strip())
        if m and m.group(1).strip() == heading:
            hi = k
            break
    if hi is None:
        head = (text.rstrip("\n") + "\n\n") if text.strip() else ""
        return head + "## %s\n%s\n" % (heading, line)
    j = len(lines)
    for k in range(hi + 1, len(lines)):
        if re.match(r"^#{1,6}\s+", lines[k].strip()):
            j = k
            break
    lines.insert(j, line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def _drop_stale(text, section):
    """One line in the STALE section dropped (the person re-confirmed it); a non-empty section keeps its heading."""
    lines = text.split("\n")
    hi, out, insec = None, [], False
    for k, l in enumerate(lines):
        m = re.match(r"^#{1,6}\s+(.+?)\s*$", l.strip())
        if m:
            name = m.group(1).strip()
            if name == "STALE":
                hi, insec = k, True
                out.append(l)
                continue
            insec = False
        if insec and not m and _norm(_STALE_TS.sub("", l).lstrip("-* ")).startswith(_norm(section)):
            continue   # the dropped line
        out.append(l)
    if hi is None:
        return text
    return "\n".join(out)


def _apply_packet(wd, recs, ts):
    """Append-only packet writes (2f). Returns (applied, skipped, {file: new text}) — nothing written here; the caller
    writes after every guard has passed, so a spec abort leaves the packet untouched too."""
    applied, skipped, files = 0, 0, {}
    for r in recs:
        kind = next((k for k in PACKET_HOME if k in r), None)
        if not kind:
            continue
        fname, heading = PACKET_HOME[kind]
        text = files.get(fname)
        if text is None:
            text = _read(os.path.join(wd, fname))
        val = " ".join((r.get(kind) or "").split())
        if not val:
            skipped += 1
            continue
        if kind == "UNSTALE":
            new = _drop_stale(text, val)
            if new != text:
                files[fname] = new
                applied += 1
            else:
                skipped += 1
            continue
        line = "- [%s] %s" % (ts, val)
        have = {_norm(_STALE_TS.sub("", l)) for l in text.splitlines()}
        if _norm(val) in have or _norm(line) in have:
            skipped += 1
            continue
        files[fname] = _append_under(text, heading, line)
        applied += 1
    return applied, skipped, files


def apply_reply(plug, reply_file, wd, sid, new_off):
    """Apply the writer's records (brief 2f) to draft-spec.md AND the packet: only blank spans and unconfirmed lines
    change; the packet is append-only; the result is checked against every confirmed line before the writes (one
    atomic rename for the spec; the packet is touched only after every guard has passed). Returns a one-line summary."""
    if not wd or not os.path.isabs(wd) or not os.path.isdir(wd):   # B2: never write relative to the cwd
        return "FAILED: no run folder to write into (%r); nothing written, the answers are kept for the next try" % (wd,)
    comp = _load(plug, "completion")
    path = os.path.join(wd, "draft-spec.md")
    text = _read(path)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    ev = []
    unparsed = False
    guard_lost = False
    replaced_conf = set()   # confirmed lines deliberately superseded this write (B3)
    reply = _read(reply_file)
    recs = _parse(reply)
    turn = _json(_p("turn", sid, ".json")) or {}
    persons = _norm(" ".join(turn.get("person") or []))
    allturn = _norm(turn.get("all") or "")
    elig = {}   # line start offset -> (line, section), for lines that may be slots
    for off, line, section in comp.scan(text):
        elig[off] = (line, section)
    old_confirmed = [l for (l, s) in elig.values() if s == "count" and comp._classify(l) == "done"]
    edits = []   # (start, end, replacement)
    dlines = []
    cited = [int(n) for (l, _s) in elig.values() for n in re.findall(r"\(D(\d+)\)", l)]   # example paragraphs are not in elig
    next_d = 1 + max([int(m.group(1)) for m in re.finditer(r"(?m)^D(\d+) · ", text)] + cited or [0])
    used = set()
    applied = 0
    if not recs and not re.search(r"(?m)^\s*NOTHING\s*$", reply.replace("END-WRITE", "\n")):
        unparsed = True
        ev.append("- [%s] UNPARSED writer reply (no records, not NOTHING): %s" % (ts, " ".join(reply.split())[:300]))
    packet_applied, packet_skipped, packet_files = _apply_packet(wd, recs, ts)
    for r in recs[:MAX_EDITS]:
        if any(k in r for k in PACKET_HOME) and not any(k in r for k in ("REPLACE", "CONFIRM", "SLOT")):
            continue   # a packet record: handled by _apply_packet above, never a "rejected" spec record
        quote = r.get("EVIDENCE", "").strip().strip("\"'“”")
        qn = _norm(quote)
        if "REPLACE" in r:
            key = _norm(r["REPLACE"]).lstrip("-* ")
            newv = _clean_value(r.get("NEW", ""))
            allhits = [(o, l) for o, (l, s) in elig.items() if s == "count" and len(key) >= 12
                       and _norm(l).lstrip("-* ").startswith(key)]
            # B3: newest wins on confirmed lines too; a kept "(superseded ...)" line is never a target (N2)
            hits = [(o, l) for o, l in allhits if "(superseded " not in l]
            if len(hits) != 1 or not newv or not quote or not qn:
                ev.append("- [%s] REJECTED replace (%s): %s" % (
                    ts, "no unique unconfirmed line" if len(hits) != 1 else "empty new text or no evidence quote",
                    r["REPLACE"][:80]))
                continue
            o, l = hits[0]
            if o in used:
                continue
            used.add(o)
            pre = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", l)
            was_conf = bool(re.search(r"\(D\d+\)", comp.CODE_SPAN_RE.sub(" ", l))) or comp._classify(l) == "done"
            nl = (pre.group(0) if pre else "") + newv
            if qn not in persons:
                nl += " [inferred]"   # code adds the mark; the writer never types it
            elif was_conf:
                nl += " (D%d)" % next_d
                dlines.append("D%d · %s · %s · the person's words (replaces an earlier decision)" % (
                    next_d, time.strftime("%Y-%m-%d"), newv[:200]))
                next_d += 1
            kept = re.sub(r"\s*\(D\d+\)", "", l) if was_conf else l   # the old cite goes so it is not counted as a slot
            if was_conf:
                replaced_conf.add(l)
            keep = kept.rstrip() + " (superseded %s)" % time.strftime("%Y-%m-%d")
            edits.append((o, o + len(l), nl + "\n" + keep))
            ev.append("- [%s] REPLACED: %s -> \"%s\" (old line kept, superseded %s) · evidence: \"%s\"%s" % (
                ts, r["REPLACE"][:70], newv[:120], time.strftime("%Y-%m-%d"), quote[:200],
                "" if qn in persons else " [inferred]"))
            applied += 1
            continue
        if "CONFIRM" in r:
            key = _norm(r["CONFIRM"]).lstrip("-* ")
            hits = [(o, l) for o, (l, s) in elig.items() if s == "count" and len(key) >= 12
                    and re.search(r"\[inferred\]|\[hypothesis\]", comp.CODE_SPAN_RE.sub(" ", l))
                    and _norm(l).lstrip("-* ").startswith(key)]
            if len(hits) != 1 or not qn or qn not in persons:
                ev.append("- [%s] REJECTED confirm (%s): %s · evidence: \"%s\"" % (
                    ts, "no unique unconfirmed line" if len(hits) != 1 else "the person's words do not contain the quote",
                    r["CONFIRM"][:80], quote[:120]))
                continue
            o, l = hits[0]
            if o in used:
                continue
            used.add(o)
            nl = re.sub(r"\s*\[(?:inferred|hypothesis)\]", "", l).rstrip() + " (D%d)" % next_d
            edits.append((o, o + len(l), nl))
            dlines.append("D%d · %s · %s · the person's words" % (next_d, time.strftime("%Y-%m-%d"), _clean_value(l.lstrip("-* "))[:200]))
            ev.append("- [%s] CONFIRMED D%d: %s · evidence (person): \"%s\"" % (ts, next_d, _clean_value(l)[:120], quote[:200]))
            next_d += 1
            applied += 1
            continue
        slot, value, by = r.get("SLOT", ""), _clean_value(r.get("VALUE", "")), r.get("BY", "").upper()
        key = _norm(slot)
        spans = [m for m in BLANK_SPAN.finditer(text) if len(key) >= 12 and _norm(m.group(0)).startswith(key)
                 and any(o <= m.start() < o + len(l) and s == "count" for o, (l, s) in elig.items())]
        if len(spans) != 1 or not value or not quote:
            ev.append("- [%s] REJECTED (%s): %s" % (ts, "no unique open blank" if len(spans) != 1 else "empty value or no evidence quote", slot[:80]))
            continue
        m = spans[0]
        if m.start() in used:
            continue
        used.add(m.start())
        who = "person" if by == "PERSON" and qn in persons else "inferred"
        note = ""
        if by == "PERSON" and who != "person":
            note = " (marked PERSON but the quote is not in the person's words: written as inferred)"
        elif qn and qn not in allturn:
            note = " (quote not found verbatim in the turn)"
        if who == "person":
            rep = "%s (D%d)" % (value, next_d)
            dlines.append("D%d · %s · %s · the person's words" % (next_d, time.strftime("%Y-%m-%d"), value[:200]))
            ev.append("- [%s] FILLED D%d: %s -> \"%s\" · evidence (person): \"%s\"" % (ts, next_d, slot[:70], value[:120], quote[:200]))
            next_d += 1
        else:
            rep = value + " [inferred]"
            ev.append("- [%s] FILLED [inferred]: %s -> \"%s\" · evidence: \"%s\"%s" % (ts, slot[:70], value[:120], quote[:200], note))
        edits.append((m.start(), m.end(), rep))
        applied += 1
    new = text
    for s_, e_, rep in sorted(edits, key=lambda x: -x[0]):
        new = new[:s_] + rep + new[e_:]
    if dlines:
        add = "\n".join(dlines) + "\n"
        i2 = new.find("\n## ROUTED NOTES")
        new = (new[:i2 + 1] + add + "\n" + new[i2 + 1:]) if i2 >= 0 else (new.rstrip("\n") + "\n" + add)
    if new != text:
        left = set(new.splitlines())
        lost = [l for l in old_confirmed if l not in left and l not in replaced_conf]
        if lost:   # refuse the whole write: a confirmed line would change
            ev.append("- [%s] ABORTED: the edit would have changed a confirmed line: %s" % (ts, lost[0][:100]))
            new, applied, packet_applied, packet_files = text, 0, 0, {}   # guard tripped: nothing at all is written
            guard_lost = True
    if new != text:
        _write_atomic(path, new)
    for fname, ptext in sorted(packet_files.items()):
        if ptext != _read(os.path.join(wd, fname)):
            _write_atomic(os.path.join(wd, fname), ptext)
    if ev:
        evp = os.path.join(wd, "spec-evidence.md")
        head = "" if os.path.isfile(evp) else "# Spec evidence\n\nWritten by the spec writer: every line it added to draft-spec.md and the packet, with the quote that supports it.\n\n"
        with open(evp, "a", encoding="utf-8") as f:
            f.write(head + "\n".join(ev) + "\n")
    rejected = sum(1 for e in ev if "REJECTED" in e or "ABORTED" in e)
    saved = applied + packet_applied
    # B4: three states. A write that saved nothing because of rejects, a tripped guard or an unreadable reply is a FAILURE,
    # and the transcript offset stays where it was so the next run reads those turns again.
    if saved == 0 and (rejected or unparsed or guard_lost):
        why = ("the reply could not be read" if unparsed else
               "a confirmed line would have changed" if guard_lost else
               "%d record(s) rejected, none could be applied" % rejected)
        return "FAILED: %s (see spec-evidence.md); the answers are kept for the next try" % why
    if new_off:
        try:
            _write_atomic(_p("offset", sid), str(new_off))
        except OSError:
            pass
    return "APPLIED spec=%d packet=%d (skipped %d) rejected=%d" % (applied, packet_applied, packet_skipped, rejected)


# ------------------------------------------------------------------ 2f: the fresh questioner

Q_END = "QUESTIONS-END"
Q_FAILED = "NONE (the fresh read failed)"


def build_questions(plug, wd, out_file, findings=""):
    """The questioner's prompt: the SAVED draft spec (whole, capped) and, at 4.3, the checked findings. Never the
    conversation. Returns 'OK' or 'FAIL <reason>'."""
    if not wd or not os.path.isabs(wd) or not os.path.isdir(wd):
        return "FAIL no run folder to read the spec from (%r)" % (wd,)
    spec = _read(os.path.join(wd, "draft-spec.md"))
    if not spec:
        return "FAIL the draft spec is missing or empty (%s)" % os.path.join(wd, "draft-spec.md")
    if len(spec) > 90000:
        spec = spec[:90000] + "\n(spec cut for length)"
    extra = ""
    if findings:
        t = _read(findings)
        if t:
            extra = "\n\n=== THE CHECKED FINDINGS (4.3) ===\n%s" % t[:20000]
    prompt = ("From the draft spec's open blanks and unconfirmed lines only, return the next up to six leveraged "
              "questions, most load-bearing first, each with RECOMMENDATION / CONFIDENCE / LOAD-BEARING in the house "
              "style's shape — or the single line NOTHING. Never use any conversation; the only sources are below. "
              "End your reply with the line %s on its own last line.\n\n=== THE SAVED DRAFT SPEC ===\n%s%s\n"
              % (Q_END, spec, extra))
    _write_atomic(out_file, prompt.replace("/skill-builder", "skill-builder"))
    return "OK"


def questions_out(reply_file, out_file):
    """The questioner's reply -> the questions file the gate reads: the reply without its QUESTIONS-END marker, or
    the failure line when the marker is missing or the reply is empty."""
    reply = _read(reply_file)
    body = reply.split(Q_END)[0].strip()
    if not body or Q_END not in reply:
        body = Q_FAILED
    _write_atomic(out_file, body + "\n")
    return "FAILED" if body == Q_FAILED else "OK"


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    hooks = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plug = _plug(hooks)
    try:
        if cmd == "stop" and len(argv) > 2:
            stop_check(hooks, argv[2], sys.stdin.read())
        elif cmd == "flag-wd":
            print(flag_wd(argv[2]))
        elif cmd == "active":   # active <sid>: exit 0 when a live run is flagged for this session (else clear the flag)
            wd = flag_wd(argv[2])
            if wd and os.path.isdir(wd) and run_active(hooks, wd, argv[2]):
                return 0
            deactivate(argv[2])
            return 1
        elif cmd == "build-prompt":     # build-prompt <payload> <prompt out> <sid>
            print(build_prompt(plug, argv[2], argv[3], argv[5] if len(argv) > 5 else flag_wd(argv[4]), argv[4]))
        elif cmd == "apply":            # apply <reply> <sid> [new offset] [run folder: spec_write.sh passes the one captured at launch]
            print(apply_reply(plug, argv[2], argv[5] if len(argv) > 5 else flag_wd(argv[3]), argv[3], argv[4] if len(argv) > 4 else ""))
        elif cmd == "report":
            print(report(hooks, argv[2]) or "")
        elif cmd == "gate":   # gate <sid>: line 1 = the screen line, line 2 = the model line ("-" = none)
            sc, ml = gate(argv[2])
            print(sc or "-")
            print(ml or "-")
        elif cmd == "build-questions":   # build-questions <sid> <prompt out> [findings file]
            print(build_questions(plug, flag_wd(argv[2]), argv[3], argv[4] if len(argv) > 4 else ""))
        elif cmd == "questions-out":     # questions-out <reply file> <questions out>
            print(questions_out(argv[2], argv[3]))
        else:
            print("usage: sb_spec.py stop|flag-wd|active|build-prompt|apply|report|gate|build-questions|questions-out ...", file=sys.stderr)
            return 2
    except Exception as e:
        print("sb_spec.py: %s: %s" % (type(e).__name__, str(e)[:200]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
