#!/usr/bin/env python3
"""stage_runner — the stateful step runner for long (multi-stage) skills. [Parts Library · Tier A · 4P.0a]

WHEN: a skill has an ordered set of stages (a stage card) and one session walks them in order.
WHAT: ONE part that owns the whole run: the stage card (JSON), the order of stages, the
      hash-chained run record (ONLY this part writes it), the damaged-record refusal,
      next/back, and the status line. Per-stage CONTENT checks are handed to the sibling
      gate parts -- forbidden_content.py (forbid), section_present.py (require_sections),
      order_lint.py (order), phase_gate.py (a phase contract) -- called as subprocesses,
      never re-implemented here.
WHY: the skill being run must never choose its own next stage or write its own record.
      "Hallucinated success" is the most-regretted failure in production LLM systems, and
      a runner is exactly the place it would enter: the actor grading its own stage order.
      The design follows the proven private rig (card runner + hash-chained append-only
      record + damaged exit), re-built fresh for the plugin with NO personal paths: every
      path comes from arguments (--card, --workdir) or the working directory -- nothing is
      hard-coded, no launcher, no names. Hook rows and slash-command registration for a
      specific skill are wired at skill build time (plan 4P.5) through the plugin's
      register, never by hand; this part supplies the machinery those rows call.

WHAT IT OWNS
  1. STAGE CARD -- a JSON file naming the skill's stages (id, mode talk|alone, prompt file,
        out path, checks). The card lives with the skill; the runner only reads it.
  2. ORDER -- stage N+1 is reachable only through a verified pass on stage N. An advance
        whose stage fails its checks records fail and refuses (exit 3); no sequence of
        calls can produce a pass for stage N+1 while N is unmet.
  3. RECORD -- record.jsonl, append-only, hash-chained (GENESIS = 64 zeros; sha256 over
        prev + canonical JSON). The whole chain is re-verified on EVERY read. Only this
        part writes it; the AI never does. State is DERIVED from the record, never stored.
  4. DAMAGED RECORD -- bad JSON, a seq gap, a chain mismatch, or a torn tail (missing
        final newline) makes the record DAMAGED: `verify` reports it (exit 6) and every
        other command refuses without writing. The run stops; a person looks.
  5. NEXT/BACK -- advance (verify, stamp, hand over) and back (re-open the previous
        stage with a fresh code word). Back after a pass means the stage's code-word line
        must be updated to the fresh word before it can pass again.
  6. STATUS LINE -- `statusline` reads Claude Code's status payload, records context fill,
        and prints where the run is.

⛔ DECLARED UNCHECKABLE -- the content checks cannot prove the stage's OUTPUT is real work.
      What they prove: the declared headings/words/absences are present as text in the
      stage's own output file, and the delegated gates' own guarantees hold (declaration-
      vs-mention, ordering, phase contracts). What they CANNOT prove: that the text is the
      stage's actual deliverable rather than words typed to satisfy the checks. Same
      terminal bound phase_gate.py declares for its `requires` -- no trace independent of
      the artifact exists. Do not patch with a "substantive?" heuristic; that was built,
      measured and reverted (see phase_gate's header).

USAGE AND EXIT CODES -- the ONE list is system/templates/skill-template/RUNNER.md (commands,
  events, the person-turn rule, the alone/talk difference, exit codes). RUNNER.md and this
  docstring point at each other; change the list THERE. In short: start, status, check,
  advance, back, person-turn, resume, abandon, snooze, recover, verify, statusline, --selftest;
  exits 0 OK · 2 usage/bad choice · 3 check failed / no person turn / taken over ·
  4 nothing to do / repeat turn · 5 no run · 6 damaged · 7 dangling.

CARD FORMAT (JSON; lives with the skill, e.g. system/templates/skill-template/card.template.json)
  { "skill": "<name>", "stop_limit": 3,
    "stages": [ { "id": "<kebab>", "mode": "talk|alone",
        "prompt": "prompts/01-<id>.md",          // relative to the card; optional
        "out": "out/01-<id>.md",                 // relative to the run dir
        "extra": ["out/..."],                    // additional required files; optional
        "inputs": ["out/..."],                   // what this stage reads; default = previous stage's out
        "checks": {
          "headings": ["## ..."],                // each must appear as a line exactly
          "min_words": 40,                       // prose words under headings, excluding the code word
          "code_word": true,                     // a line `Code word: <word>` whose hash matches the handed-out word
          "forbid": [ ...forbidden_content rules... ],        // via forbidden_content.py
          "require_sections": [ ...section_present rules... ], // via section_present.py
          "order": [ ...order_lint rules... ],                 // via order_lint.py
          "phase_gate": {"phase": 2, "contract": {...}}        // via phase_gate.py
        } } ] }
"""

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GENESIS = "0" * 64
ALPHA = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
MARKER = ".stage-runner.json"
RUNNER = "stage_runner.py"
# delegated check parts: card key -> part filename
DELEGATES = {
    "forbid": "forbidden_content.py",
    "require_sections": "section_present.py",
    "order": "order_lint.py",
    "phase_gate": "phase_gate.py",
}
PROMPT_VARS = ("CODE", "OUT", "PREV", "ID", "MODE", "N", "TOTAL", "SKILL")

OK, USAGE, CHECKFAIL, NOTHING, NORUN, DAMAGED, DANGLING = 0, 2, 3, 4, 5, 6, 7


class Damaged(Exception):
    """The run record failed chain verification."""


class PartMissing(Exception):
    """A card declares a check whose delegate part is not beside this file."""


class CannotEvaluate(Exception):
    """A delegate part could not evaluate (fail-closed)."""


