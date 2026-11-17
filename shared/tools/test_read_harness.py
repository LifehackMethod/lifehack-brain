#!/usr/bin/env python3
"""test_read_harness.py -- Run: python3 shared/tools/test_read_harness.py (stdlib only; temp folder fixtures;
a STUB model everywhere -- no test ever calls a real model). Prints one PASS/FAIL line per planted-failure
test (a) to (m); exits 0 only if all pass. ALLOW cases first."""
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import read_harness as rh  # noqa: E402

DOC1 = """Preamble text before the first heading.

## Alpha
The quarterly review checks spending against plan values and refuses guesses.

## Beta
This section covers houseplant watering schedules only.
"""

DOC2 = ("## Gamma\n" + "\n".join("filler line %d" % i for i in range(160))
        + "\n\n### Delta\nThe delta paragraph states the remote-wipe policy.\n")


def stub_for(mapping):
    """A stub call_model(prompt, model). mapping: list of (predicate(prompt), reply or ('FAIL', err))."""
    def call_model(prompt, model):
        for pred, out in mapping:
            if pred(prompt):
                if isinstance(out, tuple):
                    return None, out[1]
                return out, None
        return None, "stub has no answer for this prompt"
    return call_model


def honest_reply(body):
    """A contract-legal reply for a section: APPLIES quoting the sentence containing 'spending'
    when one is present, else DOES-NOT-APPLY."""
    m = re.search(r"[^.]*spending[^.]*\.", body, re.S)
    if m:
        return json.dumps({"verdict": "APPLIES", "quote": m.group(0).strip()})
    return json.dumps({"verdict": "DOES-NOT-APPLY", "quote": ""})


def honest_stub():
    def call_model(prompt, model):
        if "Produce findings" in prompt:  # final read
            return "NO-FINDINGS", None
        body = prompt.split("SECTION:\n", 1)[1]
        return honest_reply(body), None
    return call_model


def make_env():
    d = tempfile.mkdtemp(prefix="rh_test_")
    p1 = os.path.join(d, "doc1.md"); open(p1, "w", encoding="utf-8").write(DOC1)
    p2 = os.path.join(d, "doc2.md"); open(p2, "w", encoding="utf-8").write(DOC2)
    q = os.path.join(d, "q.txt"); open(q, "w", encoding="utf-8").write("What does this say about spending?\n")
    return d, [p1, p2], q


def run_main(args):
    old = sys.stdout
    try:
        import io
        sys.stdout = io.StringIO()
        code = rh.main(args)
        out = sys.stdout.getvalue()
    finally:
        sys.stdout = old
    return code, out


def results_rows(out_dir):
    with open(os.path.join(out_dir, "results.tsv"), encoding="utf-8") as fh:
        lines = fh.read().rstrip("\n").split("\n")
    assert lines[0] == rh.RESULTS_HEADER, "bad header: %r" % lines[0]
    return [dict(zip(rh.RESULTS_HEADER.split("\t"), l.split("\t"))) for l in lines[1:]]


RESULTS = []

def check(letter, name, fn):
    try:
        fn()
        print("PASS (%s) %s" % (letter, name))
        RESULTS.append(True)
    except AssertionError as e:
        print("FAIL (%s) %s: %s" % (letter, name, e))
        RESULTS.append(False)
    except Exception as e:
        print("FAIL (%s) %s: %s: %s" % (letter, name, e.__class__.__name__, e))
        RESULTS.append(False)


# (a) a made-up quote is refused
def test_a():
    d, docs, q = make_env()
    out = os.path.join(d, "out")
    replies = 0
    def fake(prompt, model):
        nonlocal replies
        replies += 1
        if "Produce findings" in prompt:
            return "NO-FINDINGS", None
        return json.dumps({"verdict": "APPLIES", "quote": "this exact sentence never appears anywhere"}), None
    rh.call_model = fake
    code, _ = run_main(["--docs", *docs, "--question", q, "--out", out, "--no-final"])
    rows = results_rows(out)
    assert rows, "no rows recorded"
    assert all(r["verdict"] == "OFF-LIST" and r["quote_ok"] == "false" for r in rows), \
        "made-up quote entered the record: %s" % rows
    assert code == 1, "exit %d, expected 1" % code

