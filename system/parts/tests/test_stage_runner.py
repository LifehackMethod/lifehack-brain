#!/usr/bin/env python3
"""test_stage_runner — the no-AI finish check for system/parts/stage_runner.py (plan 4P.0a).

Black-box: drives the runner's real CLI only (subprocesses), never imports it.

Finish check (plan row 4P.0a, no AI):
  (1) a record edited by hand in a temp copy is reported DAMAGED with its exit code
      and the runner refuses to advance;
  (2) a stage run out of order is refused;
  (3) a planted card naming a missing check part is refused.

Each is shown FAILING FIRST: the same check is run against a deliberately broken runner
variant (built in a temp dir, one verification sabotaged) and must fail there.

Usage: python3 system/parts/tests/test_stage_runner.py
Exit 0 only if every check passes against the real runner AND fails against each broken
variant. A check that cannot be made to fail is a finding, not a pass.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "..", "stage_runner.py")

OK, USAGE, CHECKFAIL, NOTHING, NORUN, DAMAGED, DANGLING = 0, 2, 3, 4, 5, 6, 7
CARDCHANGED = 8

_results = []


def report(label, passed, detail=""):
    _results.append(passed)
    print(" [%s] %s%s" % ("PASS" if passed else "FAIL", label,
                          (" -- " + detail) if detail else ""))


def run(args, runner=RUNNER):
    return subprocess.run([sys.executable, os.path.abspath(runner)] + args,
                          capture_output=True, text=True)


def make_card(td):
    """Two-stage card + prompt files, no AI: talk stage, then an alone stage."""
    pdir = os.path.join(td, "prompts")
    os.makedirs(pdir, exist_ok=True)
    open(os.path.join(pdir, "01-gather.md"), "w", encoding="utf-8").write(
        "Stage {{ID}} of {{TOTAL}} ({{MODE}}). Write to {{OUT}}.\n")
    open(os.path.join(pdir, "02-analyze.md"), "w", encoding="utf-8").write(
        "Stage {{ID}}. Your code word: {{CODE}}. Previous output: {{PREV}}. Write to {{OUT}}.\n")
    card = {"skill": "test", "stop_limit": 3, "stages": [
        {"id": "gather", "mode": "talk", "prompt": "prompts/01-gather.md", "out": "out/01-gather.md",
         "checks": {"headings": ["## Gather"], "min_words": 10, "code_word": True}},
        {"id": "analyze", "mode": "alone", "prompt": "prompts/02-analyze.md", "out": "out/02-analyze.md",
         "checks": {"headings": ["## Analyze"], "min_words": 10, "code_word": True}},
    ]}
    p = os.path.join(td, "card.json")
    json.dump(card, open(p, "w", encoding="utf-8"))
    return p


def build_fixture(td):
    """A complete two-stage run, no AI: start, satisfy stage 1, advance, satisfy stage 2, advance."""
    card = make_card(td)
    wd = os.path.join(td, "fixture")
    os.makedirs(wd)
    p = run(["start", "--card", card, "--workdir", wd])
    assert p.returncode == OK, p.stdout + p.stderr
    code1 = re.search(r"code word for stage gather \(print once, never store\): (RUN-[0-9A-Z]{6})",
                      p.stdout).group(1)
    rid = os.listdir(os.path.join(wd, "runs"))[0]
    open(os.path.join(wd, "runs", rid, "out", "01-gather.md"), "w", encoding="utf-8").write(
        "## Gather\n\nThe week's frame is gathered from the sources and written here in full.\n\n"
        "Code word: %s\n" % code1)
    p = person_advance(wd, "fx1")
    assert p.returncode == OK, p.stdout + p.stderr
    open(os.path.join(wd, "runs", rid, "mover.log"), "w", encoding="utf-8").write("fx1\n")  # what the mover logs
    code2 = re.search(r"(RUN-[0-9A-Z]{6})", p.stdout).group(1)
    open(os.path.join(wd, "runs", rid, "out", "02-analyze.md"), "w", encoding="utf-8").write(
        "## Analyze\n\nThe analysis follows from the gathered frame, complete and checked.\n\n"
        "Code word: %s\n" % code2)
    p = run(["advance", "--workdir", wd])
    assert p.returncode == OK and "complete" in p.stdout.lower(), p.stdout + p.stderr
    return wd, rid


def person_advance(wd, turn):
    """The person types /next: person-turn, then advance --turn (what the mover does)."""
    q = run(["person-turn", "--turn", turn, "--cmd", "next", "--workdir", wd])
    assert q.returncode == OK, q.stdout + q.stderr
    return run(["advance", "--turn", turn, "--workdir", wd])


def repoint_marker(wd, rid):
    """The run marker names the run dir by absolute path; a copied run points at ITS copy."""
    json.dump({"run_dir": os.path.join(wd, "runs", rid), "run_id": rid},
              open(os.path.join(wd, ".stage-runner.json"), "w", encoding="utf-8"))


def damage_record(wd, rid, how="mid"):
    """Edit the copy's record by hand. Returns the edited path."""
    recp = os.path.join(wd, "runs", rid, "record.jsonl")
    lines = open(recp, encoding="utf-8").read().splitlines(True)
    if how == "mid":
        obj = json.loads(lines[len(lines) // 2])
        # change only the timestamp: the replay rule cannot see it, ONLY the hash chain can,
        # so the chain-sabotaged runner still misses it (the failing-first stays meaningful)
        obj["t"] = obj["t"] + 1.0
        lines[len(lines) // 2] = json.dumps(obj, sort_keys=True) + "\n"
    elif how == "tail":
        open(recp, "w", encoding="utf-8").write("".join(lines).rstrip("\n"))
        return recp
    open(recp, "w", encoding="utf-8").write("".join(lines))
    return recp


def broken_variant(td, sabotage):
    """Copy the runner with ONE verification deliberately broken."""
    src = open(os.path.abspath(RUNNER), encoding="utf-8").read()
    marks = {
        # chain verification neutered: a damaged record reads as OK
        "chain": ('            assert o["seq"] == i and o["prev"] == prev and _hash(prev, o) == h',
                  '            assert o["seq"] == i'),
        # stage checks neutered: an unmet stage advances
        "gate": ('        problems = run_checks(card, stage, run_dir, st["code"], st["superseded"])',
                 '        problems = []'),
    }
    old, new = marks[sabotage]
    assert old in src, "sabotage anchor %r not found -- the runner changed shape" % sabotage
    dst = os.path.join(td, "broken_%s.py" % sabotage)
    open(dst, "w", encoding="utf-8").write(src.replace(old, new))
    return dst


def main():
    print("test_stage_runner — the no-AI finish check for stage_runner.py")
    with tempfile.TemporaryDirectory() as td:
        wd, rid = build_fixture(td)
        n_lines = len(open(os.path.join(wd, "runs", rid, "record.jsonl"), encoding="utf-8").read().splitlines())

        # ---------- plant (1): hand-edited record in a copy ----------
        copy = os.path.join(td, "copy-damaged")
        shutil.copytree(wd, copy)
        repoint_marker(copy, rid)
        recp = damage_record(copy, rid)
        p = run(["verify", "--workdir", copy])
        report("(1) hand-edited record reported DAMAGED with exit 6",
               p.returncode == DAMAGED and p.stdout.startswith("DAMAGED:"),
               "exit %d %s" % (p.returncode, p.stdout.strip()))
        before = open(recp, encoding="utf-8").read()
        p = run(["advance", "--workdir", copy])
        report("(1) advance refuses on the damaged record and writes nothing",
               p.returncode == DAMAGED and open(recp, encoding="utf-8").read() == before,
               "exit %d" % p.returncode)
        # torn tail: same exit code
        damage_record(copy, rid, how="tail")
        p = run(["verify", "--workdir", copy])
        report("(1) torn tail (no final newline) reported DAMAGED with exit 6",
               p.returncode == DAMAGED, "exit %d" % p.returncode)
        # FAILING FIRST, against the chain-sabotaged runner
        bcopy = os.path.join(td, "broken-chain-copy")
        shutil.copytree(wd, bcopy)
        repoint_marker(bcopy, rid)
        damage_record(bcopy, rid)
        bv = run(["verify", "--workdir", bcopy], runner=broken_variant(td, "chain"))
        report("(1) FAILING-FIRST: the broken runner MISSES the hand-edited record",
               bv.returncode == OK, "broken exit %d" % bv.returncode)
        rv = run(["verify", "--workdir", bcopy])
        report("(1) ...and the real runner CATCHES it", rv.returncode == DAMAGED,
               "exit %d" % rv.returncode)

        # ---------- plant (2): stage run out of order ----------
        fresh = os.path.join(td, "fresh")
        os.makedirs(fresh)
        card = make_card(td)
        p = run(["start", "--card", card, "--workdir", fresh])
        frid = os.listdir(os.path.join(fresh, "runs"))[0]
        p = person_advance(fresh, "f1")
        report("(2) advancing past an unmet stage exits CHECKFAIL", p.returncode == CHECKFAIL,
               "exit %d" % p.returncode)
        raw = open(os.path.join(fresh, "runs", frid, "record.jsonl"), encoding="utf-8").read()
        pass_lines = [l for l in raw.splitlines()
                      if '"event": "pass"' in l and '"stage": "analyze"' in l]
        report("(2) no pass for stage 2 exists in the record while stage 1 is unmet",
               pass_lines == [], "%d pass lines for stage 2" % len(pass_lines))
        p = run(["check", "--workdir", fresh])
        report("(2) check on the unmet stage exits CHECKFAIL", p.returncode == CHECKFAIL,
               "exit %d" % p.returncode)
        # FAILING FIRST, against the gate-sabotaged runner
        gcopy = os.path.join(td, "broken-gate-copy")
        shutil.copytree(fresh, gcopy)
        repoint_marker(gcopy, frid)
        run(["person-turn", "--turn", "g1", "--cmd", "next", "--workdir", gcopy])
        bg = run(["advance", "--turn", "g1", "--workdir", gcopy], runner=broken_variant(td, "gate"))
        report("(2) FAILING-FIRST: the broken runner ADVANCES past the unmet stage",
               bg.returncode == OK, "broken exit %d" % bg.returncode)
        rg = person_advance(fresh, "f2")
        report("(2) ...and the real runner REFUSES it", rg.returncode == CHECKFAIL,
               "exit %d" % rg.returncode)

        # ---------- plant (3): card naming a missing check part ----------
        # the runner finds its delegate parts beside ITSELF; a lone copy has none
        lone = os.path.join(td, "lone")
        os.makedirs(lone)
        shutil.copy(os.path.abspath(RUNNER), os.path.join(lone, "stage_runner.py"))
        lcard = os.path.join(lone, "card.json")
        json.dump({"skill": "s", "stages": [{"id": "a", "mode": "talk", "out": "out/a.md",
                                             "checks": {"forbid": [{"id": "x", "term": "y"}]}}]},
                  open(lcard, "w", encoding="utf-8"))
        p = run(["start", "--card", lcard, "--workdir", os.path.join(lone, "wd")],
                runner=os.path.join(lone, "stage_runner.py"))
        report("(3) card naming a missing check part refused at start (exit 2, fail-closed)",
               p.returncode == USAGE and "forbidden_content.py" in (p.stdout + p.stderr),
               "exit %d %s" % (p.returncode, (p.stdout + p.stderr).strip()[:90]))
        report("(3) nothing was written for the refused card",
               not os.path.exists(os.path.join(lone, "wd", ".stage-runner.json")))
        # FAILING FIRST: the same card against the REAL runner (part present) starts fine,
        # so prove the refusal is the missing PART, not the card shape, by inverting:
        p2 = run(["start", "--card", lcard, "--workdir", os.path.join(td, "ok-wd")])
        report("(3) control: the same card starts fine when the part IS beside the runner",
               p2.returncode == OK, "exit %d" % p2.returncode)

        # ---------- record sanity ----------
        p = run(["verify", "--workdir", wd])
        report("the untouched fixture still verifies (OK %d lines)" % n_lines,
               p.returncode == OK and ("OK %d lines" % n_lines) in p.stdout, p.stdout.strip())

    print("TEST:", "PASS" if all(_results) else "FAIL")
    return 0 if all(_results) else 1


# ======================================================================================
# Run-pickup phase 1 (spec G1 / G7): the person-turn rule, resume / abandon / snooze,
# start-after-finish, card_sha, the replay rule, mover.log. pytest style; every test
# drives the real CLI in a temp folder (never a real run). Run:
#   python3 -m pytest system/parts/tests/test_stage_runner.py -q
# ======================================================================================
import glob
import hashlib
import time

TOOK = "another window took over this run at"
OLD_NEXT = ("---\ndescription: move to the next stage of the run\n---\n"
            "The runner code already ran before you saw this message. Follow the handover "
            "injected for you this turn. If none was injected, say there is nothing new.\n")
NEW_BODY = ("The mover ran before you saw this, if a [RUN STEP] line is above. "
            "If there is none, the mover didn't run: tell the person.")
STEP_FILES = ("01-gather", "02-shape", "03-finish")
HEADS = ("## Gather", "## Shape", "## Finish")
GENESIS = "0" * 64


def card3(td, modes=("talk", "talk", "alone"), extra_inputs=None):
    pdir = os.path.join(td, "prompts")
    os.makedirs(pdir, exist_ok=True)
    stages = []
    for i, (f, h) in enumerate(zip(STEP_FILES, HEADS)):
        sid = f.split("-", 1)[1]
        open(os.path.join(pdir, f + ".md"), "w", encoding="utf-8").write(
            "Step {{ID}} of {{TOTAL}} ({{MODE}}). Code word: {{CODE}}. Write to {{OUT}}.\n")
        st = {"id": sid, "mode": modes[i], "prompt": "prompts/%s.md" % f, "out": "out/%s.md" % f,
              "checks": {"headings": [h], "min_words": 5, "code_word": True}}
        if extra_inputs and i == 1:
            st["inputs"] = extra_inputs
        stages.append(st)
    p = os.path.join(td, "card.json")
    json.dump({"skill": "ptest", "stop_limit": 3, "stages": stages}, open(p, "w", encoding="utf-8"))
    return p


class R(object):
    """One temp run, driven through the real CLI."""

    def __init__(self, tmp_path, modes=("talk", "talk", "alone"), extra_inputs=None, start=True):
        self.td = str(tmp_path)
        self.card = card3(self.td, modes, extra_inputs)
        self.wd = os.path.join(self.td, "wd")
        os.makedirs(self.wd)
        self.rid = None
        self.code = None
        if start:
            self.start()

    def cmd(self, *args):
        return run(list(args) + ["--workdir", self.wd])

    def start(self):
        p = run(["start", "--card", self.card, "--workdir", self.wd])
        assert p.returncode == OK, p.stdout + p.stderr
        self.code = re.search(r"\((?:print once, never store)\): (RUN-[0-9A-Z]{6})", p.stdout).group(1)
        self.rid = json.load(open(os.path.join(self.wd, ".stage-runner.json"), encoding="utf-8"))["run_id"]
        return p

    @property
    def run_dir(self):
        return os.path.join(self.wd, "runs", self.rid)

    def lines(self):
        return [json.loads(l) for l in open(os.path.join(self.run_dir, "record.jsonl"), encoding="utf-8")]

    def events(self):
        return [l["event"] for l in self.lines()]

    def write(self, i, code=None, body=None):
        code = code or self.code
        open(os.path.join(self.run_dir, "out", STEP_FILES[i] + ".md"), "w", encoding="utf-8").write(
            body if body is not None else
            "%s\n\nThe words written for this step are here in full and complete.\n\nCode word: %s\n"
            % (HEADS[i], code))

    def person(self, turn, c):
        return self.cmd("person-turn", "--turn", turn, "--cmd", c)

    def answer(self, pid=None):
        """The person answers (the mover logs the prompt id to person.log); -> the pid."""
        n = getattr(self, "_ans", 0) + 1
        self._ans = n
        pid = pid or ("ans%d" % n)
        with open(os.path.join(self.run_dir, "person.log"), "a", encoding="utf-8") as f:
            f.write("%s\t%.3f\n" % (pid, time.time()))
        return pid

    def adv(self, turn=None):
        return self.cmd(*(["advance", "--turn", turn] if turn else ["advance"]))

    def bk(self, turn=None):
        return self.cmd(*(["back", "--turn", turn] if turn else ["back"]))

    def step(self):
        return json.loads(self.cmd("status", "--json").stdout)

    def move(self, turn):
        """The person types /next: person-turn then advance, as the mover will. Returns advance's proc;
        remembers the new code word."""
        assert self.person(turn, "next").returncode == OK
        p = self.adv(turn)
        m = re.search(r"(RUN-[0-9A-Z]{6})", p.stdout)
        if p.returncode == OK and m:
            self.code = m.group(1)
        return p

    def to_step(self, n):
        """Walk to step index n (0-based) through verified person turns."""
        k = 0
        while self.step()["index"] - 1 < n:
            self.write(self.step()["index"] - 1)
            p = self.move("w%d" % k)
            assert p.returncode == OK, p.stdout
            k += 1


def _h(prev, o):
    body = json.dumps(o, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((prev + "\n" + body).encode()).hexdigest()


def rewrite_record(run_dir, drop):
    """Rebuild the record with a VALID chain, minus every line `drop` selects (a forger's rebuild)."""
    recp = os.path.join(run_dir, "record.jsonl")
    objs = [json.loads(l) for l in open(recp, encoding="utf-8")]
    for o in objs:
        o.pop("hash")
    objs = [o for o in objs if not drop(o)]
    prev, out = GENESIS, []
    for i, o in enumerate(objs):
        o["seq"], o["prev"] = i, prev
        h = _h(prev, o)
        o["hash"] = h
        out.append(json.dumps(o, sort_keys=True))
        prev = h
    open(recp, "w", encoding="utf-8").write("\n".join(out) + "\n")


def text(p):
    return p.stdout + p.stderr


# ---------------------------------------------------------------- person-turn
def test_person_turn_appends_a_person_line(tmp_path):
    r = R(tmp_path)
    p = r.person("t1", "next")
    assert p.returncode == OK, text(p)
    last = r.lines()[-1]
    assert last["event"] == "person" and last["data"]["turn"] == "t1" and last["data"]["cmd"] == "next"


def test_person_turn_used_turn_is_exit_4(tmp_path):
    r = R(tmp_path)
    assert r.person("t1", "next").returncode == OK
    n = len(r.lines())
    p = r.person("t1", "next")
    assert p.returncode == NOTHING, text(p)
    assert len(r.lines()) == n


def test_person_turn_needs_turn_and_a_valid_cmd(tmp_path):
    r = R(tmp_path)
    assert r.cmd("person-turn", "--cmd", "next").returncode == USAGE
    assert r.cmd("person-turn", "--turn", "t1", "--cmd", "sideways").returncode == USAGE
    assert "person" not in r.events()


def test_person_turn_with_no_run_is_exit_5(tmp_path):
    r = R(tmp_path, start=False)
    assert r.person("t1", "next").returncode == NORUN


def test_person_turn_on_a_complete_run_is_nothing_to_do(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    r.write(2)
    assert r.move("z").returncode == OK
    assert r.person("late", "next").returncode == NOTHING


# ---------------------------------------------------------------- advance on a talk step
def test_talk_advance_without_a_person_turn_is_exit_3(tmp_path):
    r = R(tmp_path)
    r.write(0)
    p = r.adv()
    assert p.returncode == CHECKFAIL and "no person turn" in text(p).lower(), text(p)
    p = r.adv("never-logged")
    assert p.returncode == CHECKFAIL and "no person turn" in text(p).lower(), text(p)
    assert r.step()["index"] == 1 and "pass" not in r.events()


def test_talk_advance_with_a_person_next_moves_one_step(tmp_path):
    r = R(tmp_path)
    r.write(0)
    p = r.move("t1")
    assert p.returncode == OK, text(p)
    assert r.step()["index"] == 2


def test_talk_advance_repeat_turn_is_exit_4_and_moves_nothing(tmp_path):
    r = R(tmp_path)
    r.write(0)
    assert r.move("t1").returncode == OK
    r.write(1)
    p = r.adv("t1")
    assert p.returncode == NOTHING, text(p)
    assert r.step()["index"] == 2


def test_talk_advance_refuses_a_person_back_line(tmp_path):
    r = R(tmp_path)
    r.write(0)
    assert r.person("t1", "back").returncode == OK
    p = r.adv("t1")
    assert p.returncode == CHECKFAIL and "no person turn" in text(p).lower()
    assert r.step()["index"] == 1


def test_a_person_line_is_consumed_by_its_first_use_even_when_it_fails(tmp_path):
    r = R(tmp_path)
    assert r.person("t1", "next").returncode == OK
    p = r.adv("t1")                      # step 1 output missing: check fails
    assert p.returncode == CHECKFAIL, text(p)
    r.write(0)
    p = r.adv("t1")                      # same turn again, now it would pass: still refused
    assert p.returncode == NOTHING, text(p)
    assert r.step()["index"] == 1
    assert r.move("t2").returncode == OK and r.step()["index"] == 2


def test_alone_step_advances_on_a_verified_pass_without_a_person(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    r.write(2)
    p = r.adv()
    assert p.returncode == OK and r.step()["complete"] is True, text(p)


def test_alone_step_still_refused_when_unmet(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    assert r.adv().returncode == CHECKFAIL


# ---------------------------------------------------------------- back
def test_back_goes_back_exactly_one_step_on_a_person_turn(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    assert r.person("b1", "back").returncode == OK
    p = r.bk("b1")
    assert p.returncode == OK, text(p)
    assert r.step()["index"] == 2
    assert "FRESH code word" in p.stdout or "fresh" in p.stdout.lower()


def test_back_without_a_person_turn_is_exit_3(tmp_path):
    r = R(tmp_path)
    r.to_step(1)
    p = r.bk()
    assert p.returncode == CHECKFAIL and "no person turn" in text(p).lower(), text(p)
    assert r.step()["index"] == 2
    p = r.bk("nobody")
    assert p.returncode == CHECKFAIL
    assert r.step()["index"] == 2


def test_back_repeat_turn_is_exit_4_double_back_is_one_step(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    assert r.person("b1", "back").returncode == OK
    assert r.bk("b1").returncode == OK
    assert r.person("b1", "back").returncode == NOTHING     # same turn id typed twice
    assert r.bk("b1").returncode == NOTHING
    assert r.step()["index"] == 2


def test_back_refuses_a_person_next_line(tmp_path):
    r = R(tmp_path)
    r.to_step(1)
    assert r.person("t9", "next").returncode == OK
    assert r.bk("t9").returncode == CHECKFAIL
    assert r.step()["index"] == 2


def test_back_at_the_first_step_is_nothing_and_still_consumes_the_turn(tmp_path):
    r = R(tmp_path)
    assert r.person("b1", "back").returncode == OK
    assert r.bk("b1").returncode == NOTHING
    r.write(0)
    assert r.person("b2", "next").returncode == OK
    # the consumed back turn cannot be replayed as anything
    assert r.bk("b1").returncode == NOTHING
    assert any(l["data"].get("turn") == "b1" and l["event"] != "person" for l in r.lines())


# ---------------------------------------------------------------- resume
def test_resume_reissues_the_current_step_with_a_fresh_code_word(tmp_path):
    r = R(tmp_path)
    r.to_step(1)
    before = r.events()
    r.answer()
    p = r.cmd("resume", "--choice", "continue")
    assert p.returncode == OK, text(p)
    new = re.search(r"(RUN-[0-9A-Z]{6})", p.stdout).group(1)
    assert new != r.code
    assert "Code word line in" in p.stdout and "02-shape.md" in p.stdout
    assert "Step shape of 3" in p.stdout                       # the CURRENT step's instructions
    after = r.events()
    assert after[:len(before)] == before and after[len(before):] == ["reissue"]
    assert r.lines()[-1]["data"]["choice"] == "continue"
    assert not {"pass", "done", "complete"} & set(after[len(before):])
    assert r.step()["index"] == 2


def test_resume_on_a_dangling_handover_is_exit_7(tmp_path):
    r = R(tmp_path)
    r.write(0)
    assert r.move("t1").returncode == OK
    rewrite_record(r.run_dir, lambda o: o["event"] == "done" and o["stage"] == "shape")  # crash before done
    r.answer()
    p = r.cmd("resume", "--choice", "continue")
    assert p.returncode == DANGLING and "recover first" in text(p), text(p)
    assert "reissue" not in r.events()


def test_resume_on_a_finished_run_is_exit_4(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    r.write(2)
    assert r.adv().returncode == OK
    n = len(r.lines())
    r.answer()
    assert r.cmd("resume", "--choice", "continue").returncode == NOTHING
    assert len(r.lines()) == n


def test_resume_on_an_abandoned_run_is_exit_4(tmp_path):
    r = R(tmp_path)
    r.answer()
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    shutil.copy(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid),
                os.path.join(r.wd, ".stage-runner.json"))      # a stale marker pointing at it
    r.answer()
    assert r.cmd("resume", "--choice", "continue").returncode == NOTHING


def test_resume_choice_is_validated(tmp_path):
    r = R(tmp_path)
    n = len(r.lines())
    for bad in ("go", "start-over", "leave-it", ""):
        r.answer()
        p = r.cmd("resume", "--choice", bad)
        assert p.returncode == USAGE and "ask the person again" in text(p).lower(), (bad, text(p))
    r.answer()
    assert r.cmd("resume").returncode == USAGE
    assert len(r.lines()) == n


def test_old_code_word_is_refused_after_resume_with_the_taken_over_message(tmp_path):
    r = R(tmp_path)
    old = r.code
    r.answer()
    assert r.cmd("resume", "--choice", "continue").returncode == OK
    r.write(0, code=old)
    c = r.cmd("check")
    assert c.returncode == CHECKFAIL and TOOK in text(c), text(c)
    assert r.person("t1", "next").returncode == OK
    p = r.adv("t1")
    assert p.returncode == CHECKFAIL and TOOK in text(p), text(p)
    assert r.step()["index"] == 1


def test_a_wrong_word_that_was_never_issued_is_not_called_a_takeover(tmp_path):
    r = R(tmp_path)
    r.write(0, code="RUN-ZZZZZZ")
    c = r.cmd("check")
    assert c.returncode == CHECKFAIL and TOOK not in text(c)


def test_the_new_code_word_passes_after_resume(tmp_path):
    r = R(tmp_path)
    r.answer()
    p = r.cmd("resume", "--choice", "continue")
    new = re.search(r"(RUN-[0-9A-Z]{6})", p.stdout).group(1)
    r.write(0, code=new)
    assert r.cmd("check").returncode == OK
    assert r.move("t1").returncode == OK


def test_resume_then_advance_with_failing_output_is_refused(tmp_path):
    r = R(tmp_path)
    r.answer()
    assert r.cmd("resume", "--choice", "continue").returncode == OK
    r.write(0, body="## Gather\n\ntoo short\n")
    assert r.person("t1", "next").returncode == OK
    assert r.adv("t1").returncode == CHECKFAIL
    assert r.step()["index"] == 1 and "pass" not in r.events()


# ---------------------------------------------------------------- abandon
def test_abandon_appends_abandoned_and_moves_the_marker_aside(tmp_path):
    r = R(tmp_path)
    r.to_step(1)
    before = r.events()
    r.answer()
    p = r.cmd("abandon", "--choice", "start-over")
    assert p.returncode == OK, text(p)
    assert not os.path.exists(os.path.join(r.wd, ".stage-runner.json"))
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid))
    after = r.events()
    assert after[:len(before)] == before and after[len(before):] == ["abandoned"]
    assert not {"pass", "done", "complete"} & set(after[len(before):])
    assert os.path.isfile(os.path.join(r.run_dir, "record.jsonl"))          # nothing deleted
    assert r.cmd("status").returncode == NORUN


def test_abandon_choice_is_validated_and_touches_nothing(tmp_path):
    r = R(tmp_path)
    for bad in ("continue", "leave-it", "nope"):
        r.answer()
        p = r.cmd("abandon", "--choice", bad)
        assert p.returncode == USAGE and "ask the person again" in text(p).lower(), (bad, text(p))
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json"))
    assert "abandoned" not in r.events()


def test_abandon_works_on_a_damaged_record(tmp_path):
    r = R(tmp_path)
    damage_record(r.wd, r.rid)
    r.answer()
    p = r.cmd("abandon", "--choice", "start-over")
    assert p.returncode == OK, text(p)
    assert not os.path.exists(os.path.join(r.wd, ".stage-runner.json"))
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid))


def test_abandon_works_on_an_unreadable_card(tmp_path):
    r = R(tmp_path)
    os.remove(r.card)
    r.answer()
    p = r.cmd("abandon", "--choice", "start-over")
    assert p.returncode == OK, text(p)
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid))
    assert "abandoned" in r.events()                         # the record itself still verifies
    assert not {"pass", "done", "complete"} & set(r.events()[-1:])


def test_status_json_exposes_abandoned_and_snoozed(tmp_path):
    r = R(tmp_path)
    j = r.step()
    assert j["snoozed"] is False and j["abandoned"] is False
    r.answer()
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    shutil.copy(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid),
                os.path.join(r.wd, ".stage-runner.json"))
    j = r.step()
    assert j["abandoned"] is True


# ---------------------------------------------------------------- snooze
def test_snooze_appends_snoozed_and_a_later_resume_lifts_it(tmp_path):
    r = R(tmp_path)
    r.answer()
    p = r.cmd("snooze", "--choice", "leave-it")
    assert p.returncode == OK, text(p)
    assert r.lines()[-1]["event"] == "snoozed" and r.lines()[-1]["data"]["choice"] == "leave-it"
    assert r.step()["snoozed"] is True
    r.answer()
    assert r.cmd("resume", "--choice", "continue").returncode == OK
    assert r.step()["snoozed"] is False


def test_a_later_person_line_also_lifts_the_snooze(tmp_path):
    r = R(tmp_path)
    r.answer()
    assert r.cmd("snooze", "--choice", "leave-it").returncode == OK
    assert r.step()["snoozed"] is True
    assert r.person("t1", "next").returncode == OK
    assert r.step()["snoozed"] is False


def test_snooze_choice_is_validated(tmp_path):
    r = R(tmp_path)
    for bad in ("continue", "start-over", "later"):
        r.answer()
        p = r.cmd("snooze", "--choice", bad)
        assert p.returncode == USAGE and "ask the person again" in text(p).lower(), (bad, text(p))
    assert "snoozed" not in r.events()


# ---------------------------------------------------------------- start
def test_start_stores_the_card_sha(tmp_path):
    r = R(tmp_path)
    sha = r.lines()[0]["data"].get("card_sha")
    assert isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha), sha


def test_start_on_an_unfinished_run_is_exit_4(tmp_path):
    r = R(tmp_path)
    n = len(r.lines())
    p = run(["start", "--card", r.card, "--workdir", r.wd])
    assert p.returncode == NOTHING, text(p)
    assert len(r.lines()) == n and os.path.isfile(os.path.join(r.wd, ".stage-runner.json"))


def test_start_after_a_complete_run_renames_the_marker_and_begins_a_new_run(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    r.write(2)
    assert r.adv().returncode == OK
    old_rid, old_code = r.rid, r.code
    old_events = r.events()
    r.start()
    assert r.rid != old_rid
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json.done-" + old_rid))
    assert r.step()["index"] == 1 and r.step()["complete"] is False
    assert r.events() == ["start"]
    # the OLD run's code words fail in the new run, nothing is skipped
    r.write(0, code=old_code)
    assert r.cmd("check").returncode == CHECKFAIL
    assert r.person("n1", "next").returncode == OK
    assert r.adv("n1").returncode == CHECKFAIL
    # the old record is untouched
    old = [json.loads(l)["event"] for l in
           open(os.path.join(r.wd, "runs", old_rid, "record.jsonl"), encoding="utf-8")]
    assert old == old_events


def test_start_after_abandon_begins_a_new_run_from_step_1(tmp_path):
    r = R(tmp_path)
    r.to_step(1)
    old = r.rid
    r.answer()
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    r.start()
    assert r.rid != old and r.step()["index"] == 1
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json.abandoned-" + old))


# ---------------------------------------------------------------- card changed mid-run
def test_card_edited_mid_run_is_card_updated(tmp_path):
    r = R(tmp_path)
    c = json.load(open(r.card, encoding="utf-8"))
    c["stages"][0]["checks"]["min_words"] = 1
    json.dump(c, open(r.card, "w", encoding="utf-8"))
    for args in (["status"], ["check"], ["advance"], ["resume", "--choice", "continue"]):
        p = r.cmd(*args)
        assert p.returncode == CARDCHANGED and "CARD UPDATED" in text(p) and "card changed mid-run" in text(p), (args, text(p))


def test_prompt_file_edited_mid_run_is_card_updated(tmp_path):
    r = R(tmp_path)
    open(os.path.join(r.td, "prompts", "02-shape.md"), "a", encoding="utf-8").write("sneaky extra line\n")
    p = r.cmd("status")
    assert p.returncode == CARDCHANGED and "card changed mid-run" in text(p), text(p)


def test_unedited_card_is_not_damaged(tmp_path):
    r = R(tmp_path)
    assert r.cmd("status").returncode == OK


# ---------------------------------------------------------------- replay rule
def test_done_without_a_pass_of_the_step_before_is_damaged(tmp_path):
    r = R(tmp_path)
    r.write(0)
    assert r.move("t1").returncode == OK
    rewrite_record(r.run_dir, lambda o: o["event"] == "pass" and o["stage"] == "gather")
    p = r.cmd("verify")
    assert p.returncode == DAMAGED and p.stdout.startswith("DAMAGED:"), text(p)
    assert r.cmd("status").returncode == DAMAGED


def test_a_done_with_no_intent_is_damaged(tmp_path):
    r = R(tmp_path)
    r.write(0)
    assert r.move("t1").returncode == OK
    rewrite_record(r.run_dir, lambda o: o["event"] == "intent")
    assert r.cmd("verify").returncode == DAMAGED


def test_complete_without_a_pass_of_the_last_step_is_damaged(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    r.write(2)
    assert r.adv().returncode == OK
    rewrite_record(r.run_dir, lambda o: o["event"] == "pass" and o["stage"] == "finish")
    p = r.cmd("verify")
    assert p.returncode == DAMAGED, text(p)


def test_an_untouched_walk_with_back_and_resume_still_verifies(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    assert r.person("b1", "back").returncode == OK and r.bk("b1").returncode == OK
    r.answer()
    assert r.cmd("resume", "--choice", "continue").returncode == OK
    r.answer()
    assert r.cmd("snooze", "--choice", "leave-it").returncode == OK
    p = r.cmd("verify")
    assert p.returncode in (OK, CHECKFAIL), text(p)          # person lines may be unlogged; never DAMAGED
    assert p.returncode != DAMAGED


def test_a_marker_that_is_valid_json_but_not_an_object_is_damaged_not_a_traceback(tmp_path):
    r = R(tmp_path)
    for bad in ("[]", '"x"', "7", "null"):
        open(os.path.join(r.wd, ".stage-runner.json"), "w", encoding="utf-8").write(bad)
        for args in (["status"], ["advance"], ["verify"]):
            p = r.cmd(*args)
            assert p.returncode == DAMAGED, (bad, args, text(p))
            assert "Traceback" not in text(p), (bad, args, text(p))


def test_a_bad_marker_can_still_be_abandoned(tmp_path):
    r = R(tmp_path)
    open(os.path.join(r.wd, ".stage-runner.json"), "w", encoding="utf-8").write("[]")
    r.answer()
    p = r.cmd("abandon", "--choice", "start-over")
    assert p.returncode == OK, text(p)
    assert not os.path.exists(os.path.join(r.wd, ".stage-runner.json"))
    r.start()
    assert r.step()["index"] == 1


# ---------------------------------------------------------------- inputs
def test_zero_byte_or_whitespace_input_counts_as_missing(tmp_path):
    for body in ("", "   \n\t \n"):
        sub = tmp_path / ("c%d" % len(body))
        sub.mkdir()
        r = R(sub, extra_inputs=["out/notes.txt"])
        r.write(0)
        open(os.path.join(r.run_dir, "out", "notes.txt"), "w", encoding="utf-8").write(body)
        p = r.move("t1")
        assert "MISSING" in p.stdout and "tell the person" in p.stdout, (repr(body), text(p))
        # a real input is not missing
    sub = tmp_path / "real"
    sub.mkdir()
    r = R(sub, extra_inputs=["out/notes.txt"])
    r.write(0)
    open(os.path.join(r.run_dir, "out", "notes.txt"), "w", encoding="utf-8").write("real notes\n")
    p = r.move("t1")
    assert "MISSING" not in p.stdout, text(p)


# ---------------------------------------------------------------- ensure_commands
def test_ensure_commands_writes_the_new_body(tmp_path):
    r = R(tmp_path)
    for name in ("next", "back"):
        body = open(os.path.join(r.wd, ".claude", "commands", name + ".md"), encoding="utf-8").read()
        assert NEW_BODY in body, (name, body)
        assert "nothing new" not in body and "nothing changed" not in body


def test_ensure_commands_rewrites_the_old_text_and_leaves_custom_bodies_alone(tmp_path):
    td = str(tmp_path)
    card = card3(td)
    wd = os.path.join(td, "wd")
    cd = os.path.join(wd, ".claude", "commands")
    os.makedirs(cd)
    open(os.path.join(cd, "next.md"), "w", encoding="utf-8").write(OLD_NEXT)
    old_back = OLD_NEXT.replace("move to the next stage of the run", "go back and re-open the previous stage") \
                       .replace("say there is nothing new", "say nothing changed")
    open(os.path.join(cd, "back.md"), "w", encoding="utf-8").write("---\ndescription: mine\n---\nMy own body.\n")
    p = run(["start", "--card", card, "--workdir", wd])
    assert p.returncode == OK, text(p)
    assert NEW_BODY in open(os.path.join(cd, "next.md"), encoding="utf-8").read()
    assert open(os.path.join(cd, "back.md"), encoding="utf-8").read() == \
        "---\ndescription: mine\n---\nMy own body.\n"
    # and the old BACK text is rewritten too
    td2 = str(tmp_path / "two")
    os.makedirs(td2)
    card2 = card3(td2)
    wd2 = os.path.join(td2, "wd")
    cd2 = os.path.join(wd2, ".claude", "commands")
    os.makedirs(cd2)
    open(os.path.join(cd2, "back.md"), "w", encoding="utf-8").write(old_back)
    assert run(["start", "--card", card2, "--workdir", wd2]).returncode == OK
    assert NEW_BODY in open(os.path.join(cd2, "back.md"), encoding="utf-8").read()


# ---------------------------------------------------------------- mover.log / verify
def test_verify_reports_a_person_line_the_mover_did_not_log(tmp_path):
    r = R(tmp_path)
    assert r.person("ghost-turn", "next").returncode == OK
    p = r.cmd("verify")
    assert p.returncode != OK and "person line not written by the mover" in text(p), text(p)
    assert "ghost-turn" in text(p)


def test_verify_passes_with_a_matching_mover_log(tmp_path):
    r = R(tmp_path)
    r.write(0)
    assert r.move("t1").returncode == OK
    open(os.path.join(r.run_dir, "mover.log"), "w", encoding="utf-8").write("t1\n")
    p = r.cmd("verify")
    assert p.returncode == OK and p.stdout.startswith("OK "), text(p)


def test_verify_names_only_the_turns_missing_from_the_mover_log(tmp_path):
    r = R(tmp_path)
    assert r.person("logged", "next").returncode == OK
    assert r.person("forged", "back").returncode == OK
    open(os.path.join(r.run_dir, "mover.log"), "w", encoding="utf-8").write("logged\n")
    p = r.cmd("verify")
    assert p.returncode != OK and "forged" in text(p) and "logged" not in text(p).replace("not written", "")


def test_the_runner_never_writes_the_mover_log(tmp_path):
    r = R(tmp_path)
    r.write(0)
    assert r.move("t1").returncode == OK
    assert not os.path.exists(os.path.join(r.run_dir, "mover.log"))


# ======================================================================================
# Phase 4c fix pass (fix list + attacker round, 2026-11-23): every kept fix planted
# failing-first. Run: python3 -m pytest system/parts/tests/test_stage_runner.py -q
# ======================================================================================
PARTS = os.path.abspath(os.path.join(HERE, ".."))


def _forge(run_dir, events):
    """Append hand-built events through stage_runner's own writer, exactly as a forger
    with python -c would (the no-tracks attack from the attacker round)."""
    calls = "; ".join(
        "s.append(%r, %r, %r, %r)" % (run_dir, e, st, d) for e, st, d in events)
    prog = ("import sys; sys.path.insert(0, %r); import stage_runner as s; %s"
            % (PARTS, calls))
    p = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr


def test_empty_record_is_damaged(tmp_path):
    """Fix 4: a record that is empty (or whose first line is not start) is DAMAGED, not a
    TypeError traceback or a clean OK."""
    r = R(tmp_path)
    open(os.path.join(r.run_dir, "record.jsonl"), "w", encoding="utf-8").close()
    p = r.cmd("verify")
    assert p.returncode == DAMAGED and "Traceback" not in text(p), text(p)


def test_first_line_not_start_is_damaged(tmp_path):
    r = R(tmp_path)
    _forge(r.run_dir, [("person", None, {"turn": "z", "cmd": "next"})])
    rewrite_record(r.run_dir, lambda o: o["event"] == "start")
    p = r.cmd("verify")
    assert p.returncode == DAMAGED and "start" in text(p), text(p)


def test_unknown_open_step_is_damaged_not_a_traceback(tmp_path):
    """Fix 5: a record whose open step is not in the card reads DAMAGED (stage_index -1),
    on advance, back, resume and status -- never an IndexError."""
    r = R(tmp_path)
    r.write(0)
    assert r.move("t1").returncode == OK          # gather -> shape (talk, needs the person)
    _forge(r.run_dir, [
        ("person", None, {"turn": "f1", "cmd": "next"}),
        ("pass", "shape", {"via": "forged", "turn": "f1"}),
        ("handover", "shape", {"via": "forged", "result": "pass", "turn": "f1"}),
        ("intent", "shape", {"to": "ghost", "code_hash": "0" * 16, "via": "forged"}),
        ("done", "ghost", {"to": "ghost", "code_hash": "0" * 16}),
    ])
    for args in (["advance"], ["back", "--turn", "x"], ["status"], ["check"],
                 ["resume", "--choice", "continue"]):
        p = r.cmd(*args)
        assert p.returncode == DAMAGED and "Traceback" not in text(p), (args, text(p))


def test_advance_on_a_complete_run_writes_nothing(tmp_path):
    """Fix 7: advance past the end is a NOTHING that appends no handover noop."""
    r = R(tmp_path)
    r.to_step(2)
    r.write(2)
    assert r.adv().returncode == OK
    n = len(r.lines())
    assert r.adv().returncode == NOTHING, text(r.adv)
    assert len(r.lines()) == n


def test_relative_run_dir_in_marker_resolves_against_the_marker_folder(tmp_path):
    """Fix 8: the marker may name the run folder relatively; it resolves against the
    marker's folder (matching the mover), from any process cwd."""
    r = R(tmp_path)
    r.to_step(1)
    json.dump({"run_dir": "runs/%s" % r.rid, "run_id": r.rid},
              open(os.path.join(r.wd, ".stage-runner.json"), "w", encoding="utf-8"))
    p = subprocess.run([sys.executable, os.path.abspath(RUNNER), "status", "--json",
                        "--workdir", r.wd], capture_output=True, text=True, cwd="/")
    assert p.returncode == OK, p.stdout + p.stderr
    assert json.loads(p.stdout)["index"] == 2


def test_abandon_on_a_complete_run_uses_the_done_tag(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    r.write(2)
    assert r.adv().returncode == OK
    r.answer()
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json.done-" + r.rid))
    assert not os.path.exists(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid))


def test_marker_pointing_outside_its_folder_is_refused_by_every_command(tmp_path):
    """A4: the folder check lives in find_run, so the runner, the reader and the mover all
    refuse a marker whose run folder sits outside the marker's folder."""
    r = R(tmp_path)
    outside = os.path.join(r.td, "outside")
    shutil.rmtree(outside, ignore_errors=True)
    os.makedirs(outside)
    json.dump({"run_dir": outside, "run_id": r.rid},
              open(os.path.join(r.wd, ".stage-runner.json"), "w", encoding="utf-8"))
    for args in (["status"], ["check"], ["advance"], ["verify"], ["recover"],
                 ["resume", "--choice", "continue"]):
        p = r.cmd(*args)
        assert p.returncode == DAMAGED and "outside" in text(p), (args, text(p))
        assert "Traceback" not in text(p)


def test_a_talk_pass_without_a_person_turn_is_damaged(tmp_path):
    """A1 (no tracks): the python -c append forgery -- a pass/handover/intent/done on a
    talk step with no person turn -- must read DAMAGED, not verify OK."""
    r = R(tmp_path)
    r.write(0)
    _forge(r.run_dir, [
        ("pass", "gather", {"via": "forged"}),
        ("handover", "gather", {"via": "forged", "result": "pass"}),
        ("intent", "gather", {"to": "shape", "code_hash": "0" * 16, "via": "forged"}),
        ("done", "shape", {"to": "shape", "code_hash": "0" * 16}),
    ])
    p = r.cmd("verify")
    assert p.returncode == DAMAGED and "person turn" in text(p), text(p)
    assert r.cmd("status").returncode == DAMAGED


def test_a_back_without_a_person_turn_is_damaged(tmp_path):
    r = R(tmp_path)
    r.to_step(1)
    _forge(r.run_dir, [("back", "shape", {"via": "forged", "to": "gather"})])
    p = r.cmd("verify")
    assert p.returncode == DAMAGED and "person turn" in text(p), text(p)


def test_the_mover_shaped_still_verifies(tmp_path):
    """Control: a talk pass carrying the mover's person turn still verifies OK."""
    r = R(tmp_path)
    r.write(0)
    assert r.move("t1").returncode == OK
    open(os.path.join(r.run_dir, "mover.log"), "w", encoding="utf-8").write("t1\n")
    p = r.cmd("verify")
    assert p.returncode == OK, text(p)


def test_resume_snooze_abandon_record_the_newest_person_prompt(tmp_path):
    """A3: resume/abandon/snooze record the newest person.log line (id + time)."""
    r = R(tmp_path)
    open(os.path.join(r.run_dir, "person.log"), "w", encoding="utf-8").write("p1\t% d\n" % time.time())
    for args, event, want in ((["resume", "--choice", "continue"], "reissue", "p1"),
                              (["snooze", "--choice", "leave-it"], "snoozed", "p2")):
        if want == "p2": # one person prompt serves exactly ONE menu command
            open(os.path.join(r.run_dir, "person.log"), "a", encoding="utf-8").write(
                "p2\t%d\n" % time.time())
        assert r.cmd(*args).returncode == OK, text(r.cmd(*args))
        last = r.lines()[-1]
        assert last["event"] == event, last
        assert last["data"]["person"]["id"] == want, last
    r2 = R(tmp_path / "ab")
    open(os.path.join(r2.run_dir, "person.log"), "w", encoding="utf-8").write("p1\t%d\n" % time.time())
    r2.write(0)
    assert r2.move("t2").returncode == OK
    open(os.path.join(r2.run_dir, "person.log"), "a", encoding="utf-8").write("t2\t%d\n" % time.time())
    assert r2.cmd("abandon", "--choice", "start-over").returncode == OK
    last = r2.lines()[-1]
    assert last["event"] == "abandoned" and last["data"]["person"]["id"] == "t2", last


def test_verify_flags_a_reissue_whose_person_prompt_is_not_logged(tmp_path):
    """A3 verify: a reissue with no person prompt recorded (or one not in person.log) is
    reported, exit 3 -- tamper evidence. (The gate itself refuses a live resume without a
    logged prompt, so a no-prompt reissue can only be forged.)"""
    r = R(tmp_path)
    _forge(r.run_dir, [("reissue", None, {"code_hash": "0" * 16, "choice": "continue"})])
    v = r.cmd("verify")
    assert v.returncode == CHECKFAIL and "person prompt" in text(v), text(v)


def test_verify_flags_a_reissue_older_than_the_last_reissue(tmp_path):
    r = R(tmp_path)
    t0 = time.time() - 100
    open(os.path.join(r.run_dir, "person.log"), "w", encoding="utf-8").write(
        "p2\t%d\n" % t0) # the OLD prompt first in the log
    open(os.path.join(r.run_dir, "person.log"), "a", encoding="utf-8").write(
        "p1\t%.3f\n" % time.time()) # a FRESH one after it: resume may use p1
    assert r.cmd("resume", "--choice", "continue").returncode == OK # uses the fresh p1
    _forge(r.run_dir, [("reissue", None, {"code_hash": "0" * 16, "choice": "continue",
                                          "person": {"id": "p2", "t": t0}})])
    v = r.cmd("verify")
    assert v.returncode == CHECKFAIL and "older" in text(v), text(v)


def test_verify_passes_when_the_person_prompt_is_logged_and_fresh(tmp_path):
    r = R(tmp_path)
    open(os.path.join(r.run_dir, "person.log"), "w", encoding="utf-8").write("p1\t%d\n" % time.time())
    r.answer()
    assert r.cmd("resume", "--choice", "continue").returncode == OK
    open(os.path.join(r.run_dir, "person.log"), "a", encoding="utf-8").write("p2\t%d\n" % time.time())
    r.answer()
    assert r.cmd("resume", "--choice", "continue").returncode == OK
    v = r.cmd("verify")
    assert v.returncode == OK, text(v)


def test_an_abandoned_run_refuses_advance_back_and_person_turn(tmp_path):
    """A5: renaming the .abandoned- marker back must not revive a run."""
    r = R(tmp_path)
    r.to_step(1)
    r.write(0)
    r.answer()
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    shutil.copy(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid),
                os.path.join(r.wd, ".stage-runner.json"))
    assert r.person("t1", "next").returncode == NOTHING, text(r.person("t1", "next"))
    assert r.adv("t1").returncode == NOTHING, text(r.adv("t1"))
    assert r.bk("t1").returncode == NOTHING
    assert r.step()["index"] == 2                     # nothing moved


def test_verify_flags_a_record_line_after_abandoned(tmp_path):
    r = R(tmp_path)
    r.answer()
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    shutil.copy(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid),
                os.path.join(r.wd, ".stage-runner.json"))
    _forge(r.run_dir, [("snoozed", None, {"choice": "leave-it"})])
    v = r.cmd("verify")
    assert v.returncode == DAMAGED and "abandoned" in text(v), text(v)


def test_verify_reports_a_changed_card(tmp_path):
    """Fix 3: verify checks card_sha like get_ctx -- a card edited mid-run is DAMAGED."""
    r = R(tmp_path)
    c = json.load(open(r.card, encoding="utf-8"))
    c["stages"][0]["checks"]["min_words"] = 1
    json.dump(c, open(r.card, "w", encoding="utf-8"))
    v = r.cmd("verify")
    assert v.returncode == DAMAGED and "card" in text(v), text(v)


# ---------------------------------------------------------------- the legacy script checks
def test_legacy_script_checks_still_pass():
    del _results[:]
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())


# ======================================================================================
# Run-pickup phase 4d: OPTIONAL steps (the owner's yes, 2026-11-23). A talk step marked
# "optional": true may be skipped BY THE PERSON: on a person{cmd:next} turn whose checks
# fail (or whose output is missing), advance records a pass {"skipped": "by the person",
# "turn": <turn>} and hands over as normal. No person turn: refused exactly as today --
# the AI can never skip. A non-optional step is unchanged. Tests first, each failing first.
# ======================================================================================

def make_optional(card_path, i=0):
    """Mark stage i of an existing card optional=True (rewrites the card file)."""
    c = json.load(open(card_path, encoding="utf-8"))
    c["stages"][i]["optional"] = True
    json.dump(c, open(card_path, "w", encoding="utf-8"))
    return card_path

def last_pass(r):
    return [l for l in r.lines() if l["event"] == "pass"][-1]

def test_optional_talk_step_skipped_by_the_person(tmp_path):
    """(a) optional + person /next + no output -> skipped pass, moves one step."""
    r = R(tmp_path, start=False)
    make_optional(r.card)
    r.start()
    p = r.move("a1")
    assert p.returncode == OK, text(p)
    lp = last_pass(r)
    assert lp["stage"] == "gather" and lp["data"].get("skipped") == "by the person"
    assert lp["data"].get("turn") == "a1"
    assert r.step()["index"] == 2

def test_optional_step_without_a_person_turn_is_refused(tmp_path):
    """(b) optional + NO person turn -> refused (exit 3), nothing written."""
    r = R(tmp_path, start=False)
    make_optional(r.card)
    r.start()
    p = r.adv()
    assert p.returncode == CHECKFAIL and "no person turn" in text(p).lower(), text(p)
    assert "pass" not in r.events() and r.step()["index"] == 1

def test_non_optional_step_still_refused_with_no_output(tmp_path):
    """(c) non-optional + person /next + no output -> refused as today (exit 3)."""
    r = R(tmp_path)
    p = r.move("a1")
    assert p.returncode == CHECKFAIL, text(p)
    assert "pass" not in r.events() and r.step()["index"] == 1

def test_optional_step_that_passes_is_a_normal_pass(tmp_path):
    """(d) optional step whose output passes its checks -> normal pass, no 'skipped'."""
    r = R(tmp_path, start=False)
    make_optional(r.card)
    r.start()
    r.write(0)
    p = r.move("a1")
    assert p.returncode == OK, text(p)
    lp = last_pass(r)
    assert "skipped" not in lp["data"]

def test_verify_ok_on_a_run_with_a_skipped_pass(tmp_path):
    """(e) verify OK on a run whose first step was skipped by the person. The skip hands
    over as normal, so the next step pauses on its missing input (by design); the person
    fills it, and the AI runs resume --choice continue to reissue the step's code word."""
    r = R(tmp_path, start=False)
    make_optional(r.card)
    r.start()
    assert r.move("a1").returncode == OK
    assert last_pass(r)["data"].get("skipped") == "by the person"
    r.write(0)  # the person fills the skipped step's output: the input pause lifts
    # the mover logs the person prompt (person.log) that authorised the resume
    open(os.path.join(r.run_dir, "person.log"), "a", encoding="utf-8").write(
        "p9\t%.3f\n" % time.time())
    r.answer()
    q = r.cmd("resume", "--choice", "continue")
    assert q.returncode == OK, text(q)
    r.code = re.search(r"(RUN-[0-9A-Z]{6})", q.stdout).group(1)
    r.write(1)
    assert r.move("a2").returncode == OK
    r.write(2)
    assert r.move("a3").returncode == OK
    open(os.path.join(r.run_dir, "mover.log"), "a", encoding="utf-8").write(
        "".join(t + "\n" for t in ("a1", "a2", "a3")))
    v = r.cmd("verify")
    assert v.returncode == OK and v.stdout.startswith("OK "), text(v)

def test_card_rejects_a_non_boolean_optional(tmp_path):
    """Card validation accepts the boolean only: optional: 'yes' -> refused at start (exit 2)."""
    r = R(tmp_path, start=False)
    c = json.load(open(r.card, encoding="utf-8"))
    c["stages"][0]["optional"] = "yes"
    json.dump(c, open(r.card, "w", encoding="utf-8"))
    p = run(["start", "--card", r.card, "--workdir", r.wd])
    assert p.returncode == USAGE, text(p)
    assert "optional" in text(p), text(p)
    assert not os.path.exists(os.path.join(r.wd, ".stage-runner.json"))

# ======================================================================================
# Phase 4e fix pass (brief 2026-11-23). Each fix planted failing-first.
# ======================================================================================

def _answer(r, pid=None):
    """The person answers (the mover logs the prompt id to person.log); -> the pid."""
    return r.answer(pid)

def test_menu_command_without_a_person_prompt_is_refused(tmp_path):
    """4e A1: resume/snooze/abandon with NO person prompt logged is refused, exit 3
    'ask the person first', nothing written."""
    r = R(tmp_path)
    r.to_step(1)
    n = len(r.lines())
    p = r.cmd("resume", "--choice", "continue")
    assert p.returncode == CHECKFAIL and "ask the person first" in text(p), text(p)
    assert len(r.lines()) == n
    p = r.cmd("snooze", "--choice", "leave-it")
    assert p.returncode == CHECKFAIL and "ask the person first" in text(p), text(p)
    assert len(r.lines()) == n

def test_menu_command_with_a_stale_person_prompt_is_refused(tmp_path):
    """4e A1: the recorded person prompt must be NEWER than the record's last line."""
    r = R(tmp_path)
    r.to_step(1)
    open(os.path.join(r.run_dir, "person.log"), "w", encoding="utf-8").write(
        "p0\t%d\n" % (time.time() - 500))
    n = len(r.lines())
    p = r.cmd("resume", "--choice", "continue")
    assert p.returncode == CHECKFAIL and "older" in text(p), text(p)
    assert len(r.lines()) == n

def test_a_person_prompt_serves_only_one_menu_command(tmp_path):
    """4e A1: each person prompt id may be used by exactly ONE menu command."""
    r = R(tmp_path)
    r.answer("p1")
    assert r.cmd("resume", "--choice", "continue").returncode == OK
    n = len(r.lines())
    p = r.cmd("snooze", "--choice", "leave-it")
    assert p.returncode == CHECKFAIL and "ask the person first" in text(p), text(p)
    assert len(r.lines()) == n

def test_verify_flags_a_reused_menu_prompt(tmp_path):
    """4e A1 verify: a menu line whose person prompt id another menu line already used is
    reported, exit 3."""
    r = R(tmp_path)
    open(os.path.join(r.run_dir, "person.log"), "w", encoding="utf-8").write(
        "p1\t%.3f\n" % time.time())
    assert r.cmd("resume", "--choice", "continue").returncode == OK
    _forge(r.run_dir, [("snoozed", None,
        {"choice": "leave-it", "person": {"id": "p1", "t": time.time()}})])
    v = r.cmd("verify")
    assert v.returncode == CHECKFAIL and "already used" in text(v), text(v)

def test_verify_flags_a_stale_menu_prompt(tmp_path):
    """4e A1 verify: a menu line whose person prompt is older than the record's line
    before it is reported, exit 3."""
    r = R(tmp_path)
    t0 = time.time() - 100
    open(os.path.join(r.run_dir, "person.log"), "w", encoding="utf-8").write(
        "p2\t%d\n" % t0) # the OLD prompt first in the log
    open(os.path.join(r.run_dir, "person.log"), "a", encoding="utf-8").write(
        "p1\t%.3f\n" % time.time()) # a FRESH one after it: resume may use p1
    assert r.cmd("resume", "--choice", "continue").returncode == OK
    _forge(r.run_dir, [("reissue", None,
        {"code_hash": "0" * 16, "choice": "continue", "person": {"id": "p2", "t": t0}})])
    v = r.cmd("verify")
    assert v.returncode == CHECKFAIL and "older" in text(v), text(v)

def test_verify_run_reads_a_set_aside_run(tmp_path):
    """4e A1: `verify --run <run folder>` reads an abandoned (set-aside) run directly."""
    r = R(tmp_path)
    r.to_step(1)
    r.answer()
    open(os.path.join(r.run_dir, "mover.log"), "w", encoding="utf-8").write("w0\n")
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    p = run(["verify", "--run", r.run_dir])
    assert p.returncode == OK and p.stdout.startswith("OK "), text(p)

def test_abandon_in_a_copied_folder_never_touches_the_original_record(tmp_path):
    """4e A2: a copied folder whose marker still points at the ORIGINAL run folder:
    abandon in the copy renames the copy's marker only; the original record is unchanged."""
    r = R(tmp_path)
    r.to_step(1)
    r.answer()
    before = open(os.path.join(r.run_dir, "record.jsonl"), encoding="utf-8").read()
    copy = os.path.join(r.td, "copy")
    shutil.copytree(r.wd, copy) # its marker still names r.run_dir, outside the copy
    p = run(["abandon", "--choice", "start-over", "--workdir", copy])
    assert p.returncode == OK, text(p)
    assert open(os.path.join(r.run_dir, "record.jsonl"), encoding="utf-8").read() == before
    assert not os.path.exists(os.path.join(copy, ".stage-runner.json"))
    assert os.path.isfile(os.path.join(copy, ".stage-runner.json.abandoned-" + r.rid))

def test_optional_skip_handover_names_the_skip(tmp_path):
    """4e A3: a skipped optional step's handover says 'was SKIPPED by your /next (not
    finished: <codes>)', and status --json lists it under 'skipped'."""
    r = R(tmp_path, start=False)
    make_optional(r.card)
    r.start()
    p = r.move("a1")
    assert p.returncode == OK, text(p)
    assert "SKIPPED by your /next" in p.stdout, text(p)
    assert "not finished:" in p.stdout, text(p)
    j = r.step()
    assert j["skipped"] == ["gather"], j

def test_status_json_skipped_is_empty_without_a_skip(tmp_path):
    r = R(tmp_path)
    assert r.step()["skipped"] == []

def test_card_rejects_an_alone_optional_step(tmp_path):
    """4e A3: a card that marks an ALONE step optional is refused at start (exit 2)."""
    r = R(tmp_path, start=False)
    c = json.load(open(r.card, encoding="utf-8"))
    c["stages"][2]["optional"] = True
    json.dump(c, open(r.card, "w", encoding="utf-8"))
    p = run(["start", "--card", r.card, "--workdir", r.wd])
    assert p.returncode == USAGE and "optional" in text(p), text(p)
    assert not os.path.exists(os.path.join(r.wd, ".stage-runner.json"))

def test_global_workdir_before_the_subcommand_is_honoured(tmp_path):
    """4e A4: `stage_runner.py --workdir W status` from another folder sees W's run."""
    r = R(tmp_path)
    r.to_step(1)
    p = subprocess.run([sys.executable, os.path.abspath(RUNNER), "--workdir", r.wd,
                        "status", "--json"], capture_output=True, text=True, cwd="/")
    assert p.returncode == OK, p.stdout + p.stderr
    assert json.loads(p.stdout)["index"] == 2

def test_ensure_commands_marks_the_commands_not_model_invocable(tmp_path):
    """4e fix 7: /next and /back carry disable-model-invocation: true; a file still in the
    previous (no-flag) body is rewritten the same way the old-body rewrite works; a custom
    body is left alone."""
    td = str(tmp_path)
    card = card3(td)
    wd = os.path.join(td, "wd")
    cd = os.path.join(wd, ".claude", "commands")
    os.makedirs(cd)
    prev = "---\ndescription: move to the next stage of the run\n---\n" + NEW_BODY + "\n"
    open(os.path.join(cd, "next.md"), "w", encoding="utf-8").write(prev)
    open(os.path.join(cd, "back.md"), "w", encoding="utf-8").write(
        "---\ndescription: mine\n---\nMy own body.\n")
    assert run(["start", "--card", card, "--workdir", wd]).returncode == OK
    nxt = open(os.path.join(cd, "next.md"), encoding="utf-8").read()
    assert "disable-model-invocation: true" in nxt, nxt
    assert NEW_BODY in nxt, nxt
    assert open(os.path.join(cd, "back.md"), encoding="utf-8").read() == \
        "---\ndescription: mine\n---\nMy own body.\n"

def test_start_sets_a_revived_abandoned_run_aside(tmp_path):
    """4e fix 8: a run abandoned and revived (its .abandoned- marker copied back) is set
    aside by start like a finished run -- today start refuses and the folder stays stuck."""
    r = R(tmp_path)
    r.to_step(1)
    r.answer()
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    shutil.copy(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid),
                os.path.join(r.wd, ".stage-runner.json"))
    n_before = len(glob.glob(os.path.join(r.wd, ".stage-runner.json.abandoned-*")))
    r.start()
    assert r.step()["index"] == 1 and r.step()["complete"] is False # a NEW run began
    n_after = len(glob.glob(os.path.join(r.wd, ".stage-runner.json.abandoned-*")))
    assert n_after == n_before + 1, (n_before, n_after) # the revived run was set aside


