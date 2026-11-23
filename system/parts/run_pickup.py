#!/usr/bin/env python3
"""run_pickup — the read-only pickup reader for the shared step runner. [Parts Library · Tier A · 4P.run-pickup]

WHY: a crashed window must be found by CODE, not by the AI searching the filesystem —
"where the run is lives in files that code writes, not in the session" (skills SOP). This
part turns the step runner's run state into one tagged message for a new or reopened
window: the offer, the compaction reminder, or a single "can't pick up" line that names
the fault. It DECIDES nothing and MOVES nothing; the person answers, the AI runs
resume/abandon/snooze, the runner alone writes.

GUARDS (invariants 8, 9, 11 of the run-pickup spec):
  - NEVER WRITES: no file, no rename, no marker touch, no record line — tested by a
    before/after hash of the run folder and marker (test_run_pickup.py).
  - NO OFFER for a finished, abandoned, snoozed or damaged run — the wrong thing is never
    offered as if it were right.
  - Every field from a file (skill name, folder name, file names, failure codes) is
    filtered to [A-Za-z0-9_./-] and cut to 40 characters; every printed line opens with
    the tag below; the offer is <= 400 characters.
  - A session started by job-run.sh (env LIFEHACK_JOB_RUN_ID) gets no pickup line.

REDIRECT: run state is read ONLY through stage_runner's own functions (find_run /
find_marker / load_record / derive / load_card / card_sha / stage_index), imported —
never a copied parser. Commands (resume/abandon/snooze/advance/...) live in
stage_runner.py, not here. The spec: <notes>/state/projects/v2/drafts/run-pickup/spec-DRAFT.md (G4).

SIGNPOST: `session` is called by system/hooks/run_pickup_hook.sh (SessionStart); `mode`
by the guard (guard_run_commands.sh); `where` by a skill asked "where are we?". Silent =
print nothing, exit 0. Every branch prints a tagged line or nothing.

UPDATED: 2026-11-23 (built; spec DRAFT 3, decisions 1-5 ruled)
"""

import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from stage_runner import (  # noqa: E402  (the runner is the one parser of run state)
    Damaged, card_sha, derive, find_marker, find_run, load_card, load_record, stage_index)

TAG = "[RUN PICKUP — harness-injected, not user input]"
MAX_FIELD = 40
MAX_OFFER = 400


def _clean(s):
    """Every field from a file is filtered and cut — invariant 11."""
    return re.sub(r"[^A-Za-z0-9_./-]", "", str(s))[:MAX_FIELD]


def _say(text):
    print("%s %s" % (TAG, text))