# (b) an off-list answer is recorded OFF-LIST after one retry; run exits 1
def test_b():
    d, docs, q = make_env()
    out = os.path.join(d, "out")
    calls = []
    def fake(prompt, model):
        calls.append(1)
        if "Produce findings" in prompt:
            return "NO-FINDINGS", None
        return json.dumps({"verdict": "MAYBE", "quote": ""}), None
    rh.call_model = fake
    code, _ = run_main(["--docs", *docs, "--question", q, "--out", out, "--no-final"])
    rows = results_rows(out)
    assert len(rows) == len(rh.split_document(os.path.basename(docs[0]), DOC1)) + \
        len(rh.split_document(os.path.basename(docs[1]), DOC2)), "wrong row count"
    assert all(r["verdict"] == "OFF-LIST" for r in rows), rows
    # one retry per section: exactly twice as many section calls as sections
    n_sections = len(rows)
    assert len(calls) == 2 * n_sections, "expected one retry per section, calls=%d sections=%d" % (len(calls), n_sections)
    assert code == 1, "exit %d, expected 1" % code

# (c) a section whose call fails shows as unanswered and the run exits 1
def test_c():
    d, docs, q = make_env()
    out = os.path.join(d, "out")
    def fake(prompt, model):
        if "Produce findings" in prompt:
            return "NO-FINDINGS", None
        return None, "call exited 1; stderr tail: simulated outage"
    rh.call_model = fake
    code, _ = run_main(["--docs", *docs, "--question", q, "--out", out, "--no-final"])
    rows = results_rows(out)
    assert all(r["verdict"] == "OFF-LIST" and r["quote_ok"] == "false" for r in rows), rows
    assert code == 1, "exit %d, expected 1" % code

# (d) a cut-off results.tsv is refused
def test_d():
    d, docs, q = make_env()
    out = os.path.join(d, "out"); os.makedirs(out)
    p = os.path.join(out, "results.tsv")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(rh.RESULTS_HEADER + "\nabc\tdef")  # last byte is NOT a newline
    rh.call_model = honest_stub()
    code, _ = run_main(["--docs", *docs, "--question", q, "--out", out, "--no-final"])
    assert code == 4, "exit %d, expected 4" % code

# (e) an unreadable input exits 4
def test_e():
    d, docs, q = make_env()
    out = os.path.join(d, "out")
    rh.call_model = honest_stub()
    code, _ = run_main(["--docs", os.path.join(d, "missing.md"), docs[1],
                        "--question", q, "--out", out, "--no-final"])
    assert code == 4, "exit %d, expected 4" % code

# (f) a final-read finding citing a row that does not exist is refused
def test_f():
    d, docs, q = make_env()
    out = os.path.join(d, "out")
    def fake(prompt, model):
        if "Produce findings" in prompt:
            return "FINDING: spending is checked | ROWS: doc1.md:999-999:deadbeef", None
        body = prompt.split("SECTION:\n", 1)[1]
        return honest_reply(body), None
    rh.call_model = fake
    code, _ = run_main(["--docs", *docs, "--question", q, "--out", out])
    with open(os.path.join(out, "final.md"), encoding="utf-8") as fh:
        final = fh.read()
    assert "REFUSED" in final and "doc1.md:999-999:deadbeef" in final, final
    assert "FINDING: spending is checked | ROWS: doc1.md:999-999:deadbeef" not in \
        [l for l in final.splitlines() if l.startswith("FINDING:")], "refused finding was kept"