# ======================================================================================
# ITEM 2 (2026-11-27): a card changed mid-run is its own state (exit 8, CARD UPDATED), and the person's yes
# (`refresh --choice continue`) pins the new card and carries on at the SAME step. The check that was missed last time:
# a live run survives a card change.
# ======================================================================================
def _edit_card(r, **kw):
    c = json.load(open(r.card, encoding="utf-8"))
    c["stages"][1]["checks"]["min_words"] = kw.get("min_words", 4)
    json.dump(c, open(r.card, "w", encoding="utf-8"))


def _mover_log(r, *turns):
    open(os.path.join(r.run_dir, "mover.log"), "w", encoding="utf-8").write("".join(t + "\n" for t in turns))


def test_live_run_survives_a_card_change_and_continues_at_the_same_step(tmp_path):
    r = R(tmp_path)
    r.write(0)
    assert r.move("t1").returncode == OK
    _mover_log(r, "t1")
    before = open(os.path.join(r.run_dir, "record.jsonl"), encoding="utf-8").read()
    assert r.step()["index"] == 2
    _edit_card(r)
    p = r.cmd("status")
    assert p.returncode == CARDCHANGED and "CARD UPDATED" in text(p) and "step 2" in text(p), text(p)
    assert r.cmd("advance").returncode == CARDCHANGED          # still refuses: nothing moves on a changed card
    r.answer("yes1")
    p = r.cmd("refresh", "--choice", "continue")
    assert p.returncode == OK and "carrying on with the new version at step shape (2 of 3)" in text(p), text(p)
    r.code = re.search(r"(RUN-[0-9A-Z]{6})", p.stdout).group(1)
    after = open(os.path.join(r.run_dir, "record.jsonl"), encoding="utf-8").read()
    assert after.startswith(before)                            # every earlier line is exactly as it was
    new = r.lines()[len(before.splitlines()):]
    assert [l["event"] for l in new] == ["refresh"] and new[0]["stage"] == "shape", new
    assert new[0]["data"]["person"]["id"] == "yes1"
    st = r.step()
    assert st["index"] == 2 and not st["complete"], st          # same step, no restart
    assert r.cmd("verify").returncode == OK, text(r.cmd("verify"))   # verify passes across the refresh
    r.write(1)
    assert r.move("t2").returncode == OK                       # and the run goes on from there
    _mover_log(r, "t1", "t2")
    assert r.step()["index"] == 3
    assert r.cmd("verify").returncode == OK


