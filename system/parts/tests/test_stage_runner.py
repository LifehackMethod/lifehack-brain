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
    p = r.cmd("resume", "--choice", "continue")
    assert p.returncode == DANGLING and "recover first" in text(p), text(p)
    assert "reissue" not in r.events()


def test_resume_on_a_finished_run_is_exit_4(tmp_path):
    r = R(tmp_path)
    r.to_step(2)
    r.write(2)
    assert r.adv().returncode == OK
    n = len(r.lines())
    assert r.cmd("resume", "--choice", "continue").returncode == NOTHING
    assert len(r.lines()) == n


def test_resume_on_an_abandoned_run_is_exit_4(tmp_path):
    r = R(tmp_path)
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    shutil.copy(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid),
                os.path.join(r.wd, ".stage-runner.json"))      # a stale marker pointing at it
    assert r.cmd("resume", "--choice", "continue").returncode == NOTHING


def test_resume_choice_is_validated(tmp_path):
    r = R(tmp_path)
    n = len(r.lines())
    for bad in ("go", "start-over", "leave-it", ""):
        p = r.cmd("resume", "--choice", bad)
        assert p.returncode == USAGE and "ask the person again" in text(p).lower(), (bad, text(p))
    assert r.cmd("resume").returncode == USAGE
    assert len(r.lines()) == n


def test_old_code_word_is_refused_after_resume_with_the_taken_over_message(tmp_path):
    r = R(tmp_path)
    old = r.code
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
    p = r.cmd("resume", "--choice", "continue")
    new = re.search(r"(RUN-[0-9A-Z]{6})", p.stdout).group(1)
    r.write(0, code=new)
    assert r.cmd("check").returncode == OK
    assert r.move("t1").returncode == OK


def test_resume_then_advance_with_failing_output_is_refused(tmp_path):
    r = R(tmp_path)
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
        p = r.cmd("abandon", "--choice", bad)
        assert p.returncode == USAGE and "ask the person again" in text(p).lower(), (bad, text(p))
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json"))
    assert "abandoned" not in r.events()


def test_abandon_works_on_a_damaged_record(tmp_path):
    r = R(tmp_path)
    damage_record(r.wd, r.rid)
    p = r.cmd("abandon", "--choice", "start-over")
    assert p.returncode == OK, text(p)
    assert not os.path.exists(os.path.join(r.wd, ".stage-runner.json"))
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid))


def test_abandon_works_on_an_unreadable_card(tmp_path):
    r = R(tmp_path)
    os.remove(r.card)
    p = r.cmd("abandon", "--choice", "start-over")
    assert p.returncode == OK, text(p)
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid))
    assert "abandoned" in r.events()                         # the record itself still verifies
    assert not {"pass", "done", "complete"} & set(r.events()[-1:])


def test_status_json_exposes_abandoned_and_snoozed(tmp_path):
    r = R(tmp_path)
    j = r.step()
    assert j["snoozed"] is False and j["abandoned"] is False
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    shutil.copy(os.path.join(r.wd, ".stage-runner.json.abandoned-" + r.rid),
                os.path.join(r.wd, ".stage-runner.json"))
    j = r.step()
    assert j["abandoned"] is True


# ---------------------------------------------------------------- snooze
def test_snooze_appends_snoozed_and_a_later_resume_lifts_it(tmp_path):
    r = R(tmp_path)
    p = r.cmd("snooze", "--choice", "leave-it")
    assert p.returncode == OK, text(p)
    assert r.lines()[-1]["event"] == "snoozed" and r.lines()[-1]["data"]["choice"] == "leave-it"
    assert r.step()["snoozed"] is True
    assert r.cmd("resume", "--choice", "continue").returncode == OK
    assert r.step()["snoozed"] is False


def test_a_later_person_line_also_lifts_the_snooze(tmp_path):
    r = R(tmp_path)
    assert r.cmd("snooze", "--choice", "leave-it").returncode == OK
    assert r.step()["snoozed"] is True
    assert r.person("t1", "next").returncode == OK
    assert r.step()["snoozed"] is False


def test_snooze_choice_is_validated(tmp_path):
    r = R(tmp_path)
    for bad in ("continue", "start-over", "later"):
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
    assert r.cmd("abandon", "--choice", "start-over").returncode == OK
    r.start()
    assert r.rid != old and r.step()["index"] == 1
    assert os.path.isfile(os.path.join(r.wd, ".stage-runner.json.abandoned-" + old))


# ---------------------------------------------------------------- card changed mid-run
def test_card_edited_mid_run_is_damaged(tmp_path):
    r = R(tmp_path)
    c = json.load(open(r.card, encoding="utf-8"))
    c["stages"][0]["checks"]["min_words"] = 1
    json.dump(c, open(r.card, "w", encoding="utf-8"))
    for args in (["status"], ["check"], ["advance"], ["resume", "--choice", "continue"]):
        p = r.cmd(*args)
        assert p.returncode == DAMAGED and "card changed mid-run" in text(p), (args, text(p))


def test_prompt_file_edited_mid_run_is_damaged(tmp_path):
    r = R(tmp_path)
    open(os.path.join(r.td, "prompts", "02-shape.md"), "a", encoding="utf-8").write("sneaky extra line\n")
    p = r.cmd("status")
    assert p.returncode == DAMAGED and "card changed mid-run" in text(p), text(p)


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
    assert r.cmd("resume", "--choice", "continue").returncode == OK
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


# ---------------------------------------------------------------- the legacy script checks
def test_legacy_script_checks_still_pass():
    del _results[:]
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