# ---------------------------------------------------------------- record
def _hash(prev, line):
    body = json.dumps(line, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((prev + "\n" + body).encode()).hexdigest()


def load_record(run_dir):
    """Verify the whole chain; any damage raises Damaged. Read-only; the chain is
    re-verified on every read -- state is never trusted from a stored copy."""
    p = os.path.join(run_dir, "record.jsonl")
    if not os.path.exists(p):
        raise Damaged("record.jsonl missing")
    raw = open(p, "rb").read()
    if raw and not raw.endswith(b"\n"):
        raise Damaged("torn tail: last line has no newline")
    lines, prev = [], GENESIS
    body_lines = raw.decode("utf-8", "replace").split("\n")[:-1] if raw else []
    for i, ln in enumerate(body_lines):
        try:
            o = json.loads(ln)
            h = o.pop("hash")
            assert o["seq"] == i and o["prev"] == prev and _hash(prev, o) == h
        except Exception:
            raise Damaged("line %d damaged (bad JSON, gap, or chain mismatch)" % (i + 1))
        o["hash"] = h
        lines.append(o)
        prev = h
    if not lines:
        raise Damaged("record.jsonl is empty")
    if lines[0]["event"] != "start":
        raise Damaged("the first record line is not start")
    try:
        derive(lines)          # the replay rule: lines must make sense in order, not just chain
    except Damaged:
        raise
    except Exception:
        raise Damaged("record lines do not replay (a line has the wrong shape)")
    return lines


_depth = {}


@contextlib.contextmanager
def locked(run_dir):
    if _depth.get(run_dir):
        yield
        return
    f = open(os.path.join(run_dir, ".lock"), "w", encoding="utf-8")
    fcntl.flock(f, fcntl.LOCK_EX)
    _depth[run_dir] = 1
    try:
        yield
    finally:
        _depth[run_dir] = 0
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def append(run_dir, event, stage=None, data=None, run=None):
    """The ONLY writer of record lines. Under lock, over a freshly verified chain."""
    with locked(run_dir):
        rec = os.path.join(run_dir, "record.jsonl")
        lines = load_record(run_dir) if os.path.exists(rec) else []
        prev = lines[-1]["hash"] if lines else GENESIS
        o = {"seq": len(lines), "t": time.time(), "prev": prev, "event": event,
             "run": run or (lines[0]["run"] if lines else os.path.basename(run_dir)),
             "stage": stage, "data": data or {}}
        o["hash"] = _hash(prev, o)
        fd = os.open(os.path.join(run_dir, "record.jsonl"),
                     os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, (json.dumps(o, sort_keys=True) + "\n").encode())
            os.fsync(fd)
        finally:
            os.close(fd)
        return o


def derive(lines):
    """Run state FROM the record, never from a stored copy. Also the REPLAY RULE: a forward
    handover (`intent`) needs a `pass` of the step it leaves since that step opened; a `back`
    handover needs its `back` line; `done` needs its `intent`; `complete` needs the run to be at
    COMPLETE. Anything else raises Damaged (a rebuilt chain without passes is not a real run)."""
    s = {"cur": None, "code": None, "complete": False, "pending": None,
         "run": None, "card": None, "skill": None, "fails": 0, "card_sha": None,
         "persons": {}, "superseded": {}, "snoozed": False, "abandoned": False,
         "passed": False, "backed": None, "skipped": []}
    for l in lines:
        e, d = l["event"], l["data"]
        if s["abandoned"]:
            raise Damaged("a record line after abandoned (a run set aside cannot move)")
        if e == "start":
            s.update(run=l["run"], card=d["card"], skill=d.get("skill"),
                     cur=d["first"], code=d.get("code_hash"), card_sha=d.get("card_sha"),
                     passed=False, backed=None)
        elif e == "person":
            s["persons"][d["turn"]] = {"cmd": d["cmd"], "consumed": False}
            s["snoozed"] = False
        elif e == "pass":
            if l["stage"] != s["cur"]:
                raise Damaged("a pass for a step that is not the open step")
            s["passed"] = True
            if d.get("skipped"):
                s["skipped"].append(l["stage"])
            _consume(s, d)
        elif e == "back":
            s["backed"] = (l["stage"], d.get("to"))
            _consume(s, d)
        elif e in ("handover",):
            _consume(s, d)
        elif e == "intent":
            if l["stage"] != s["cur"]:
                raise Damaged("a handover from a step that is not the open step")
            if d.get("back"):
                if s["backed"] != (l["stage"], d.get("to")):
                    raise Damaged("a back handover without its back line")
            elif not s["passed"]:
                raise Damaged("a forward handover without a pass of the step it leaves")
            s["pending"] = l
        elif e == "done":
            if not s["pending"] or s["pending"]["data"].get("to") != d.get("to"):
                raise Damaged("a done without its handover intent")
            s.update(pending=None, cur=d["to"], code=d.get("code_hash") or None,
                     passed=False, backed=None)
        elif e == "fail":
            s["fails"] += 1
            _consume(s, d)
        elif e == "complete":
            if s["cur"] != "COMPLETE":
                raise Damaged("complete without a pass of the last step")
            s["complete"] = True
        elif e == "reissue":
            if s["code"]:
                s["superseded"][s["code"]] = l["t"]
            s.update(code=d.get("code_hash"), snoozed=False)
        elif e == "abandoned":
            s["abandoned"] = True
        elif e == "snoozed":
            s["snoozed"] = True
    return s


def _consume(s, d):
    """A person line is used up by the first advance/back that names its turn, whatever the result."""
    t = d.get("turn")
    if t is not None and t in s["persons"]:
        s["persons"][t]["consumed"] = True


def check_order(lines, card):
    """Replay against the card's step order (needs the card): forward handovers go exactly one
    step on (or to COMPLETE from the last step); back handovers go exactly one step back.
    Also the PERSON-TURN replay rule: a pass on a talk step must carry data.turn naming a
    person{cmd:next} line before it, and every back must name a person{cmd:back}; the pass
    and the back are the anchors -- an intent/done leaving a talk step needs its pass (the
    replay rule in derive), so no forward move from a talk step can exist without one."""
    persons = {}
    for l in lines:
        e, d = l["event"], l["data"]
        if e == "person":
            persons[d["turn"]] = {"cmd": d.get("cmd"), "used": False}
            continue
        if e == "back":
            p = persons.get(d.get("turn"))
            if not p or p["used"] or p["cmd"] != "back":
                raise Damaged("a back moved a step without a person turn")
            p["used"] = True
            continue
        if e != "pass":
            continue
        i = stage_index(card, l["stage"])
        if i < 0 or card["stages"][i].get("mode", "talk") != "talk":
            continue
        p = persons.get(d.get("turn"))
        if not p or p["used"] or p["cmd"] != "next":
            raise Damaged("a talk step moved without a person turn")
        p["used"] = True
    for l in lines:
        if l["event"] != "intent":
            continue
        d = l["data"]
        i, to = stage_index(card, l["stage"]), d.get("to")
        if i < 0:
            raise Damaged("a handover from a step the card does not have")
        if d.get("back"):
            ok = i > 0 and to == card["stages"][i - 1]["id"]
        elif to == "COMPLETE":
            ok = i == len(card["stages"]) - 1
        else:
            ok = i + 1 < len(card["stages"]) and to == card["stages"][i + 1]["id"]
        if not ok:
            raise Damaged("a handover that skips a step")


def card_sha(path, card):
    """sha256 of card.json plus every prompt file, in stage order."""
    h = hashlib.sha256()
    h.update(open(path, "rb").read())
    for st in card["stages"]:
        if st.get("prompt"):
            h.update(b"\0" + st["prompt"].encode() + b"\0")
            h.update(open(os.path.join(card["_dir"], st["prompt"]), "rb").read())
    return h.hexdigest()


# ---------------------------------------------------------------- card, run discovery
def load_card(path):
    """Load and sanity-check a stage card. Raises ValueError on a shape the runner
    cannot honour -- before anything is written."""
    if not os.path.isfile(path):
        raise ValueError("card not found: %r" % path)
    c = json.loads(open(path, encoding="utf-8").read())
    if not isinstance(c, dict) or not isinstance(c.get("stages"), list) or not c["stages"]:
        raise ValueError("card must hold a non-empty 'stages' list")
    ids = set()
    for i, s in enumerate(c["stages"]):
        if not isinstance(s, dict) or not s.get("id"):
            raise ValueError("stage %d has no 'id'" % i)
        if s["id"] in ids:
            raise ValueError("duplicate stage id %r" % s["id"])
        ids.add(s["id"])
        if s.get("mode", "talk") not in ("talk", "alone"):
            raise ValueError("stage %r: mode must be 'talk' or 'alone'" % s["id"])
        if "optional" in s and not isinstance(s["optional"], bool):
            raise ValueError("stage %r: 'optional' must be true or false (a boolean)" % s["id"])
        if s.get("optional") and s.get("mode", "talk") == "alone":
            raise ValueError("stage %r: an ALONE step cannot be 'optional' (only a talk step "
                             "may be skipped by the person)" % s["id"])
        for rel in [s.get("out")] + list(s.get("extra", [])):
            if not rel:
                raise ValueError("stage %r has no 'out'" % s["id"])
            if os.path.isabs(rel) or ".." in rel.split(os.sep):
                raise ValueError("stage %r: output path %r must be relative to the run dir"
                                 % (s["id"], rel))
        if s.get("prompt"):
            pp = os.path.join(os.path.dirname(os.path.abspath(path)), s["prompt"])
            if not os.path.isfile(pp):
                raise ValueError("stage %r: prompt file not found: %r" % (s["id"], pp))
        ck = s.get("checks", {})
        for key in DELEGATES:
            want = dict if key == "phase_gate" else list
            if key in ck and not isinstance(ck[key], want):
                raise ValueError("stage %r: checks.%r has the wrong shape (want %s)"
                                 % (s["id"], key, want.__name__))
    c["_dir"] = os.path.dirname(os.path.abspath(path))
    return c


def find_marker(start):
    """(workdir, marker path) walking up from `start`, without reading it, or None."""
    d = os.path.abspath(start or os.getcwd())
    for _ in range(8):
        m = os.path.join(d, MARKER)
        if os.path.isfile(m):
            return d, m
        if os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    return None


def find_run(start):
    """(workdir, run_dir) walking up from `start`, or None. A marker that is valid JSON but not
    an object (or whose run_dir is not text) raises Damaged -- never a traceback."""
    d = os.path.abspath(start or os.getcwd())
    for _ in range(8):
        m = os.path.join(d, MARKER)
        if os.path.isfile(m):
            try:
                j = json.load(open(m, encoding="utf-8"))
                if not isinstance(j, dict) or not isinstance(j.get("run_dir"), str):
                    raise Damaged("the run marker %s is not a JSON object naming a run folder" % m)
                run_dir = j["run_dir"]
                if not os.path.isabs(run_dir):
                    run_dir = os.path.join(d, run_dir)
                rr, rw = os.path.realpath(run_dir), os.path.realpath(d)
                if rr != rw and not (rr + os.sep).startswith(rw + os.sep):
                    raise Damaged("the run folder %s sits outside the marker's folder" % m)
                return d, run_dir
            except (OSError, ValueError, KeyError) as e:
                sys.stderr.write("stage_runner: unreadable marker %s: %r (hooks stay inert)\n"
                                 % (m, e))
                return None
        if os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)
    return None


def stage_index(card, sid):
    for i, s in enumerate(card["stages"]):
        if s["id"] == sid:
            return i
    return -1


def chash(w):
    return hashlib.sha256(w.encode()).hexdigest()[:16]


def new_code():
    return "RUN-" + "".join(secrets.choice(ALPHA) for _ in range(6))


# ---------------------------------------------------------------- delegated checks
def _delegate(part, args, stdin=None):
    """Run one sibling gate part. Fail-closed on every bad outcome."""
    p = os.path.join(HERE, part)
    if not os.path.isfile(p):
        raise PartMissing(part)
    proc = subprocess.run([sys.executable, p] + args, input=stdin,
                          capture_output=True, text=True)
    if proc.returncode == 2:
        raise CannotEvaluate("%s could not evaluate: %s" % (part, proc.stderr.strip()[:300]))
    return proc