def test_a_changed_card_without_a_refresh_line_fails_verify(tmp_path):
    r = R(tmp_path)
    _edit_card(r)
    v = r.cmd("verify")
    assert v.returncode == DAMAGED and "card changed mid-run" in text(v), text(v)


def test_a_forged_card_sha_in_the_record_fails_verify(tmp_path):
    r = R(tmp_path)
    _edit_card(r)
    rec = os.path.join(r.run_dir, "record.jsonl")
    ls = open(rec, encoding="utf-8").read().splitlines()
    first = json.loads(ls[0])
    sys.path.insert(0, os.path.dirname(RUNNER))
    import stage_runner as sr
    first["data"]["card_sha"] = sr.card_sha(r.card, sr.load_card(r.card))   # pretend the run started on the new card
    open(rec, "w", encoding="utf-8").write(json.dumps(first, sort_keys=True) + "\n")
    assert r.cmd("verify").returncode == DAMAGED               # the chain no longer matches


def test_a_hand_made_refresh_line_that_does_not_follow_the_card_fails(tmp_path):
    r = R(tmp_path)
    sys.path.insert(0, os.path.dirname(RUNNER))
    import stage_runner as sr
    ls = r.lines()
    o = {"seq": len(ls), "t": time.time(), "prev": ls[-1]["hash"], "event": "refresh", "run": ls[0]["run"], "stage": "gather",
         "data": {"prev_card_sha": "f" * 64, "card_sha": "e" * 64, "card": r.card, "code_hash": "x"}}
    o["hash"] = sr._hash(o["prev"], o)
    open(os.path.join(r.run_dir, "record.jsonl"), "a", encoding="utf-8").write(json.dumps(o, sort_keys=True) + "\n")
    assert r.cmd("verify").returncode == DAMAGED
    assert r.cmd("status").returncode == DAMAGED


