#!/usr/bin/env python3
"""sb_spec.py -- the skill builder's back room in code (round 2b, Y; reshaped by 2c): the spec REPORTER (B2), the spec WRITER's
mechanics (B3) and the BARS from code (B4). Imported by observe_ups.sh (the one-line report), sb_start.py (the per-turn bars and
the writer's input) and sb_waves.py; run as `python3 sb_spec.py stop <sid>` by end_of_turn_checks.sh (the cheap Stop check: the
bars, the files read, and the wave receipts), and as `apply` by the in-turn WRITER (a haiku Agent helper that the wave list
sends; see waves.json). No AI in this file.

WHY (2c): the background writer (detached, locks, pids, a WAIT/SAVED gate) was dropped. The writer now runs IN THE TURN as a
wave of the talking AI's helpers (lib/sb_waves.py hands the list over, code checks the receipts after the turn). What stays here
is what code must do and an AI must not: build the writer's input from the person's verbatim words (build_turn_input), apply the
writer's records with every guard (apply_reply: blank and unconfirmed lines only, newest wins on a confirmed line with the old one
kept marked "(superseded <date>)", [inferred] added by code, one atomic rename, a questions-free FAILED when nothing applied),
count the draft spec (scripts/completion.py), and hand over the bars.

State (all under ~/.claude/run/observe/, per session; never in the plugin or the person's notes):
  spec-sess-<sid>.flag   wd=<run folder>      present = a skill-builder run is live in this session (the only file test
                                              the Stop and prompt hooks make; removed when the run is complete/abandoned)
  spec-state-<sid>.json  hash and size of draft-spec.md at the last report (the baseline for "changed / not changed this turn"),
                       plus "decided": did the person's prompt at that report look like a decision (DECISION_RE)
  spec-given-<sid>.json  the bar lines handed to the model this turn (the Stop check compares the reply with them)
  spec-mismatch-<sid>.txt / spec-read-<sid>.txt   one-shot notes for the next turn's line
  spec-wave-<sid>.json   the pointer to this turn's wave folder (lib/sb_waves.py), read by the Stop check
In the run folder: draft-spec.md (written by the in-turn writer's apply, by the step-5 spec updater and by the compiler, never
two at once: the waves are sequential), spec-evidence.md (the quoted evidence), and waves/<turn id>/ (every helper's output).
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
    "> **Saved by the in-turn writer** (a small-tier helper in the turn's first wave; its records are applied by code, "
    "system/hooks/lib/sb_spec.py apply, 2c 2026-11-26) from what the person just decided, and brought fully up to date by "
    "step 5's spec updater; the main window never writes this file. Only lines the round gives evidence for are filled; each "
    "new line ends with the inferred mark unless the person said or approved it; a confirmed line is never deleted, and a "
    "replaced line is kept beneath marked (superseded <date>). Evidence, quoted, is in spec-evidence.md beside this file.\n\n"
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
        if not sid:
            return
        os.makedirs(od(), exist_ok=True)
        ensure_spec(plug, wd)
        _write_atomic(flag_path(sid), "wd=%s\nat=%d\n" % (wd, int(time.time())))
        _write_atomic(_p("state", sid, ".json"), json.dumps(_state_of(plug, wd)))
    except Exception as e:
        _log("activate (draft spec / flag)", e)


def deactivate(sid):
    # the wave pointer (spec-wave-<sid>.json) is NOT removed here: the Stop check of the very turn that completed the run still reads it
    for kind, ext in (("sess", ".flag"), ("state", ".json"), ("given", ".json"), ("mismatch", ".txt"), ("read", ".txt")):
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
        extra = ""
        if not prev or prev.get("hash") == now["hash"]:
            line = "📋 Spec: not changed this turn" + extra
            if prev and prev.get("decided"):
                line = "⚠ You decided something this turn; the spec did not change. " + line
            return line
        return "📋 Spec: changed this turn" + extra
    except Exception as e:
        return "📋 Spec line unavailable: %s" % _log("spec report", e)[:160]


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
    """Cheap Stop step: (0) the wave receipts (lib/sb_waves.py: every job this turn's list handed over left its file?), (1) does a
    bar in the reply match what code gave or gives now? (2) which files were read this turn?"""
    try:
        import sb_waves
        try:
            tp = json.loads(payload_text).get("transcript_path") or ""
        except ValueError:
            tp = ""
        sb_waves.check(sid, tp)   # never raises; writes the one-shot warning the next turn's list carries
    except Exception as e:
        _log("wave receipt check", e)
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

def _last_reply(tp, cap=6000):
    """The window's own words in its LAST reply (every assistant text after the transcript's final person message): the
    questions the person is now answering. The current prompt is not in the transcript yet when the prompt hook runs."""
    SR = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
    entries = _transcript_entries(tp) if tp else []
    last = max([i for i, d in enumerate(entries) if _is_prompt(d)] or [-1])
    texts = []
    for d in entries[last + 1:]:
        if d.get("type") == "assistant" and not d.get("isSidechain"):
            t = SR.sub("", _text_of((d.get("message") or {}).get("content"))).strip()
            if t:
                texts.append(t)
    body = "\n\n".join(texts)
    return body[-cap:] if len(body) > cap else body


_WRITER_BRIEF_RELS = (".claude/skills/skill-builder/prompts/subagents/spec-writer.md",
                      "skills/skill-builder/prompts/subagents/spec-writer.md")


def _writer_brief(plug):
    for rel in _WRITER_BRIEF_RELS:
        p = os.path.join(plug, rel)
        if os.path.isfile(p):
            return p
    return ""
PACKET_CAP = 20000
CARRY_MAX = 3   # earlier turns whose save never applied are carried into this turn's input (their words must not be lost)


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


def _unsaved_turns(waves_dir, this):
    """[(turn folder name, person text)] of earlier turns that handed the writer an input but whose save never applied (no receipt,
    or one that starts FAILED), oldest first, at most CARRY_MAX. A retry therefore needs no transcript offset and no state."""
    out = []
    try:
        names = sorted((d for d in os.listdir(waves_dir) if os.path.isfile(os.path.join(waves_dir, d, "writer-input.md"))
                        and d != this), key=lambda d: os.path.getmtime(os.path.join(waves_dir, d, "writer-input.md")))
    except OSError:
        return out
    for d in names:
        rcpt = _read(os.path.join(waves_dir, d, "writer.md.applied")).strip()
        if rcpt and not rcpt.startswith("FAILED"):
            continue
        text = _read(os.path.join(waves_dir, d, "person.md"))
        if text.strip():
            out.append((d, text.split("\n\n", 1)[-1].strip()))
    return out[-CARRY_MAX:]


def build_turn_input(plug, wd, sid, td, prompt, tp, run_dir=""):
    """THE WRITER'S WHOLE INPUT for this turn, written by code into the turn folder (<td>/writer-input.md): the writer's brief
    (everything above its test card), the draft spec, the packet, and the evidence: the window's last reply (the questions being
    answered) and the person's words VERBATIM, plus any earlier turn whose save never applied. Also <td>/turn.json's sibling
    <td>/evidence.json (the person's texts, which apply_reply checks every quoted line against). Returns 'OK' or 'FAIL <reason>'."""
    if not wd or not os.path.isabs(wd) or not os.path.isdir(wd):
        return "FAIL no run folder (%r)" % (wd,)
    try:
        bp = _writer_brief(plug)
        brief = _read(bp) if bp else ""
        if "— TEST CARD —" in brief:
            brief = brief.split("— TEST CARD —")[0].rstrip()
        if not brief:
            return "FAIL the writer brief is missing (prompts/subagents/spec-writer.md)"
        spec = _read(os.path.join(wd, "draft-spec.md"))
        if not spec:
            return "FAIL the draft spec is missing or empty (%s)" % os.path.join(wd, "draft-spec.md")
        if len(spec) > 90000:
            spec = spec[:90000] + "\n(spec cut for length)"
        carried = _unsaved_turns(os.path.dirname(td), os.path.basename(td))
        turns = []
        for d, text in carried:
            turns.append(("PERSON", text))   # an earlier answer that was never saved: its own words, as that turn recorded them
        reply = _last_reply(tp)
        if reply:
            turns.append(("SKILL", reply))
        turns.append(("PERSON", prompt))
        body = "\n\n".join("%s: %s" % (w, t) for w, t in turns)
        cap = int(os.environ.get("SPEC_TRANSCRIPT_CAP", "20000"))
        if len(body) > cap:
            body = "(earlier text cut)\n" + body[-cap:]
        prompt_text = ("At most %d records in your reply, `---` between records, and END-WRITE on its own last line.\n\n%s"
                       "\n\n=== THE DRAFT SPEC (current) ===\n%s\n\n%s\n\n=== THE ROUND\u2019S TURNS (the only evidence) ===\n%s\n"
                       % (MAX_EDITS, brief, spec, _packet_brief(wd), body))
        # the nested model session runs the same hooks: no literal slash-command may appear in its prompt
        _write_atomic(os.path.join(td, "writer-input.md"), prompt_text.replace("/skill-builder", "skill-builder"))
        _write_atomic(os.path.join(td, "evidence.json"), json.dumps(
            {"person": [t for w, t in turns if w == "PERSON"], "all": body, "carried": [d for d, _ in carried]}))
    except (OSError, ValueError) as e:
        return "FAIL %s: %s" % (type(e).__name__, e)
    return "OK"


def _norm(s):
    return " ".join(s.split()).lower()


def apply_and_mark(plug, reply_file, wd, sid):
    """The writer's one command: apply the records, then write the RECEIPT <reply file>.applied (one line, written by code, so
    the AI cannot forge it): 'APPLIED spec=N packet=M ...' or 'FAILED: <reason>'. A success also settles every earlier turn this
    input carried (their words were in this write), so they are not carried again."""
    try:
        res = apply_reply(plug, reply_file, wd, sid)
    except Exception as e:
        res = "FAILED: %s" % _log("apply", e)[:200]
    res = " ".join(str(res).split())
    try:
        _write_atomic(reply_file + ".applied", res + "\n")
        if res.startswith("APPLIED"):
            ev = _json(os.path.join(os.path.dirname(os.path.abspath(reply_file)), "evidence.json")) or {}
            root = os.path.dirname(os.path.dirname(os.path.abspath(reply_file)))
            for d in ev.get("carried") or []:
                _write_atomic(os.path.join(root, d, "writer.md.applied"), "CARRIED into %s: %s\n"
                              % (os.path.basename(os.path.dirname(os.path.abspath(reply_file))), res))
    except OSError as e:
        res = "FAILED: the receipt could not be written (%s)" % e
    return res


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


def apply_reply(plug, reply_file, wd, sid):
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
    turn = _json(os.path.join(os.path.dirname(os.path.abspath(reply_file)), "evidence.json")) or {}   # written by build_turn_input
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
            if was_conf and qn not in persons:   # audit S5: a decision the person confirmed is never demoted by words that are not theirs
                ev.append("- [%s] REJECTED replace (a confirmed line is replaced only when the quote is in the person's words): %s" % (
                    ts, r["REPLACE"][:80]))
                used.discard(o)
                continue
            lab = re.match(r"^\s*(?:[-*+]|\d+[.)])?\s*(\*\*[^*\n]+\*\*[:：]?\s*)", l)   # audit S4: the old line's bold label stays
            if lab and not newv.lstrip().startswith("**"):
                newv = lab.group(1) + newv
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
    # B4: three states. A write that saved nothing because of rejects, a tripped guard or an unreadable reply is a FAILURE
    # (its turn keeps no receipt, so the next turn's input carries those words again).
    if saved == 0 and (rejected or unparsed or guard_lost):
        why = ("the reply could not be read" if unparsed else
               "a confirmed line would have changed" if guard_lost else
               "%d record(s) rejected, none could be applied" % rejected)
        return "FAILED: %s (see spec-evidence.md); the answers are kept for the next try" % why
    return "APPLIED spec=%d packet=%d (skipped %d) rejected=%d" % (applied, packet_applied, packet_skipped, rejected)


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
        elif cmd == "apply" and len(argv) > 4:   # apply <records file> <sid> <run folder>: the in-turn writer's one command
            print(apply_and_mark(plug, argv[2], argv[4], argv[3]))
        elif cmd == "report":
            print(report(hooks, argv[2]) or "")
        else:
            print("usage: sb_spec.py stop <sid> | flag-wd <sid> | active <sid> | apply <records file> <sid> <run folder> | report <sid>", file=sys.stderr)
            return 2
    except Exception as e:
        print("sb_spec.py: %s: %s" % (type(e).__name__, str(e)[:200]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