def delegated_checks(stage, text, run_dir):
    """Problems from the delegate parts named by the card. Raises PartMissing /
    CannotEvaluate (both fail closed, exit 2)."""
    problems = []
    ck = stage.get("checks", {})
    with tempfile.TemporaryDirectory() as td:
        if ck.get("forbid"):
            rp = os.path.join(td, "rules.json")
            json.dump(ck["forbid"], open(rp, "w", encoding="utf-8"))
            proc = _delegate(DELEGATES["forbid"], ["--rules", rp, "--stdin", "--json"], stdin=text)
            for h in json.loads(proc.stdout)["hits"]:
                problems.append({"code": "forbid", "detail": "forbidden content [%s] line %d: %s"
                                 % (h["id"], h["line"], h["evidence"])})
        if ck.get("require_sections"):
            rp = os.path.join(td, "rules.json")
            json.dump(ck["require_sections"], open(rp, "w", encoding="utf-8"))
            ap_ = os.path.join(td, "artifact.md")
            open(ap_, "w", encoding="utf-8").write(text)
            proc = _delegate(DELEGATES["require_sections"], ["--rules", rp, "--artifact", ap_, "--json"])
            for v in json.loads(proc.stdout).get("verdicts", []):
                if v.get("verdict") != "PRESENT":
                    problems.append({"code": "require_sections",
                                     "detail": "required section [%s]: %s" % (v.get("id"), v.get("verdict"))})
        if ck.get("order"):
            rp = os.path.join(td, "rules.json")
            json.dump(ck["order"], open(rp, "w", encoding="utf-8"))
            ap_ = os.path.join(td, "artifact.md")
            open(ap_, "w", encoding="utf-8").write(text)
            proc = _delegate(DELEGATES["order"], ["--rules", rp, "--artifact", ap_, "--json"])
            for v in json.loads(proc.stdout).get("verdicts", []):
                if v.get("verdict") not in ("ORDERED", "NOT_APPLICABLE"):
                    problems.append({"code": "order", "detail": "ordering [%s]: %s"
                                     % (v.get("id"), v.get("verdict"))})
        if isinstance(ck.get("phase_gate"), dict):
            spec = ck["phase_gate"]
            cp = os.path.join(td, "contract.json")
            json.dump(spec.get("contract", {}), open(cp, "w", encoding="utf-8"))
            ap_ = os.path.join(td, "artifact.md")
            open(ap_, "w", encoding="utf-8").write(text)
            proc = _delegate(DELEGATES["phase_gate"],
                             ["--contract", cp, "--artifact", ap_, "--phase",
                              str(spec.get("phase", 1)), "--json"])
            v = json.loads(proc.stdout)
            if v.get("verdict") != "PASSED":
                names = "; ".join(m["id"] for m in v.get("missing_requirements", []))
                forb = "; ".join(h["id"] for h in v.get("forbidden_present", []))
                problems.append({"code": "phase_gate", "detail": "phase contract: %s (%s)"
                                 % (v.get("verdict"), names + ("; " if names and forb else "") + forb)})
    return problems


# ---------------------------------------------------------------- own checks
def run_checks(card, stage, run_dir, code_hash, superseded=None):
    """All checks for one stage: the runner's own, then the delegated gates."""
    problems = []
    out = os.path.join(run_dir, stage["out"])
    if not os.path.isfile(out) or os.path.getsize(out) == 0:
        problems.append({"code": "missing_file",
                         "detail": "output file %s is missing or empty" % stage["out"]})
        return problems
    text = open(out, encoding="utf-8", errors="replace").read()
    if not text.strip():
        problems.append({"code": "missing_file",
                         "detail": "output file %s is missing or empty" % stage["out"]})
        return problems
    ck = stage.get("checks", {})
    for h in ck.get("headings", []):
        if not re.search(r"^%s[ \t]*$" % re.escape(h), text, re.M):
            problems.append({"code": "heading",
                             "detail": "missing heading %s (a line exactly: %s)" % (h, h)})
    m = re.search(r"^Code word:\s*(\S+)\s*$", text, re.M)
    if ck.get("code_word") and not (m and chash(m.group(1)) == code_hash):
        when = (superseded or {}).get(chash(m.group(1))) if m else None
        if when is not None:
            problems.append({"code": "taken_over",
                             "detail": "another window took over this run at %s -- stop working on it here"
                                       % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when))})
        else:
            problems.append({"code": "code_word",
                             "detail": "missing or wrong code word (the word handed out for this stage)"})
    body = re.sub(r"^(#+ .*|Code word:.*)$", "", text, flags=re.M)
    nw = len(re.findall(r"\w+", body))
    if nw < ck.get("min_words", 0):
        problems.append({"code": "min_words",
                         "detail": "only %d words of content, need %d" % (nw, ck["min_words"])})
    for ex in stage.get("extra", []):
        ep = os.path.join(run_dir, ex)
        if not os.path.isfile(ep) or os.path.getsize(ep) == 0:
            problems.append({"code": "missing_extra",
                             "detail": "required file %s is missing or empty" % ex})
    problems += delegated_checks(stage, text, run_dir)
    return problems


# ---------------------------------------------------------------- prompts, inputs
def render_prompt(card, run_dir, i, code):
    """The stage's prompt with placeholders filled; a masked copy is kept in the run.
    A stage with no 'prompt' in the card has none to render."""
    s = card["stages"][i]
    if not s.get("prompt"):
        return ""
    t = open(os.path.join(card["_dir"], s["prompt"]), encoding="utf-8").read()
    prev = os.path.join(run_dir, card["stages"][i - 1]["out"]) if i else ""
    vals = {"CODE": code, "OUT": os.path.join(run_dir, s["out"]), "PREV": prev,
            "ID": s["id"], "MODE": s.get("mode", "talk"), "N": str(i + 1),
            "TOTAL": str(len(card["stages"])), "SKILL": card.get("skill", "")}
    for k in PROMPT_VARS:
        t = t.replace("{{%s}}" % k, vals[k])
    os.makedirs(os.path.join(run_dir, "stage"), exist_ok=True)
    mine = "%02d.prompt.md" % (i + 1)
    open(os.path.join(run_dir, "stage", mine), "w", encoding="utf-8").write(
        t.replace(code, "(code word: delivered by the runner, not stored here)"))
    for f_ in os.listdir(os.path.join(run_dir, "stage")):
        if f_.endswith(".prompt.md") and f_ != mine:
            os.remove(os.path.join(run_dir, "stage", f_))
    return t


def stage_inputs(card, i):
    s = card["stages"][i]
    if "inputs" in s:
        return list(s["inputs"])
    return [card["stages"][i - 1]["out"]] if i else []


def inputs_report(card, run_dir, i):
    lines, bad = [], []
    for rel in stage_inputs(card, i):
        p = os.path.join(run_dir, rel)
        txt = open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else ""
        if not txt.strip():                      # missing, 0 bytes, or only whitespace
            lines.append("INPUTS: %s · MISSING" % rel)
            bad.append(rel)
            continue
        n = len(txt.splitlines())
        lines.append("INPUTS: %s · %d line%s" % (rel, n, "" if n == 1 else "s"))
    return lines, bad


def _newest_person(run_dir):
    """The newest person prompt the mover logged, from <run folder>/person.log (one
    prompt_id<TAB>unix_time per line, written by the mover for every person prompt), or None."""
    try:
        with open(os.path.join(run_dir, "person.log"), encoding="utf-8") as f:
            rows = [l.split("\t") for l in f if l.strip()]
    except OSError:
        return None
    if not rows:
        return None
    try:
        return {"id": rows[-1][0].strip(), "t": float(rows[-1][1])}
    except (IndexError, ValueError):
        return None


def _menu_gate(run_dir, lines):
    """The AI's own menu command (resume / abandon / snooze) writes only when the newest
    person prompt in person.log is NEWER than the record's last line and has not already
    been used by another menu command -- each person prompt id may serve exactly ONE menu
    command. Returns (rc, text) to refuse, or None to allow."""
    newest = _newest_person(run_dir)
    used = set()
    for l in lines:
        rec = l["data"].get("person") if isinstance(l["data"], dict) else None
        if isinstance(rec, dict) and isinstance(rec.get("id"), str):
            used.add(rec["id"])
    if not newest:
        return CHECKFAIL, ("stage_runner: no person prompt is logged for this run -- ask the "
                           "person first; nothing was written (exit 3).")
    if newest["id"] in used:
        return CHECKFAIL, ("stage_runner: that person prompt was already used by another menu "
                           "command -- ask the person first; nothing was written (exit 3).")
    if newest["t"] + 1.0 < lines[-1]["t"]:
        return CHECKFAIL, ("stage_runner: the newest person prompt is older than the run's "
                           "last move -- ask the person first; nothing was written (exit 3).")
    return None


MOVER_BODY = ("The mover ran before you saw this, if a [RUN STEP] line is above. "
              "If there is none, the mover didn't run: tell the person.\n")
_OLD_BODIES = {
    "next": ("The runner code already ran before you saw this message. Follow the handover "
             "injected for you this turn. If none was injected, say there is nothing new.\n"),
    "back": ("The runner code already ran before you saw this message. Follow the handover "
             "injected for you this turn. If none was injected, say nothing changed.\n"),
}