def test_refresh_refuses_when_the_open_step_is_gone(tmp_path):
    r = R(tmp_path)
    r.write(0)
    assert r.move("t1").returncode == OK
    c = json.load(open(r.card, encoding="utf-8"))
    del c["stages"][1]                                         # the open step "shape" is removed
    json.dump(c, open(r.card, "w", encoding="utf-8"))
    r.answer("yes1")
    n = len(r.lines())
    p = r.cmd("refresh", "--choice", "continue")
    assert p.returncode == CHECKFAIL and "shape" in text(p) and "no longer in the updated card" in text(p), text(p)
    assert len(r.lines()) == n                                 # nothing written


def test_refresh_needs_a_person_prompt_a_changed_card_and_the_menu_word(tmp_path):
    r = R(tmp_path)
    assert r.cmd("refresh", "--choice", "continue").returncode == NOTHING     # unchanged card: nothing to do
    _edit_card(r)
    p = r.cmd("refresh", "--choice", "continue")
    assert p.returncode == CHECKFAIL and "no person prompt" in text(p), text(p)
    assert r.cmd("status").returncode == CARDCHANGED                        # the question is shown
    r.answer("yes1")
    assert r.cmd("refresh", "--choice", "start-over").returncode == USAGE
    assert r.cmd("refresh", "--choice", "continue").returncode == OK
    assert r.cmd("refresh", "--choice", "continue").returncode == NOTHING      # already refreshed


