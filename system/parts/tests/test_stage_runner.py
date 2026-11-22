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

OK, USAGE, CHECKFAIL, NOTHING, NORUN, DAMAGED = 0, 2, 3, 4, 5, 6

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
    p = run(["advance", "--workdir", wd])
    assert p.returncode == OK, p.stdout + p.stderr
    code2 = re.search(r"(RUN-[0-9A-Z]{6})", p.stdout).group(1)
    open(os.path.join(wd, "runs", rid, "out", "02-analyze.md"), "w", encoding="utf-8").write(
        "## Analyze\n\nThe analysis follows from the gathered frame, complete and checked.\n\n"
        "Code word: %s\n" % code2)
    p = run(["advance", "--workdir", wd])
    assert p.returncode == OK and "complete" in p.stdout.lower(), p.stdout + p.stderr
    return wd, rid


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
        for k in ("event", "stage", "run"):
            if obj.get(k):
                obj[k] = obj[k] + "x"
                break
        else:
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
        "gate": ('        problems = run_checks(card, stage, run_dir, st["code"])',
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
        p = run(["advance", "--workdir", fresh])
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
        bg = run(["advance", "--workdir", gcopy], runner=broken_variant(td, "gate"))
        report("(2) FAILING-FIRST: the broken runner ADVANCES past the unmet stage",
               bg.returncode == OK, "broken exit %d" % bg.returncode)
        rg = run(["advance", "--workdir", fresh])
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


if __name__ == "__main__":
    sys.exit(main())