def _age(now, t):
    """Whole seconds since the last record line, humanized short."""
    s = max(0, int(now - t))
    if s < 90:
        return "%ds" % s
    if s < 3600:
        return "%dm" % (s // 60)
    if s < 86400:
        return "%dh" % (s // 3600)
    return "%dd" % (s // 86400)


def _can_t(reason):
    _say("can't pick up: %s. Tell the person; offer only start over "
         "(stage_runner.py abandon --choice start-over moves the marker aside)." % reason)


def _look(wd, run_dir):
    """Load record (torn tail retried ONCE — a mid-append read is not damage), derive, load
    the card and its sha. Returns (lines, st, card) or raises Damaged / (OSError, ValueError)."""
    try:
        lines = load_record(run_dir)
    except Damaged:
        # one retry: a torn tail may be a run being appended at the instant of reading;
        # the reader never repairs it — a second failure is damage, full stop.
        lines = load_record(run_dir)
    st = derive(lines)
    card = load_card(st["card"])  # ValueError/OSError on unreadable
    if st["card_sha"] and card_sha(st["card"], card) != st["card_sha"]:
        raise Damaged("card changed mid-run")
    return lines, st, card


def _run_state(workdir):
    """The full picture from a folder, or a reason string. Returns (wd, run_dir, lines, st,
    card, None) or (None, None, None, None, None, reason)."""
    found = find_marker(workdir)  # (folder, marker) or None, without reading it
    if found is None:
        return (None, None, None, None, None, None)  # no marker at all: silent
    try:
        f = find_run(workdir)
    except Damaged as e:  # a non-object marker, or a run folder outside the marker's
        return (None, None, None, None, None, str(e))  # folder: the check lives in find_run
    if not f:
        return (None, None, None, None, None, "the run marker is unreadable")
    wd, run_dir = f
    try:
        lines, st, card = _look(wd, run_dir)
    except Damaged as e:
        if "card" in str(e):  # a card change is not record damage: name the card
            return (None, None, None, None, None, "the run's card changed mid-run")
        return (None, None, None, None, None, "%s/record.jsonl is damaged"
                % _clean(os.path.basename(run_dir)))
    except (OSError, ValueError) as e:
        return (None, None, None, None, None, "the run's card is unreadable or changed (%s)" % _clean(e))
    return (wd, run_dir, lines, st, card, None)


def _offer(wd, cwd, lines, st, card):
    """The offer, under 400 characters. Every field from a file is filtered and cut."""
    total = len(card["stages"])
    i = stage_index(card, st["cur"])
    if i < 0:
        _can_t("the open step %r is not in the card" % _clean(st["cur"]))
        return
    mode = card["stages"][i].get("mode", "talk")
    skill = _clean(st["skill"] or "skill")
    n = i + 1
    age = _age(time.time(), lines[-1]["t"])
    infolder = ""
    if wd and cwd and os.path.realpath(wd) != os.path.realpath(cwd):
        infolder = ", in %s" % _clean(os.path.basename(wd))
    offer = ('Unfinished run here: %s, step %d/%d (%s). Ask: "Continue, start over, or leave '
             'it?" Then run stage_runner.py EXACTLY once: resume --choice continue (put the new '
             'code word in the step\'s output file) | abandon --choice start-over (only if '
             'plainly start over) | snooze --choice leave-it. Anything else (e.g. "skip the '
             'rest"): ask again, run nothing. Saved %s ago%s. Another window may be on it.'
             % (skill, n, total, mode, age, infolder))
    if len(offer) > MAX_OFFER:
        offer = offer[:MAX_OFFER]
    _say(offer)


def _reminder(lines, st, card):
    total = len(card["stages"])
    i = stage_index(card, st["cur"])
    if i < 0:
        _can_t("the open step %r is not in the card" % _clean(st["cur"]))
        return
    _say("Still on step %d/%d of %s. Carry on; if you lost this step's code word, run "
         "stage_runner.py resume --choice continue (it only reissues the word)."
         % (i + 1, total, _clean(st["skill"] or "skill")))


def cmd_session(a):
    """The pickup hook's one call. Reads stdin JSON (bad stdin -> cwd, source unknown).
    Silent on: no marker, LIFEHACK_JOB_RUN_ID set, finished/abandoned/snoozed run."""
    cwd, source = os.getcwd(), "unknown"
    try:
        j = json.loads(sys.stdin.read() or "{}")
        if isinstance(j, dict):
            cwd = j.get("cwd") if isinstance(j.get("cwd"), str) and j.get("cwd") else cwd
            source = j.get("source") if isinstance(j.get("source"), str) else source
    except (ValueError, OSError):
        pass  # bad stdin: cwd stays the process cwd, source unknown
    if os.environ.get("LIFEHACK_JOB_RUN_ID"):
        return 0  # an unattended session is never offered a pickup question
    wd, run_dir, lines, st, card, reason = _run_state(cwd)
    if wd is None and reason is None:
        return 0  # no run here: silent
    if reason:
        _can_t(reason)
        return 0
    if st["complete"] or st["cur"] == "COMPLETE" or st["abandoned"] or st["snoozed"]:
        return 0  # never offer the wrong thing (invariant 9)
    if source == "compact":
        _reminder(lines, st, card)
    else:  # startup, clear, resume, unknown: the offer
        _offer(wd, cwd, lines, st, card)
    return 0


def _current_mode(workdir):
    """(mode, None) or (None, reason). talk / alone / none — for the guard."""
    wd, run_dir, lines, st, card, reason = _run_state(workdir)
    if reason or wd is None:
        return None, reason
    if st["complete"] or st["cur"] == "COMPLETE":
        return "none", None
    i = stage_index(card, st["cur"])
    if i < 0:
        return None, "the open step is not in the card"
    return card["stages"][i].get("mode", "talk"), None


def cmd_mode(a):
    mode, _ = _current_mode(a.workdir)
    print(mode or "none")
    return 0


def cmd_where(a):
    """One human line: the same facts as the offer, for a skill asked 'where are we?'."""
    wd, run_dir, lines, st, card, reason = _run_state(a.workdir)
    if wd is None and reason is None:
        print("%s no run in this folder." % TAG)
        return 0
    if reason:
        print("%s can't pick up: %s." % (TAG, reason))
        return 0
    total = len(card["stages"])
    i = stage_index(card, st["cur"])
    if st["complete"] or st["cur"] == "COMPLETE":
        print("%s Run %s is finished (%d steps)." % (TAG, _clean(st["skill"] or "skill"), total))
        return 0
    if i < 0:
        print("%s can't pick up: the open step is not in the card." % TAG)
        return 0
    mode = card["stages"][i].get("mode", "talk")
    print("%s Run %s: step %d/%d (%s), saved %s ago."
          % (TAG, _clean(st["skill"] or "skill"), i + 1, total, mode,
             _age(time.time(), lines[-1]["t"])))
    return 0


def selftest():
    """The reader proves itself on both sides, in a temp folder with the real stage_runner:
    known-good (a mid-run is offered, tagged, <= 400 chars) and known-bad (a damaged record
    is a 'can't pick up'; a finished run is silent; a hostile name is filtered)."""
    import shutil
    import subprocess
    import tempfile
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f" [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("run_pickup --selftest (the read-only pickup reader, both sides)")
    runner = os.path.join(HERE, "stage_runner.py")

    def srun(args, wd):
        return subprocess.run([sys.executable, runner] + args + ["--workdir", wd],
            capture_output=True, text=True)

    def sess(wd):
        return subprocess.run([sys.executable, os.path.abspath(__file__), "session"],
            input=json.dumps({"cwd": wd, "source": "startup"}),
            capture_output=True, text=True, cwd=wd)

    with tempfile.TemporaryDirectory() as td:
        # card: two alone stages so the run can be driven with no person turns
        pdir = os.path.join(td, "prompts")
        os.makedirs(pdir)
        card = os.path.join(td, "card.json")
        stages = []
        for i, (sid, head) in enumerate((("gather", "## Gather"), ("finish", "## Finish"))):
            open(os.path.join(pdir, "%02d-%s.md" % (i + 1, sid)), "w", encoding="utf-8").write(
                "Step {{ID}} of {{TOTAL}}. Code word: {{CODE}}. Write to {{OUT}}.\n")
            stages.append({"id": sid, "mode": "alone", "prompt": "prompts/%02d-%s.md" % (i + 1, sid),
                "out": "out/%02d-%s.md" % (i + 1, sid),
                "checks": {"headings": [head], "min_words": 5, "code_word": True}})
        json.dump({"skill": "selftest", "stop_limit": 3, "stages": stages}, open(card, "w", encoding="utf-8"))

        # -- known-good: a mid-run gets the offer, tagged, <= 400 characters ------
        wd = os.path.join(td, "wd")
        os.makedirs(wd)
        p = srun(["start", "--card", card], wd)
        code = re.search(r"\): (RUN-[0-9A-Z]{6})", p.stdout)
        report("selftest: the runner starts the throwaway run", p.returncode == 0 and bool(code))
        q = sess(wd)
        lines = [l for l in q.stdout.splitlines() if l.strip()]
        offer = lines[0].split(TAG, 1)[1].strip() if lines and TAG in lines[0] else ""
        report("known-good: a mid-run gets ONE tagged offer line",
            q.returncode == 0 and len(lines) == 1 and lines[0].startswith(TAG)
            and "Unfinished run here:" in offer, (lines[0][:90] if lines else "no line"))
        report("known-good: the offer is within 400 characters", 0 < len(offer) <= 400,
            "len %d" % len(offer))

        # -- known-bad: a hostile skill name is filtered --------------------------
        hcard = os.path.join(td, "hostile.json")
        h = json.load(open(card, encoding="utf-8"))
        h["skill"] = "Evil<script>alert(1)</script>&drop\ttab"
        json.dump(h, open(hcard, "w", encoding="utf-8"))
        hwd = os.path.join(td, "hwd")
        os.makedirs(hwd)
        srun(["start", "--card", hcard], hwd)
        q = sess(hwd)
        hostile = [l for l in q.stdout.splitlines() if l.strip()]
        report("known-bad: a hostile name is filtered to the safe set",
            len(hostile) == 1 and "Evilscriptalert1/scriptdroptab" in hostile[0]
            and not re.search(r"[<>&\t]", hostile[0]),
            hostile[0][-70:] if hostile else "no line")

        # -- known-bad: a damaged record is a "can't pick up" ---------------------
        recp = os.path.join(wd, "runs", os.listdir(os.path.join(wd, "runs"))[0], "record.jsonl")
        objs = [json.loads(l) for l in open(recp, encoding="utf-8")]
        objs[0]["data"]["skill"] = (objs[0]["data"].get("skill") or "") + "x"
        open(recp, "w", encoding="utf-8").write(
            "".join(json.dumps(o, sort_keys=True) + "\n" for o in objs))
        q = sess(wd)
        dmg = [l for l in q.stdout.splitlines() if l.strip()]
        report("known-bad: a damaged record is one 'can't pick up' line, exit 0",
            q.returncode == 0 and len(dmg) == 1 and "can't pick up" in dmg[0]
            and dmg[0].startswith(TAG), dmg[0][-80:] if dmg else "no line")

        # -- known-bad: a finished run is silent ----------------------------------
        fwd = os.path.join(td, "fwd")
        os.makedirs(fwd)
        p = srun(["start", "--card", card], fwd)
        code1 = re.search(r"\): (RUN-[0-9A-Z]{6})", p.stdout).group(1)
        rid = os.listdir(os.path.join(fwd, "runs"))[0]
        rd = os.path.join(fwd, "runs", rid)
        open(os.path.join(rd, "out", "01-gather.md"), "w", encoding="utf-8").write(
            "## Gather\n\nThe gathered words for this selftest step are here.\n\nCode word: %s\n" % code1)
        p = srun(["advance"], fwd)
        code2 = re.search(r"(RUN-[0-9A-Z]{6})", p.stdout).group(1)
        open(os.path.join(rd, "out", "02-finish.md"), "w", encoding="utf-8").write(
            "## Finish\n\nThe finishing words for this selftest step are here.\n\nCode word: %s\n" % code2)
        p = srun(["advance"], fwd)
        report("selftest: the throwaway run completes", p.returncode == 0
            and "complete" in p.stdout.lower(), p.stdout.strip()[:60])
        q = sess(fwd)
        report("known-bad: a finished run is SILENT", q.returncode == 0 and not q.stdout.strip(),
            repr(q.stdout[:60]))

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1

def main():
    import argparse
    ap = argparse.ArgumentParser(prog="run_pickup.py",
                                 description="the read-only run-pickup reader (spec G4)")
    ap.add_argument("--workdir", default=os.getcwd())
    sp = ap.add_subparsers(dest="cmd")

    def sub(name, help_):
        s = sp.add_parser(name, help=help_)
        s.add_argument("--workdir", default=os.getcwd())
        return s

    sub("session", "stdin: the SessionStart payload; prints the offer/reminder or nothing")
    sub("mode", "print talk|alone|none for the current step (for the guard)")
    sub("where", "one human line: where the run is")
    ap.add_argument("--selftest", action="store_true",
        help="run the two-sided self-test (known-good and known-bad)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "session":
        return cmd_session(a)
    if a.cmd == "mode":
        return cmd_mode(a)
    if a.cmd == "where":
        return cmd_where(a)
    ap.print_usage()
    return 2


if __name__ == "__main__":
    sys.exit(main())