# (g) an honest run over the same fixtures exits 0, every section answered; check-record agrees
def test_g():
    d, docs, q = make_env()
    out = os.path.join(d, "out")
    rh.call_model = honest_stub()
    code, _ = run_main(["--docs", *docs, "--question", q, "--out", out])
    rows = results_rows(out)
    legal = set(rh.VERDICTS) | {"OFF-LIST"}
    assert all(r["verdict"] in legal for r in rows), rows
    assert all(r["verdict"] != "OFF-LIST" for r in rows), "honest run still had OFF-LIST rows"
    n_sections = len(rh.split_document(os.path.basename(docs[0]), DOC1)) + \
        len(rh.split_document(os.path.basename(docs[1]), DOC2))
    assert len(rows) == n_sections, "rows=%d sections=%d" % (len(rows), n_sections)
    assert code == 0, "exit %d, expected 0" % code
    cov = open(os.path.join(out, "coverage.md"), encoding="utf-8").read()
    assert "sections examined: %d" % n_sections in cov, cov
    # the doc with no APPLIES (doc2 has none of the spending phrase) is listed with zero APPLIES
    assert "doc2.md: 0" in cov, cov
    # and --check-record over the same record passes
    code2, _ = run_main(["--check-record", os.path.join(out, "results.tsv"), "--docs", *docs])
    assert code2 == 0, "check-record exit %d, expected 0" % code2


check("a", "made-up quote refused", test_a)
check("b", "off-list answer retried once then OFF-LIST, exit 1", test_b)
check("c", "failed call leaves the section unanswered, exit 1", test_c)
check("d", "cut-off results.tsv refused (exit 4)", test_d)
check("e", "unreadable input exits 4", test_e)
check("f", "final-read finding citing a missing row refused", test_f)
check("g", "honest run exits 0 with every section answered", test_g)


# ---- card 4.1: quote lists and the captain ----

def req_rows(out_dir):
    rows = results_rows(out_dir)
    return [r for r in rows if r["req_id"]]

def test_h():
    # a list with one real quote and one made-up quote: the real one is kept as a row,
    # the made-up one is dropped and counted, exit 0
    d, docs, q = make_env()
    out = os.path.join(d, "out")
    real = "The quarterly review checks spending against plan values and refuses guesses."
    def fake(prompt, model):
        if "Produce findings" in prompt:
            return "NO-FINDINGS", None
        body = prompt.split("SECTION:\n", 1)[1]
        m = re.search(r"[^.]*spending[^.]*\.", body, re.S)
        if m:
            return json.dumps({"verdict": "APPLIES",
                               "quotes": [m.group(0).strip(), "this exact sentence never appears anywhere"]}), None
        return json.dumps({"verdict": "DOES-NOT-APPLY", "quote": ""}), None
    rh.call_model = fake
    code, _ = run_main(["--docs", *docs, "--question", q, "--out", out, "--no-final"])
    rows = req_rows(out)
    assert len(rows) == 1, "expected exactly one kept-quote row, got %s" % rows
    assert rows[0]["req_id"] == "R001" and rows[0]["verdict"] == "APPLIES", rows
    assert rh.norm(real) in rows[0]["quote"], rows
    assert rows[0]["quotes_dropped"] == "1", rows
    cov = open(os.path.join(out, "coverage.md"), encoding="utf-8").read()
    assert "quotes dropped: 1" in cov, cov
    assert "total requirements: 1" in cov, cov
    assert code == 0, "exit %d, expected 0" % code

def test_i():
    # a list where every quote is made up: retried once, then OFF-LIST, exit 1
    d, docs, q = make_env()
    out = os.path.join(d, "out")
    calls = []
    def fake(prompt, model):
        calls.append(1)
        if "Produce findings" in prompt:
            return "NO-FINDINGS", None
        return json.dumps({"verdict": "APPLIES",
                           "quotes": ["made up one", "made up two"]}), None
    rh.call_model = fake
    code, _ = run_main(["--docs", *docs, "--question", q, "--out", out, "--no-final"])
    rows = results_rows(out)
    assert all(r["verdict"] == "OFF-LIST" and r["quote_ok"] == "false" for r in rows), rows
    n_sections = len(rows)
    assert len(calls) == 2 * n_sections, "expected one retry per section, calls=%d" % len(calls)
    assert code == 1, "exit %d, expected 1" % code