def test_the_model_cannot_ask_and_answer_in_the_same_turn(tmp_path):
    """The blocker: /next on a changed card is exit 8 and writes no record line, so that prompt is still 'unused'. An immediate
    refresh on it must be refused; only a separate, later person prompt (the yes) lets it through."""
    r = R(tmp_path)
    _edit_card(r)
    r.answer("p-next")                                          # the person typed /next; the mover logged the prompt
    assert r.cmd("advance").returncode == CARDCHANGED           # the question is shown on p-next; nothing written
    n = len(r.lines())
    p = r.cmd("refresh", "--choice", "continue")                # the model's immediate refresh, no new prompt
    assert p.returncode == CHECKFAIL and "separate, later prompt" in text(p), text(p)
    assert len(r.lines()) == n
    r.answer("p-yes")                                           # the person's own yes
    p = r.cmd("refresh", "--choice", "continue")
    assert p.returncode == OK, text(p)
    last = r.lines()[-1]
    assert last["event"] == "refresh" and last["data"]["seen_on"] == "p-next" and last["data"]["person"]["id"] == "p-yes", last
    assert not os.path.exists(os.path.join(r.run_dir, "card-updated-seen.json"))
    assert r.cmd("verify").returncode == OK, text(r.cmd("verify"))


def test_refresh_without_the_question_ever_shown_is_refused(tmp_path):
    r = R(tmp_path)
    _edit_card(r)
    r.answer("p1")
    p = r.cmd("refresh", "--choice", "continue")
    assert p.returncode == CHECKFAIL and "not been shown" in text(p), text(p)


