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
    except Damaged:
        return (None, None, None, None, None, "the run marker is not a JSON object naming a run folder")
    if not f:
        return (None, None, None, None, None, "the run marker is unreadable")
    wd, run_dir = f
    rwd, rrun = os.path.realpath(wd), os.path.realpath(run_dir)  # /tmp is a symlink on macOS
    if not (rrun + os.sep).startswith(rwd + os.sep) and rrun != rwd:
        return (None, None, None, None, None, "run folder outside this folder")
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
    a = ap.parse_args()
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