def record_pointer(wd):
    """SB-10: tell the mover, per session, where this run folder is, so /next and /back work from a
    window whose cwd is elsewhere (system/tools/run_pointer.sh, over hooks/lib/flag.sh).
    Best effort: a failure here never stops a start; it returns a short reason (empty on success)."""
    sh = os.path.join(HERE, "..", "tools", "run_pointer.sh")
    try:
        r = subprocess.run(["bash", sh, "set", wd], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        print("stage_runner: pointer update failed: %s" % e, file=sys.stderr)
        return "pointer script failed: %s" % (e,)
    if r.returncode != 0:
        out = (r.stderr.strip() or r.stdout.strip()).splitlines()
        reason = out[-1] if out else ("exit %d" % r.returncode)
        print("stage_runner: pointer update failed: %s" % reason, file=sys.stderr)
        return reason
    return ""


def ensure_commands(wd):
    """Write /next and /back as project commands (an unregistered slash command never
    reaches the hooks -- the rig's P3 lesson). Skill hook rows are registered through
    the plugin's register at build time (4P.5); this only covers the two commands.
    A file whose body is the OLD runner text -- or the previous no-flag body -- is
    rewritten to the new body; any other (custom) body is left alone. The front matter
    carries disable-model-invocation: true: the person types these, the AI never runs
    them as tools."""
    cd = os.path.join(wd, ".claude", "commands")
    os.makedirs(cd, exist_ok=True)
    for name, desc in (("next", "move to the next stage of the run"),
                       ("back", "go back and re-open the previous stage")):
        fp = os.path.join(cd, name + ".md")
        new = "---\ndescription: %s\ndisable-model-invocation: true\n---\n%s" % (desc, MOVER_BODY)
        if not os.path.exists(fp):
            open(fp, "w", encoding="utf-8").write(new)
            continue
        olds = ["---\ndescription: %s\n---\n%s" % (desc, MOVER_BODY),
                "---\ndescription: %s\n---\n%s" % (desc, _OLD_BODIES[name])]
        if open(fp, encoding="utf-8").read() in olds:
            open(fp, "w", encoding="utf-8").write(new)


# ---------------------------------------------------------------- actions
def _turn_gate(st, turn, cmd):
    """The person-turn rule. Returns (None, tdata) when an unconsumed person line of `cmd` names
    `turn`; else ((rc, text), None). A consumed turn is a repeat (4); no such line is `no person turn` (3)."""
    p = st["persons"].get(turn) if turn else None
    if p and p["consumed"]:
        return (NOTHING, "stage_runner: that turn was already used (one person turn moves the run "
                         "at most one step). Nothing changed."), None
    if not p or p["cmd"] != cmd:
        return (CHECKFAIL, "stage_runner: no person turn -- only the person's typed /%s moves this "
                           "step. Ask them to type /%s." % (cmd, cmd)), None
    return None, {"turn": turn}


def do_advance(run_dir, card, via, turn=None):
    """Verify the current stage, then hand over. Under lock. Returns (rc, text).
    A TALK step also needs an unconsumed person{cmd:next} with the same turn; an ALONE step
    advances on a verified pass alone (a matching person line, if any, is consumed)."""
    with locked(run_dir):
        st = derive(load_record(run_dir))
        if st["pending"]:
            return DANGLING, "pending handover to %r without done: run `recover` first" % st["pending"]["data"].get("to")
        if st["complete"] or st["cur"] == "COMPLETE":
            return NOTHING, "stage_runner: the run is complete, nothing to advance."
        if st["abandoned"]:
            return NOTHING, "stage_runner: the run was abandoned; nothing to advance."
        i = stage_index(card, st["cur"])
        if i < 0:
            return DAMAGED, "stage_runner: the open step %r is not in the card." % st["cur"]
        stage = card["stages"][i]
        pl = st["persons"].get(turn) if turn else None
        if stage.get("mode", "talk") == "talk":
            refused, td = _turn_gate(st, turn, "next")
            if refused:
                return refused
        else:
            td = {"turn": turn} if pl and not pl["consumed"] and pl["cmd"] == "next" else {}
        problems = run_checks(card, stage, run_dir, st["code"], st["superseded"])
        # An OPTIONAL talk step may be skipped BY THE PERSON: on a person{cmd:next} turn
        # (same --turn, the normal turn gate) whose checks fail or whose output is missing,
        # record a pass naming the person turn and hand over as normal. Without a person
        # turn it is refused exactly as today -- the AI can never skip. Non-optional: unchanged.
        skipped = bool(problems) and bool(td) and stage.get("optional") \
            and stage.get("mode", "talk") == "talk"
        if problems and not skipped:
            append(run_dir, "fail", st["cur"], dict({"via": via, "problems": problems}, **td))
            append(run_dir, "handover", st["cur"], dict({"via": via, "result": "fail"}, **td))
            return CHECKFAIL, ("stage_runner: step %s is not finished. Missing:\n%s"
                               % (st["cur"], "\n".join("- " + p["detail"] for p in problems)))
        pdata = dict({"via": via}, **td)
        if skipped:
            pdata["skipped"] = "by the person"
        append(run_dir, "pass", st["cur"], pdata)
        append(run_dir, "handover", st["cur"], dict(pdata, result="pass"))
        to_i = i + 1
        to = card["stages"][to_i]["id"] if to_i < len(card["stages"]) else "COMPLETE"
        code = new_code() if to != "COMPLETE" else None
        append(run_dir, "intent", st["cur"], {"to": to, "code_hash": chash(code or ""), "via": via})
        prompt, ilines, bad = None, [], []
        if to != "COMPLETE":
            ilines, bad = inputs_report(card, run_dir, to_i)
            if not bad:
                prompt = render_prompt(card, run_dir, to_i, code)
        append(run_dir, "done", to, {"to": to, "code_hash": chash(code or "")})
        if to == "COMPLETE":
            append(run_dir, "complete", None, {})
            return OK, "stage_runner: the run is complete."
        if skipped:
            head = ("stage_runner: step %s was SKIPPED by your /next (not finished: %s). "
                    "Your next step:" % (st["cur"], ", ".join(p["code"] for p in problems)))
        else:
            head = "stage_runner: the %s step is done. Your next step:" % st["cur"]
        if bad:
            return OK, "%s\n%s\nA step input is missing or empty: %s. Do not start this step; tell the person." % (
                head, "\n".join(ilines), ", ".join(bad))
        return OK, "%s\n%s\n\n%s" % (head, "\n".join(ilines), prompt or "")


def do_back(run_dir, card, via="cli", turn=None):
    """Re-open the previous stage with a fresh code word. Under lock. Going back ALWAYS needs an
    unconsumed person{cmd:back} with the same turn; exactly one step."""
    with locked(run_dir):
        st = derive(load_record(run_dir))
        if st["pending"]:
            return DANGLING, "pending handover without done: run `recover` first"
        if st["complete"] or st["cur"] == "COMPLETE":
            return NOTHING, "stage_runner: the run is complete; back does not reopen it."
        if st["abandoned"]:
            return NOTHING, "stage_runner: the run was abandoned; nothing to reopen."
        i = stage_index(card, st["cur"])
        if i < 0:
            return DAMAGED, "stage_runner: the open step %r is not in the card." % st["cur"]
        refused, td = _turn_gate(st, turn, "back")
        if refused:
            return refused
        if i <= 0:
            append(run_dir, "handover", st["cur"], dict({"via": via, "result": "noop"}, **td))
            return NOTHING, "stage_runner: already at the first stage; nothing to go back to."
        to = card["stages"][i - 1]["id"]
        code = new_code()
        append(run_dir, "back", st["cur"], dict({"via": via, "to": to}, **td))
        append(run_dir, "intent", st["cur"], {"to": to, "code_hash": chash(code), "via": via, "back": True})
        prompt = render_prompt(card, run_dir, i - 1, code)
        append(run_dir, "done", to, {"to": to, "code_hash": chash(code)})
        return OK, ("stage_runner: the previous step %s is open again. A FRESH code word was issued: "
                    "update the output's `Code word:` line to it before the step can pass.\n\n%s" % (to, prompt))


def do_person_turn(run_dir, turn, cmd):
    """Append the person's typed command. ONLY this writes `person` lines. A used turn id is a repeat."""
    with locked(run_dir):
        st = derive(load_record(run_dir))
        if st["complete"] or st["cur"] == "COMPLETE":
            return NOTHING, "stage_runner: the run is complete; nothing to move."
        if st["abandoned"]:
            return NOTHING, "stage_runner: the run was abandoned; nothing to record."
        if turn in st["persons"]:
            return NOTHING, "stage_runner: turn %s was already used. Nothing changed." % turn
        append(run_dir, "person", None, {"turn": turn, "cmd": cmd})
        return OK, "person turn recorded: /%s" % cmd


def do_resume(run_dir, card):
    """Reissue the CURRENT step with a fresh code word. Never writes pass/done/complete.
    The AI's own move: needs a logged person prompt newer than the run's last line, unused
    by any earlier menu command (_menu_gate) -- else refused, ask the person first."""
    with locked(run_dir):
        lines = load_record(run_dir)
        st = derive(lines)
        if st["pending"]:
            return DANGLING, "stage_runner: a handover was left half-done: run recover first."
        if st["complete"] or st["cur"] == "COMPLETE":
            return NOTHING, "stage_runner: the run is finished; nothing to resume."
        if st["abandoned"]:
            return NOTHING, "stage_runner: the run was abandoned; nothing to resume."
        refused = _menu_gate(run_dir, lines)
        if refused:
            return refused
        i = stage_index(card, st["cur"])
        if i < 0:
            return DAMAGED, "stage_runner: the open step %r is not in the card." % st["cur"]
        code = new_code()
        append(run_dir, "reissue", st["cur"], {"code_hash": chash(code), "choice": "continue",
                                               "person": _newest_person(run_dir)})
        prompt = render_prompt(card, run_dir, i, code)
        out = os.path.join(run_dir, card["stages"][i]["out"])
        return OK, ("stage_runner: resumed at step %s (%d of %d). A FRESH code word was issued and the "
                    "old one no longer works: %s\nUpdate the Code word line in %s to the new word. "
                    "The step and its checks are unchanged.\n\n%s"
                    % (st["cur"], i + 1, len(card["stages"]), code, out, prompt))


def do_snooze(run_dir):
    with locked(run_dir):
        lines = load_record(run_dir)
        st = derive(lines)
        if st["complete"] or st["cur"] == "COMPLETE" or st["abandoned"]:
            return NOTHING, "stage_runner: the run is finished or abandoned; nothing to quiet."
        refused = _menu_gate(run_dir, lines)
        if refused:
            return refused
        append(run_dir, "snoozed", st["cur"], {"choice": "leave-it",
                                               "person": _newest_person(run_dir)})
        return OK, "stage_runner: left alone. The pickup question stays quiet for this run until it is brought up."


def do_recover(run_dir, card):
    """Complete a handover whose process died between intent and done."""
    with locked(run_dir):
        st = derive(load_record(run_dir))
        if not st["pending"]:
            return NOTHING, "no dangling handover"
        to = st["pending"]["data"].get("to")
        if to == "COMPLETE":
            append(run_dir, "done", "COMPLETE", {"to": "COMPLETE", "code_hash": ""})
            append(run_dir, "complete", None, {})
            return OK, "recovered: run marked complete."
        i = stage_index(card, to)
        if i < 0:
            append(run_dir, "recover", None, {"action": "rolled-back", "to": to})
            return OK, "recovered: rolled back the unknown target %r" % to
        code = new_code()
        prompt = render_prompt(card, run_dir, i, code)
        append(run_dir, "done", to, {"to": to, "code_hash": chash(code)})
        return OK, "recovered: handover to %s completed with a FRESH code word.\n\n%s" % (to, prompt)


# ---------------------------------------------------------------- commands
def get_ctx(args):
    try:
        f = find_run(getattr(args, "workdir", None))
    except Damaged as e:
        print("stage_runner: record damaged: %s. Everything but `verify` and `abandon` refuses." % e)
        return None, DAMAGED
    if not f:
        print("no active run in %s" % os.path.abspath(getattr(args, "workdir", None) or os.getcwd()))
        return None, NORUN
    wd, run_dir = f
    try:
        lines = load_record(run_dir)
    except Damaged as e:
        print("stage_runner: record damaged: %s. Everything but `verify` refuses." % e)
        return None, DAMAGED
    st = derive(lines)
    try:
        card = load_card(st["card"])
    except (OSError, ValueError) as e:
        print("stage_runner: the run's card is unreadable: %s" % e)
        return None, DAMAGED
    try:
        if st["card_sha"] and card_sha(st["card"], card) != st["card_sha"]:
            print("stage_runner: DAMAGED -- card changed mid-run (the card or a prompt file was edited "
                  "after the run started). Everything but `verify` refuses.")
            return None, DAMAGED
        if st["cur"] != "COMPLETE" and stage_index(card, st["cur"]) < 0:
            print("stage_runner: record damaged: the open step %r is not in the card. "
                  "Everything but 'verify' refuses." % st["cur"])
            return None, DAMAGED
        check_order(lines, card)
    except OSError as e:
        print("stage_runner: the run's card is unreadable: %s" % e)
        return None, DAMAGED
    except Damaged as e:
        print("stage_runner: record damaged: %s. Everything but `verify` refuses." % e)
        return None, DAMAGED
    return (wd, run_dir, lines, st, card), OK


def _set_aside(marker, tag):
    """Rename the marker to <marker>.<tag> (never delete); returns the new path."""
    tag = re.sub(r"[^A-Za-z0-9_.-]", "_", str(tag))[:80]
    dst = "%s.%s" % (marker, tag)
    if os.path.exists(dst):
        dst = "%s-%d" % (dst, int(time.time()))
    os.rename(marker, dst)
    return dst


def cmd_start(a):
    wd = os.path.abspath(a.workdir)
    try:
        card = load_card(a.card)
    except ValueError as e:
        print("stage_runner: %s" % e)
        return USAGE
    # fail-closed BEFORE anything is written: a card naming a delegated check whose
    # part is not beside this file must refuse now, not fail silently at check time.
    for s in card["stages"]:
        for key in DELEGATES:
            if s.get("checks", {}).get(key):
                _delegate(DELEGATES[key], ["--selftest"]) if False else None
                p = os.path.join(HERE, DELEGATES[key])
                if not os.path.isfile(p):
                    print("stage_runner: CANNOT EVALUATE -- stage %r names the %r check but %s "
                          "is not beside stage_runner.py (%s). Deploy them together."
                          % (s["id"], key, DELEGATES[key], HERE))
                    return USAGE
    try:
        found = find_run(wd)
    except Damaged as e:
        print("stage_runner: record damaged: %s. Nothing was changed; have the person choose "
              "start over (abandon) first." % e)
        return DAMAGED
    if found:
        try:
            old = derive(load_record(found[1]))
        except (Damaged, OSError) as e:
            print("stage_runner: the run in %s is damaged (%s). Nothing was changed; have the "
                  "person choose start over (abandon) first." % (found[0], e))
            return DAMAGED
        if old["abandoned"]:
            # an abandoned run revived by copying its .abandoned- marker back: set it
            # aside again like a finished run, then begin a NEW run (never revive it).
            mp = os.path.join(found[0], MARKER)
            _set_aside(mp, "abandoned-" + (old["run"] or os.path.basename(found[1])))
        elif not (old["complete"] or old["cur"] == "COMPLETE"):
            print("stage_runner: a run is already active in %s. Nothing was changed. "
                  "Use a different --workdir to start fresh." % wd)
            return NOTHING
        else:
            # a finished run: set its marker aside (kept, not deleted) and begin a NEW run
            mp = os.path.join(found[0], MARKER)
            _set_aside(mp, "done-" + (old["run"] or os.path.basename(found[1])))
    rid = a.run_id or time.strftime("%Y%m%dT%H%M%S") + "-" + secrets.token_hex(2)
    run_dir = os.path.join(wd, "runs", rid)
    if os.path.exists(run_dir):
        print("run dir exists: %s" % run_dir)
        return USAGE
    os.makedirs(os.path.join(run_dir, "out"))
    first = card["stages"][0]["id"]
    code = new_code()
    append(run_dir, "start", None, {"card": os.path.abspath(a.card), "skill": card.get("skill", ""),
                                    "first": first, "code_hash": chash(code),
                                    "card_sha": card_sha(a.card, card)}, run=rid)
    json.dump({"run_dir": run_dir, "run_id": rid, "card": os.path.abspath(a.card)},
              open(os.path.join(wd, MARKER), "w", encoding="utf-8"))
    ensure_commands(wd)
    ptr_err = record_pointer(wd)
    prompt = render_prompt(card, run_dir, 0, code)
    warn = "\nrun started, but /next from other windows may not work: %s" % ptr_err if ptr_err else ""
    print("run %s started in %s (%s, %d stages)%s\ncode word for stage %s (print once, never store): %s\n\n%s"
          % (rid, wd, card.get("skill", ""), len(card["stages"]), warn, first, code, prompt))
    return OK


def cmd_status(a):
    c, rc = get_ctx(a)
    if not c:
        return rc
    wd, run_dir, lines, st, card = c
    problems = []
    if not (st["complete"] or st["cur"] == "COMPLETE"):
        problems = run_checks(card, card["stages"][stage_index(card, st["cur"])], run_dir, st["code"],
                              st["superseded"])
    i = stage_index(card, st["cur"])
    done = st["complete"] or st["cur"] == "COMPLETE"
    mode = card["stages"][i].get("mode", "talk") if 0 <= i < len(card["stages"]) else ""
    j = {"run": st["run"], "skill": st["skill"], "stage": st["cur"],
         "index": len(card["stages"]) if done else i + 1, "total": len(card["stages"]),
         "mode": mode, "complete": st["complete"], "pending": bool(st["pending"]),
         "fails": st["fails"], "snoozed": st["snoozed"], "abandoned": st["abandoned"],
        "skipped": st["skipped"],
         "summary": "RUN done" if done else "RUN %d/%d %s (%s)" % (i + 1, len(card["stages"]), st["cur"], mode),
         "missing": [p["detail"] for p in problems], "lines": len(lines)}
    if a.json:
        print(json.dumps(j, indent=1))
    else:
        print("%s | run %s%s\nmissing: %s" % (j["summary"], j["run"],
              (" | DANGLING" if st["pending"] else ""), "; ".join(j["missing"]) or "nothing"))
    return OK


def cmd_check(a):
    c, rc = get_ctx(a)
    if not c:
        return rc
    wd, run_dir, lines, st, card = c
    if st["complete"] or st["cur"] == "COMPLETE":
        print("PASS (run complete)")
        return OK
    try:
        problems = run_checks(card, card["stages"][stage_index(card, st["cur"])], run_dir, st["code"],
                              st["superseded"])
    except (PartMissing, CannotEvaluate) as e:
        print("stage_runner: CANNOT EVALUATE -- %s" % e)
        return USAGE
    if problems:
        print("FAIL\n" + "\n".join("- " + p["detail"] for p in problems))
        return CHECKFAIL
    print("PASS")
    return OK


def cmd_advance(a):
    c, rc = get_ctx(a)
    if not c:
        return rc
    try:
        rc, txt = do_advance(c[1], c[4], a.via, a.turn)
    except (PartMissing, CannotEvaluate) as e:
        print("stage_runner: CANNOT EVALUATE -- %s" % e)
        return USAGE
    print(txt)
    return rc


def cmd_back(a):
    c, rc = get_ctx(a)
    if not c:
        return rc
    rc, txt = do_back(c[1], c[4], "cli", a.turn)
    print(txt)
    return rc


MENU = {"resume": "continue", "abandon": "start-over", "snooze": "leave-it"}


def _bad_choice(cmd, choice):
    """Exit 2 unless --choice is this command's menu word (closed menu: continue / start-over / leave-it)."""
    if choice == MENU[cmd]:
        return None
    print("stage_runner: %r is not a menu word for %s (the closed menu is continue / start-over / "
          "leave-it; %s takes %s). Ask the person again." % (choice, cmd, cmd, MENU[cmd]))
    return USAGE


def cmd_person_turn(a):
    if not a.turn or not a.cmd_:
        print("stage_runner: person-turn needs --turn and --cmd next|back")
        return USAGE
    c, rc = get_ctx(a)
    if not c:
        return rc
    rc, txt = do_person_turn(c[1], a.turn, a.cmd_)
    print(txt)
    return rc


def cmd_resume(a):
    bad = _bad_choice("resume", a.choice)
    if bad:
        return bad
    c, rc = get_ctx(a)
    if not c:
        return rc
    rc, txt = do_resume(c[1], c[4])
    print(txt)
    return rc


def cmd_snooze(a):
    bad = _bad_choice("snooze", a.choice)
    if bad:
        return bad
    c, rc = get_ctx(a)
    if not c:
        return rc
    rc, txt = do_snooze(c[1])
    print(txt)
    return rc


def cmd_abandon(a):
    """Set the run aside. Works on a damaged record, an unreadable card or a bad marker: the
    marker is renamed in every case; `abandoned` is appended only if the record verifies. Never
    writes pass / done / complete; nothing is deleted."""
    bad = _bad_choice("abandon", a.choice)
    if bad:
        return bad
    found = find_marker(a.workdir)
    if not found:
        print("no active run in %s" % os.path.abspath(a.workdir or os.getcwd()))
        return NORUN
    wd, mp = found
    rid = run_dir = None
    try:
        j = json.load(open(mp, encoding="utf-8"))
        if isinstance(j, dict):
            rid = j.get("run_id") if isinstance(j.get("run_id"), str) else None
            run_dir = j.get("run_dir") if isinstance(j.get("run_dir"), str) else None
    except (OSError, ValueError):
        pass
    # the run folder must sit inside the marker's folder, resolved exactly as find_run
    # resolves it (realpath) -- a copied folder whose marker still names the original run
    # renames its marker only and NEVER appends to the original record.
    note = ""
    outside = False
    if run_dir:
        if not os.path.isabs(run_dir):
            run_dir = os.path.join(wd, run_dir)
        rr, rw = os.path.realpath(run_dir), os.path.realpath(wd)
        if rr != rw and not (rr + os.sep).startswith(rw + os.sep):
            outside = True
            note = (" (the run folder sits outside the marker's folder, so no abandoned "
                    "line was written)")
    tag = "abandoned-"
    if run_dir and not outside:
        try:
            lines = load_record(run_dir)
            st = derive(lines)
            rid = rid or lines[0]["run"]
            if st["complete"] or st["cur"] == "COMPLETE":
                tag = "done-"        # a finished run set aside was never abandoned mid-way
            refused = _menu_gate(run_dir, lines)
            if refused:
                print(refused[1])
                return CHECKFAIL
            append(run_dir, "abandoned", st["cur"], {"choice": "start-over",
                                                     "person": _newest_person(run_dir)})
        except (Damaged, OSError, IndexError, KeyError):
            note = " (the record does not verify, so no abandoned line was written)"
    dst = _set_aside(mp, tag + (rid or (os.path.basename(run_dir) if run_dir else None)
                                or "unknown-%d" % int(time.time())))
    print("stage_runner: run set aside%s. Marker moved to %s. Nothing was deleted." % (note, dst))
    return OK


def cmd_recover(a):
    c, rc = get_ctx(a)
    if not c:
        return rc
    rc, txt = do_recover(c[1], c[4])
    print(txt)
    return rc


def cmd_verify(a):
    """The no-AI finish check command: verify the chain, the replay rule and the mover log;
    report, never write. A `person` line whose turn is not in <run folder>/mover.log is
    reported (tamper-evidence, not prevention) and exits 3."""
    if getattr(a, "run", None):
        # --run <folder>: read that run folder directly -- also a run whose marker was
        # set aside (abandoned), which find_run can no longer see.
        run_dir = os.path.abspath(a.run)
        if not os.path.isfile(os.path.join(run_dir, "record.jsonl")):
            print("no record at %s" % run_dir)
            return NORUN
    else:
        try:
            f = find_run(a.workdir)
        except Damaged as e:
            print("DAMAGED: %s" % e)
            return DAMAGED
        if not f:
            print("no active run")
            return NORUN
        run_dir = f[1]
    try:
        lines = load_record(run_dir)
        st = derive(lines)
        try:
            card = load_card(st["card"])
        except (OSError, ValueError) as e:
            print("DAMAGED: the run's card is unreadable (%s)" % e)
            return DAMAGED
        try:
            if st["card_sha"] and card_sha(st["card"], card) != st["card_sha"]:
                print("DAMAGED: card changed mid-run")
                return DAMAGED
            check_order(lines, card)
        except OSError as e:
            print("DAMAGED: the run's card is unreadable (%s)" % e)
            return DAMAGED
        except Damaged as e:
            print("DAMAGED: %s" % e)
            return DAMAGED
    except Damaged as e:
        print("DAMAGED: %s" % e)
        return DAMAGED
    logged = set()
    try:
        logged = set(x.strip() for x in open(os.path.join(run_dir, "mover.log"), encoding="utf-8"))
    except OSError:
        pass
    ghosts = [l["data"]["turn"] for l in lines if l["event"] == "person" and l["data"]["turn"] not in logged]
    pids, ptimes = set(), {}
    try:
        for ln in open(os.path.join(run_dir, "person.log"), encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            pid_, _, t_ = ln.partition("\t")
            pids.add(pid_)
            try:
                ptimes[pid_] = float(t_)
            except ValueError:
                pass
    except OSError:
        pass
    nprompts = []
    used_menu_ids = set()   # each person prompt id may serve exactly ONE menu command
    prev_t = None
    for l in lines:
        e = l["event"]
        if e in ("reissue", "abandoned", "snoozed"):
            rec = l["data"].get("person")
            where = "line %d" % (l["seq"] + 1)
            pid_ = rec.get("id") if isinstance(rec, dict) else None
            if not rec:
                nprompts.append("%s at %s: no person prompt recorded" % (e, where))
            elif pid_ not in pids:
                nprompts.append("%s at %s: its person prompt %r is not in person.log"
                                % (e, where, pid_))
            elif pid_ in used_menu_ids:
                nprompts.append("%s at %s: its person prompt %r was already used by another "
                                "menu command" % (e, where, pid_))
            elif prev_t is not None and ptimes.get(pid_, 0.0) + 1.0 < prev_t:
                nprompts.append("%s at %s: its person prompt is older than the run's last "
                                "move" % (e, where))
            if pid_:
                used_menu_ids.add(pid_)
        prev_t = l["t"]
    if ghosts:
        print("UNLOGGED: person line not written by the mover: turn %s (%d line%s)"
              % (", ".join(ghosts), len(ghosts), "" if len(ghosts) == 1 else "s"))
        ghosts_report = True
    else:
        ghosts_report = False
    if nprompts:
        print("UNLOGGED: a resume/abandon/snooze without a logged person prompt (%d):\n%s"
              % (len(nprompts), "\n".join("- " + x for x in nprompts)))
    if ghosts_report or nprompts:
        return CHECKFAIL
    print("OK %d lines" % len(lines))
    return OK


def cmd_statusline(a):
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    inner = ""
    if a.inner:
        try:
            inner = subprocess.run(a.inner, shell=True, input=raw, capture_output=True,
                                   text=True, timeout=5).stdout.strip().splitlines()[0]
        except Exception:
            inner = ""
    tag = ""
    try:
        jj = json.loads(raw) if raw else {}
        cwd = (jj.get("workspace") or {}).get("current_dir") or jj.get("cwd")
        f = find_run(cwd or os.getcwd())
        if f:
            pct = (jj.get("context_window") or {}).get("used_percentage")
            if isinstance(pct, (int, float)):
                json.dump({"pct": pct, "t": time.time()},
                          open(os.path.join(f[1], "context.json"), "w", encoding="utf-8"))
            try:
                st = derive(load_record(f[1]))
                card = load_card(st["card"])
                if st["complete"]:
                    tag = "RUN done"
                else:
                    i = stage_index(card, st["cur"])
                    tag = "RUN %d/%d %s (%s)" % (i + 1, len(card["stages"]), st["cur"],
                                                 card["stages"][i].get("mode", ""))
            except (Damaged, OSError, ValueError):
                tag = "RUN RECORD DAMAGED"
    except Exception:
        tag = ""
    print(" | ".join(x for x in (inner, tag) if x))
    return OK


# ---------------------------------------------------------------- self-test
def _selftest_card(td, with_forbid=True, alone=True):
    """A two-stage card for the self-test: talk stage then alone stage."""
    pdir = os.path.join(td, "prompts")
    os.makedirs(pdir, exist_ok=True)
    open(os.path.join(pdir, "01-frame.md"), "w", encoding="utf-8").write(
        "Stage {{ID}} of {{TOTAL}} ({{MODE}}). Write to {{OUT}}.\n")
    open(os.path.join(pdir, "02-connect.md"), "w", encoding="utf-8").write(
        "Stage {{ID}}. Your code word: {{CODE}}. Previous output: {{PREV}}. Write to {{OUT}}.\n")
    st1 = {"id": "frame", "mode": "talk", "prompt": "prompts/01-frame.md", "out": "out/01-frame.md",
           "checks": {"headings": ["## Frame"], "min_words": 10, "code_word": True}}
    st2 = {"id": "connect", "mode": "alone" if alone else "talk", "prompt": "prompts/02-connect.md",
           "out": "out/02-connect.md",
           "checks": {"headings": ["## Connect"], "min_words": 10, "code_word": True}}
    if with_forbid:
        st2["checks"]["forbid"] = [{"id": "no-win-yet", "term": "Win", "mode": "declaration",
                                    "why": "selftest: the Win is named later"}]
    return {"skill": "selftest", "stop_limit": 3, "stages": [st1, st2]}


def _run(args, cwd=None):
    return subprocess.run([sys.executable, os.path.abspath(__file__)] + args,
                          capture_output=True, text=True, cwd=cwd)


def _person_advance(wd, turn):
    """The person types /next: person-turn, then advance --turn (what the mover does)."""
    _run(["person-turn", "--turn", turn, "--cmd", "next", "--workdir", wd])
    return _run(["advance", "--turn", turn, "--workdir", wd])


def _stage1_body(code):
    return ("## Frame\n\nThe monthly goal is confirmed as written and the deltas are "
            "gathered here for the week ahead.\n\nCode word: %s\n" % code)


def _broken_variant(td, sabotage):
    """A copy of this runner with ONE verification deliberately broken, for the
    failing-first proof: the finish check must FAIL against it."""
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    marks = {
        "chain": ('            assert o["seq"] == i and o["prev"] == prev and _hash(prev, o) == h',
                  '            assert o["seq"] == i'),
        "gate": ('        problems = run_checks(card, stage, run_dir, st["code"], st["superseded"])',
                 '        problems = []'),
        "sibling": ('    if not os.path.isfile(p):\n        raise PartMissing(part)',
                    '    if not os.path.isfile(p):\n        class _P:\n'
                    '            stdout = json.dumps({"hits": [], "verdicts": []})\n'
                    '            returncode = 0\n'
                    '        return _P()'),
    }
    if sabotage not in marks:
        raise ValueError("unknown sabotage %r" % sabotage)
    old, new = marks[sabotage]
    if old not in src:
        raise ValueError("sabotage anchor not found for %r -- the runner changed shape" % sabotage)
    dst = os.path.join(td, "broken_%s.py" % sabotage)
    open(dst, "w", encoding="utf-8").write(src.replace(old, new))
    return dst


def _run_broken(broken_path, args):
    return subprocess.run([sys.executable, broken_path] + args, capture_output=True, text=True)


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f" [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("stage_runner --selftest (the no-AI finish check, plus failing-first proofs)")
    os.environ["HOME"] = tempfile.mkdtemp(prefix="sr-selftest-home.")  # the run pointer never touches the real one

    import shutil

    # -- the pointer failure is reported, never swallowed (a stand-in run_pointer.sh that fails) --
    _here = globals()["HERE"]
    with tempfile.TemporaryDirectory() as fake:
        os.makedirs(os.path.join(fake, "parts"))
        os.makedirs(os.path.join(fake, "tools"))
        with open(os.path.join(fake, "tools", "run_pointer.sh"), "w", encoding="utf-8") as fh:
            fh.write("echo 'no writable flag folder' >&2\nexit 3\n")
        globals()["HERE"] = os.path.join(fake, "parts")
        try:
            why = record_pointer(fake)
        finally:
            globals()["HERE"] = _here
    report("a failing pointer script is reported with its reason", "no writable flag folder" in why, repr(why))

    with tempfile.TemporaryDirectory() as td:
        card = os.path.join(td, "card.json")
        json.dump(_selftest_card(td), open(card, "w", encoding="utf-8"))
        wd = os.path.join(td, "fixture")
        os.makedirs(wd)

        # -- fixture run, no AI ------------------------------------------------
        p = _run(["start", "--card", card, "--workdir", wd])
        report("start exits OK", p.returncode == OK, "exit %d" % p.returncode)
        m = re.search(r"code word for stage frame \(print once, never store\): (RUN-[0-9A-Z]{6})", p.stdout)
        code1 = m.group(1) if m else None
        report("start prints the first code word", bool(code1))
        p = _run(["verify", "--workdir", wd])
        report("verify on a fresh run: OK", p.returncode == OK and p.stdout.startswith("OK "),
               p.stdout.strip())

        # -- (2) out-of-order: stage 1 unmet -> advance refused ----------------
        p = _person_advance(wd, "s0")
        report("advance with stage 1 unmet exits CHECKFAIL", p.returncode == CHECKFAIL,
               "exit %d" % p.returncode)
        p = _run(["advance", "--workdir", wd])
        report("a talk step refuses an advance with no person turn (exit 3, no person turn)",
               p.returncode == CHECKFAIL and "no person turn" in p.stdout, "exit %d" % p.returncode)
        p = _run(["advance", "--turn", "s0", "--workdir", wd])
        report("a used person turn is a repeat (exit 4)", p.returncode == NOTHING, "exit %d" % p.returncode)
        p2 = _run(["check", "--workdir", wd])
        report("check on the unmet stage exits CHECKFAIL", p2.returncode == CHECKFAIL,
               "exit %d" % p2.returncode)
        rid = os.listdir(os.path.join(wd, "runs"))[0]
        raw = open(os.path.join(wd, "runs", rid, "record.jsonl"), encoding="utf-8").read()
        report("no pass was recorded for the unmet stage", '"stage": "frame"' not in
               [l for l in raw.splitlines() if '"event": "pass"' in l][0] if
               any('"event": "pass"' in l and '"stage": "frame"' in l for l in raw.splitlines())
               else True)
        # satisfy stage 1 properly and advance
        out1 = os.path.join(wd, "runs", rid, "out", "01-frame.md")
        open(out1, "w", encoding="utf-8").write(_stage1_body(code1))
        p = _person_advance(wd, "s1")
        report("advance after a passing stage exits OK", p.returncode == OK,
               "exit %d %s" % (p.returncode, p.stdout[:80]))
        m = re.search(r"(RUN-[0-9A-Z]{6})", p.stdout)
        code2 = m.group(1) if m else None
        out2 = os.path.join(wd, "runs", rid, "out", "02-connect.md")
        open(out2, "w", encoding="utf-8").write("## Connect\n\nThe connected picture follows from the frame "
                              "above, complete for the week.\n\nCode word: %s\n" % code2)
        p = _run(["advance", "--workdir", wd])
        report("second advance completes the run",
               p.returncode == OK and "complete" in p.stdout.lower(),
               "exit %d %s" % (p.returncode, p.stdout.strip()[:80]))
        p = _run(["advance", "--workdir", wd])
        report("advance past the end is a NOTHING no-op", p.returncode == NOTHING,
               "exit %d" % p.returncode)
        p = _run(["back", "--workdir", wd])
        report("back on a complete run is refused", p.returncode == NOTHING, "exit %d" % p.returncode)

        # -- (1) damaged record: copy, edit one field, verify + refuse ---------
        copy = os.path.join(td, "copy")
        shutil.copytree(wd, copy)
        # the marker names the run dir by absolute path; a copied run points at ITS copy
        json.dump({"run_dir": os.path.join(copy, "runs", rid), "run_id": rid},
                  open(os.path.join(copy, MARKER), "w", encoding="utf-8"))
        recp = os.path.join(copy, "runs", rid, "record.jsonl")
        lines = open(recp, encoding="utf-8").read().splitlines(True)
        mid = len(lines) // 2
        obj = json.loads(lines[mid])
        for k in ("event", "stage", "run"):
            if obj.get(k):
                obj[k] = obj[k] + "x"
                break
        else:
            obj["t"] = obj["t"] + 1.0
        lines[mid] = json.dumps(obj, sort_keys=True) + "\n"
        open(recp, "w", encoding="utf-8").write("".join(lines))
        p = _run(["verify", "--workdir", copy])
        report("hand-edited record is reported DAMAGED with exit 6",
               p.returncode == DAMAGED and p.stdout.startswith("DAMAGED:"),
               "exit %d %s" % (p.returncode, p.stdout.strip()))
        before = open(recp, encoding="utf-8").read()
        p = _run(["advance", "--workdir", copy])
        report("advance on a damaged record refuses without writing",
               p.returncode == DAMAGED and open(recp, encoding="utf-8").read() == before,
               "exit %d" % p.returncode)
        open(recp, "w", encoding="utf-8").write(before.rstrip("\n"))
        p = _run(["verify", "--workdir", copy])
        report("a torn tail (no final newline) is reported DAMAGED", p.returncode == DAMAGED,
               "exit %d" % p.returncode)

        # -- (3) card naming a missing check part -------------------------------
        lone = os.path.join(td, "lone")
        os.makedirs(lone)
        shutil.copy(os.path.abspath(__file__), os.path.join(lone, RUNNER))
        lp = os.path.join(lone, "prompts")
        os.makedirs(lp, exist_ok=True)
        open(os.path.join(lp, "01-frame.md"), "w", encoding="utf-8").write("Stage {{ID}}. Write to {{OUT}}.\n")
        open(os.path.join(lp, "02-connect.md"), "w", encoding="utf-8").write("Stage {{ID}}. Write to {{OUT}}.\n")
        lone_card = os.path.join(lone, "card.json")
        c = _selftest_card(td, with_forbid=True)
        c["stages"][0]["prompt"] = "prompts/01-frame.md"
        c["stages"][1]["prompt"] = "prompts/02-connect.md"
        json.dump(c, open(lone_card, "w", encoding="utf-8"))
        p = subprocess.run([sys.executable, os.path.join(lone, RUNNER), "start", "--card",
                            lone_card, "--workdir", os.path.join(lone, "wd")],
                           capture_output=True, text=True)
        report("card naming a missing check part is refused at start (exit 2, fail-closed)",
               p.returncode == USAGE and "forbidden_content.py" in (p.stdout + p.stderr),
               "exit %d %s" % (p.returncode, (p.stdout + p.stderr).strip()[:100]))
        report("nothing was written for the refused card",
               not os.path.exists(os.path.join(lone, "wd", MARKER)))

        # -- failing-first: each check FAILS against a broken variant ----------
        bwd = os.path.join(td, "bwd")
        os.makedirs(bwd)
        bcard = os.path.join(td, "bcard.json")
        json.dump(_selftest_card(td, with_forbid=False), open(bcard, "w", encoding="utf-8"))
        _run(["start", "--card", bcard, "--workdir", bwd])
        brid = os.listdir(os.path.join(bwd, "runs"))[0]

        # chain sabotage: the broken runner MISSES a damaged record
        bcopy = os.path.join(td, "bdmg")
        shutil.copytree(bwd, bcopy)
        json.dump({"run_dir": os.path.join(bcopy, "runs", brid), "run_id": brid},
                  open(os.path.join(bcopy, MARKER), "w", encoding="utf-8"))
        drec = os.path.join(bcopy, "runs", brid, "record.jsonl")
        raw = open(drec, encoding="utf-8").read()
        first_line = raw.splitlines()[0]
        obj = json.loads(first_line)
        obj["data"]["skill"] = obj["data"]["skill"] + "x"
        open(drec, "w", encoding="utf-8").write(json.dumps(obj, sort_keys=True) + "\n"
                              + raw.split("\n", 1)[1])
        bv = _run_broken(_broken_variant(td, "chain"), ["verify", "--workdir", bcopy])
        report("FAILING-FIRST: damaged-record check MISSES the damage on the broken runner",
               bv.returncode == OK, "broken exit %d" % bv.returncode)
        rv = _run(["verify", "--workdir", bcopy])
        report("...and the real runner CATCHES it", rv.returncode == DAMAGED,
               "exit %d" % rv.returncode)

        # gate sabotage: advance with stage 1 unmet must SUCCEED on the broken runner
        gcopy = os.path.join(td, "bgate")
        shutil.copytree(bwd, gcopy)
        json.dump({"run_dir": os.path.join(gcopy, "runs", brid), "run_id": brid},
                  open(os.path.join(gcopy, MARKER), "w", encoding="utf-8"))
        _run(["person-turn", "--turn", "g1", "--cmd", "next", "--workdir", gcopy])
        bg = _run_broken(_broken_variant(td, "gate"), ["advance", "--turn", "g1", "--workdir", gcopy])
        report("FAILING-FIRST: out-of-order advance SUCCEEDS on the broken runner",
               bg.returncode == OK, "broken exit %d" % bg.returncode)
        rg = _person_advance(bwd, "b1")
        report("...and the real runner REFUSES it", rg.returncode == CHECKFAIL,
               "exit %d" % rg.returncode)

        # sibling sabotage: a missing check part is ACCEPTED by the broken runner
        # (two neuterings: the start-time refusal AND the delegate's raise)
        slpath = _broken_variant(td, "sibling")
        anchor = 'if not os.path.isfile(p):\n                    print("stage_runner: CANNOT EVALUATE'
        slsrc = open(slpath, encoding="utf-8").read()
        assert anchor in slsrc, "start-refusal anchor moved"
        open(slpath, "w", encoding="utf-8").write(slsrc.replace(
            anchor, 'if False:\n                    print("stage_runner: CANNOT EVALUATE'))
        slsrc = slpath
        slone = os.path.join(td, "slone")
        os.makedirs(slone)
        shutil.copy(slsrc, os.path.join(slone, RUNNER))
        sc = os.path.join(slone, "card.json")
        json.dump({"skill": "s", "stages": [{"id": "a", "mode": "talk", "out": "out/a.md",
                                             "checks": {"forbid": [{"id": "x", "term": "y"}]}}]},
                  open(sc, "w", encoding="utf-8"))
        swd = os.path.join(slone, "wd")
        subprocess.run([sys.executable, slsrc, "start", "--card", sc, "--workdir", swd],
                       capture_output=True, text=True)
        srid = os.listdir(os.path.join(swd, "runs"))[0]
        os.makedirs(os.path.join(swd, "runs", srid, "out"), exist_ok=True)
        open(os.path.join(swd, "runs", srid, "out", "a.md"), "w", encoding="utf-8").write("some content\n")
        rb = _run_broken(slsrc, ["check", "--workdir", swd])
        report("FAILING-FIRST: missing-check-part card is ACCEPTED by the broken runner",
               rb.returncode in (OK, NOTHING), "broken exit %d" % rb.returncode)
        # the real runner, alone (no sibling parts beside it), refuses the same card at start
        rlone = os.path.join(td, "rlone")
        os.makedirs(rlone)
        shutil.copy(os.path.abspath(__file__), os.path.join(rlone, RUNNER))
        rcard = os.path.join(rlone, "card.json")
        json.dump({"skill": "s", "stages": [{"id": "a", "mode": "talk", "out": "out/a.md",
                                             "checks": {"forbid": [{"id": "x", "term": "y"}]}}]},
                  open(rcard, "w", encoding="utf-8"))
        pr = subprocess.run([sys.executable, os.path.join(rlone, RUNNER), "start", "--card", rcard,
                             "--workdir", os.path.join(rlone, "wd")], capture_output=True, text=True)
        report("real runner: card naming a missing check part refused at start",
               pr.returncode == USAGE and "forbidden_content.py" in (pr.stdout + pr.stderr),
               "exit %d" % pr.returncode)

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(prog=RUNNER,
                                 description="stage_runner -- the stateful step runner for long skills")
    ap.add_argument("--workdir", default=os.getcwd(),
                    help="folder the run lives in (default: cwd); every path comes from "
                         "arguments, never hard-coded")
    ap.add_argument("--selftest", action="store_true",
                    help="run the two-sided self-test (the no-AI finish check)")
    sp = ap.add_subparsers(dest="cmd")

    def add(name, fn, *args):
        s = sp.add_parser(name)
        # SUPPRESS: a global --workdir given BEFORE the subcommand must survive; a
        # subcommand-level default would overwrite it.
        s.add_argument("--workdir", default=argparse.SUPPRESS)
        for ar, kw in args:
            s.add_argument(ar, **kw)
        s.set_defaults(fn=fn)

    add("start", cmd_start, ("--card", dict(required=True)), ("--run-id", dict(default=None)))
    add("status", cmd_status, ("--json", dict(action="store_true")))
    add("check", cmd_check)
    add("advance", cmd_advance, ("--via", dict(default="cli")), ("--turn", dict(default=None)))
    add("back", cmd_back, ("--turn", dict(default=None)))
    add("person-turn", cmd_person_turn, ("--turn", dict(default=None)),
        ("--cmd", dict(dest="cmd_", choices=["next", "back"], default=None)))
    add("resume", cmd_resume, ("--choice", dict(default=None)))
    add("abandon", cmd_abandon, ("--choice", dict(default=None)))
    add("snooze", cmd_snooze, ("--choice", dict(default=None)))
    add("recover", cmd_recover)
    add("verify", cmd_verify, ("--run", dict(default=None, metavar="RUN_FOLDER",
        help="verify this run folder directly (also a set-aside/abandoned run)")))
    add("statusline", cmd_statusline, ("--inner", dict(default="")))
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_usage()
        return USAGE
    if a.cmd == "statusline":
        return cmd_statusline(a)
    try:
        return a.fn(a)
    except Damaged as e:
        print("stage_runner: record damaged: %s" % e)
        return DAMAGED
    except PartMissing as e:
        print("stage_runner: CANNOT EVALUATE -- the card names a check whose part is not "
              "beside stage_runner.py: %s. Deploy them together." % e)
        return USAGE
    except CannotEvaluate as e:
        print("stage_runner: CANNOT EVALUATE -- %s" % e)
        return USAGE


if __name__ == "__main__":
    sys.exit(main())