def captain_env():
    """An honest run first (so results.tsv carries R001), then a plan file."""
    d, docs, q = make_env()
    out = os.path.join(d, "out")
    rh.call_model = honest_stub()
    code, _ = run_main(["--docs", *docs, "--question", q, "--out", out, "--no-final"])
    assert code == 0, "honest run exit %d, expected 0" % code
    plan = os.path.join(d, "planA.md")
    open(plan, "w", encoding="utf-8").write("# Plan A\nThe quarterly review step checks spending.\n")
    return d, docs, q, out, plan

CAPTAIN_ALL_MET = "R001 | MET | the quarterly review step in plan A\n"

def test_j():
    # captain reply that skips a requirement: that requirement is UNANSWERED, exit 1
    d, docs, q, out, plan = captain_env()
    def fake(prompt, model, allow_read=False):
        return "", None  # captain answers nothing
    rh.call_model = fake
    code, _ = run_main(["--captain", os.path.join(out, "results.tsv"), "--plans", plan,
                        "--docs", *docs, "--out", os.path.join(d, "cap")])
    with open(os.path.join(d, "cap", "captain.tsv"), encoding="utf-8") as fh:
        cap = fh.read()
    assert "R001\t" in cap and "UNANSWERED" in cap, cap
    assert code == 1, "exit %d, expected 1" % code

def test_k():
    # captain reply that answers one requirement twice: UNANSWERED, exit 1
    d, docs, q, out, plan = captain_env()
    def fake(prompt, model, allow_read=False):
        return CAPTAIN_ALL_MET + CAPTAIN_ALL_MET, None
    rh.call_model = fake
    code, _ = run_main(["--captain", os.path.join(out, "results.tsv"), "--plans", plan,
                        "--docs", *docs, "--out", os.path.join(d, "cap")])
    with open(os.path.join(d, "cap", "captain.tsv"), encoding="utf-8") as fh:
        cap = fh.read()
    assert "UNANSWERED" in cap, cap
    assert code == 1, "exit %d, expected 1" % code

def test_l():
    # captain reply with an off-list verdict: UNANSWERED, exit 1
    d, docs, q, out, plan = captain_env()
    def fake(prompt, model, allow_read=False):
        return "R001 | MAYBE | a verdict that is not on the list\n", None
    rh.call_model = fake
    code, _ = run_main(["--captain", os.path.join(out, "results.tsv"), "--plans", plan,
                        "--docs", *docs, "--out", os.path.join(d, "cap")])
    with open(os.path.join(d, "cap", "captain.tsv"), encoding="utf-8") as fh:
        cap = fh.read()
    assert "UNANSWERED" in cap, cap
    assert code == 1, "exit %d, expected 1" % code

def test_m():
    # honest captain reply: every requirement answered, findings.md lists the UNMET one, exit 0
    d, docs, q, out, plan = captain_env()
    def fake(prompt, model, allow_read=False):
        return "R001 | UNMET | nothing in plan A names the quarterly review\n", None
    rh.call_model = fake
    code, _ = run_main(["--captain", os.path.join(out, "results.tsv"), "--plans", plan,
                        "--docs", *docs, "--out", os.path.join(d, "cap")])
    with open(os.path.join(d, "cap", "captain.tsv"), encoding="utf-8") as fh:
        cap = fh.read()
    assert "UNMET\tnothing in plan A names the quarterly review" in cap, cap
    find = open(os.path.join(d, "cap", "findings.md"), encoding="utf-8").read()
    assert "R001" in find and "UNMET" in find and "quarterly review" in find, find
    assert os.path.exists(os.path.join(d, "cap", "captain.raw.txt")), "raw reply missing"
    assert code == 0, "exit %d, expected 0" % code

check("h", "list with one real and one made-up quote: real kept, made-up dropped and counted, exit 0", test_h)
check("i", "list where every quote is made up: retried once, then OFF-LIST, exit 1", test_i)
check("j", "captain reply that skips a requirement: UNANSWERED, exit 1", test_j)
check("k", "captain reply that answers one requirement twice: UNANSWERED, exit 1", test_k)
check("l", "captain reply with an off-list verdict: UNANSWERED, exit 1", test_l)
check("m", "honest captain reply: findings.md lists the UNMET one, exit 0", test_m)

sys.exit(0 if all(RESULTS) else 1)