def test_verify_flags_a_refresh_on_the_prompt_its_question_was_shown_on(tmp_path):
    r = R(tmp_path)
    sys.path.insert(0, os.path.dirname(RUNNER))
    import stage_runner as sr
    old_sha = sr.card_sha(r.card, sr.load_card(r.card))
    _edit_card(r)
    new_sha = sr.card_sha(r.card, sr.load_card(r.card))
    r.answer("p1")
    ls = r.lines()
    for seen_on in ("p1", None):                                # same prompt; and no seen_on at all
        data = {"prev_card_sha": old_sha, "card_sha": new_sha, "card": r.card, "code_hash": "x", "choice": "continue",
                "person": {"id": "p1", "t": time.time()}}
        if seen_on:
            data["seen_on"] = seen_on
        o = {"seq": len(ls), "t": time.time(), "prev": ls[-1]["hash"], "event": "refresh", "run": ls[0]["run"],
             "stage": "gather", "data": data}
        o["hash"] = sr._hash(o["prev"], o)
        rec = os.path.join(r.run_dir, "record.jsonl")
        keep = open(rec, encoding="utf-8").read()
        open(rec, "a", encoding="utf-8").write(json.dumps(o, sort_keys=True) + "\n")
        v = r.cmd("verify")
        assert v.returncode == CHECKFAIL and "update question" in text(v), (seen_on, text(v))
        open(rec, "w", encoding="utf-8").write(keep)
