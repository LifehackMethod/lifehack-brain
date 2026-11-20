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

# The REAL call_model, captured before any test replaces it (the pointer tests exercise the
# real function against a stub command, never a real model).
REAL_CALL_MODEL = rh.call_model

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

# ---- card 5.1: the whole-document forced read ----

WHOLE_PLAN = ("# Plan Alpha\n"
              "## Step one\n"
              "The build step writes the report.\n"
              "## Step two\n"
              "The verify step checks the report.\n")
WHOLE_DOC = ("# Doc Bravo\n"
             "## Findings\n"
             "The quarterly review checks spending against plan values.\n"
             "## Scope\n"
             "This covers houseplant watering only.\n")

def honest_whole_reply():
    """A shape-legal whole reply for the two fixtures: a complete ledger, one finding with a
    verified CANON quote and a verified PLAN quote."""
    led = []
    for label, text in (("planA.md", WHOLE_PLAN), ("docB.md", WHOLE_DOC)):
        for ln, hl in rh.real_headings(text):
            led.append("LEDGER | %s | %d | %s" % (label, ln, hl.lstrip("#").strip()))
    return "\n".join(led + [
        "FINDING | 1 | UNMET | nothing in the plan waters the houseplants.",
        "CANON | 1 | docB.md | 5 | This covers houseplant watering only.",
        "PLAN | 1 | planA.md | 3 | The build step writes the report.",
    ]) + "\n"

def make_whole_env():
    d = tempfile.mkdtemp(prefix="rh_whole_")
    plan = os.path.join(d, "planA.md"); open(plan, "w", encoding="utf-8").write(WHOLE_PLAN)
    doc = os.path.join(d, "docB.md"); open(doc, "w", encoding="utf-8").write(WHOLE_DOC)
    task = os.path.join(d, "task.txt")
    open(task, "w", encoding="utf-8").write("Read these files whole and report problems.\n")
    return d, plan, doc, task

def run_whole(stub):
    code, out, d, _stdout = run_whole_capture(stub)
    return code, out, d

def run_whole_capture(stub, model="medium"):
    """Like run_whole, but also returns what the tool printed on stdout (card 6.1c)."""
    d, plan, doc, task = make_whole_env()
    out = os.path.join(d, "out")
    rh.call_model = stub
    code, stdout = run_main(["--whole", "--plans", plan, "--docs", doc, "--task", task,
                             "--model", model, "--out", out])
    return code, out, d, stdout

def read_file(out_dir, name):
    with open(os.path.join(out_dir, name), encoding="utf-8") as fh:
        return fh.read()

# (n) honest whole reply: exit 0, the check states what was proven and carries the honesty line
def test_n():
    code, out, _d, stdout = run_whole_capture(lambda prompt, model, **kw: (honest_whole_reply(), None))
    assert code == 0, "exit %d, expected 0" % code
    ck = read_file(out, "check.md")
    assert "RESULT=" not in ck and "COMPLETE" not in ck, ck
    assert "proven: every file was put in front of the model (2 files" in ck, ck
    assert "proven: 6 of 6 headings listed" in ck, ck
    assert "proven: 2 of 2 quotes found" in ck, ck
    assert rh.HONESTY_LINE in ck, ck
    assert "retried: no" in ck, ck
    assert "ledger planA.md: 3/3" in ck and "ledger docB.md: 3/3" in ck, ck
    assert os.path.exists(os.path.join(out, "reply.raw.txt")), "raw reply missing"
    tsv = read_file(out, "findings.tsv")
    assert "\tUNMET\t" in tsv and "\tyes\n" in tsv, tsv

# (o) reply missing one heading: retried once, the missing heading named; second reply complete
def test_o():
    calls, prompts = [], []
    def fake(prompt, model, **kw):
        calls.append(1)
        prompts.append(prompt)
        if len(calls) == 1:
            # the ledger is missing docB.md's "Scope" heading (real line 4)
            return honest_whole_reply().replace("LEDGER | docB.md | 4 | Scope\n", ""), None
        return honest_whole_reply(), None
    code, out, _d = run_whole(fake)
    assert len(calls) == 2, "expected one retry, calls=%d" % len(calls)
    assert "Scope" in prompts[1] and "docB.md" in prompts[1] and "line 4" in prompts[1], \
        "the retry prompt must name the missing heading"
    assert code == 0, "exit %d, expected 0" % code
    ck = read_file(out, "check.md")
    assert "retried: yes" in ck, ck
    assert "RESULT=" not in ck and "COMPLETE" not in ck, ck
    assert "proven: 6 of 6 headings listed" in ck, ck
    assert os.path.exists(os.path.join(out, "reply.retry.raw.txt")), "retry raw reply missing"

# (p) reply missing a heading on both tries: exit 1, RESULT=INCOMPLETE, heading listed
def test_p():
    def fake(prompt, model, **kw):
        return honest_whole_reply().replace("LEDGER | docB.md | 4 | Scope\n", ""), None
    code, out, _d = run_whole(fake)
    assert code == 1, "exit %d, expected 1" % code
    ck = read_file(out, "check.md")
    assert "RESULT=" not in ck and "COMPLETE" not in ck, ck
    assert "proven: 5 of 6 headings listed" in ck, ck
    assert "not proven: every heading listed; 1 missing" in ck, ck
    assert "docB.md line 4 (Scope)" in ck, ck

# (q) one real and one made-up quote: made-up REFUSED and counted; finding with only a
#     made-up quote is UNSUPPORTED
def test_q():
    reply = honest_whole_reply().replace(
        "CANON | 1 | docB.md | 5 | This covers houseplant watering only.\n"
        "PLAN | 1 | planA.md | 3 | The build step writes the report.\n",
        "CANON | 1 | docB.md | 5 | This covers houseplant watering only.\n"
        "CANON | 1 | docB.md | 5 | words that appear in no file anywhere.\n"
        "FINDING | 2 | TENSION | a finding whose only quote is made up.\n"
        "CANON | 2 | docB.md | 5 | this quote is invented from nothing.\n")
    code, out, _d = run_whole(lambda prompt, model, **kw: (reply, None))
    assert code == 0, "exit %d, expected 0" % code
    ck = read_file(out, "check.md")
    assert "quotes: 1/3 verified" in ck, ck
    assert "unsupported: 1" in ck, ck
    tsv = read_file(out, "findings.tsv")
    lines = tsv.rstrip("\n").split("\n")
    row2 = [l for l in lines if l.startswith("2\t")][0]
    assert "\tno\n" in "\n" + row2 + "\n" or row2.endswith("\tno"), row2
    fmd = read_file(out, "findings.md")
    assert fmd.count("REFUSED") == 2, fmd
    assert "VERIFIED" in fmd, fmd

# (r) unparseable reply on both tries: exit 1, RESULT=UNPARSEABLE
def test_r():
    calls = []
    def fake(prompt, model, **kw):
        calls.append(1)
        return "I read the documents carefully and have some thoughts to share.\n", None
    code, out, _d = run_whole(fake)
    assert len(calls) == 2, "expected one retry, calls=%d" % len(calls)
    assert code == 1, "exit %d, expected 1" % code
    ck = read_file(out, "check.md")
    assert "RESULT=" not in ck and "COMPLETE" not in ck, ck
    assert "proven: nothing about the reply" in ck, ck
    assert rh.HONESTY_LINE in ck, ck

# (s) findings.md does not contain the model name
def test_s():
    code, out, _d = run_whole(lambda prompt, model, **kw: (honest_whole_reply(), None))
    assert code == 0, "exit %d, expected 0" % code
    fmd = read_file(out, "findings.md")
    assert "sonnet" not in fmd.lower() and "claude" not in fmd.lower(), fmd

check("n", "honest whole reply: exit 0, check states what was proven", test_n)
check("o", "missing one heading: retried once with it named, second reply complete, exit 0", test_o)
check("p", "missing a heading on both tries: exit 1, proven lines name the gap", test_p)
check("q", "made-up quote REFUSED and counted; quoteless finding UNSUPPORTED", test_q)
check("r", "unparseable reply on both tries: exit 1, proven lines name it", test_r)
check("s", "findings.md does not name the model", test_s)

# ---- card 6.1: (a) the real whole-run quote case; (b) no bare complete; (c) stdout; (d) run log ----

# (t) built from the real whole-run case measured 2026-11-19: the file bolds text with ** markers and
#     the reply quotes it without them (finding 4) or keeps the trailing ones (finding 9); both
#     are real quotes and must verify, not be refused. Placeholder text and paths.
BOLD_PLAN = ("# Plan Chi\n"
             "## Step one\n"
             "**The weekly skill gets the FULL rulebook**, not the small version.\n")
BOLD_DOC = ("# Doc Delta\n"
            "## Scope\n"
            "**Skill-SOP items skipped, and why:** the forked test copies.\n")

def test_t():
    d = tempfile.mkdtemp(prefix="rh_bold_")
    plan = os.path.join(d, "planX.md"); open(plan, "w", encoding="utf-8").write(BOLD_PLAN)
    doc = os.path.join(d, "docY.md"); open(doc, "w", encoding="utf-8").write(BOLD_DOC)
    task = os.path.join(d, "task.txt")
    open(task, "w", encoding="utf-8").write("Read these files whole and report problems.\n")
    reply = ("LEDGER | planX.md | 1 | Plan Chi\n"
             "LEDGER | planX.md | 2 | Step one\n"
             "LEDGER | docY.md | 1 | Doc Delta\n"
             "LEDGER | docY.md | 2 | Scope\n"
             "FINDING | 1 | TENSION | the rulebook breadth is contested.\n"
             "PLAN | 1 | planX.md | 3 | The weekly skill gets the FULL rulebook, not the small version.\n"
             "CANON | 1 | docY.md | 3 | Skill-SOP items skipped, and why:** the forked test copies.\n")
    rh.call_model = lambda prompt, model, **kw: (reply, None)
    code, stdout = run_main(["--whole", "--plans", plan, "--docs", doc, "--task", task,
                             "--model", "medium", "--out", os.path.join(d, "out")])
    assert code == 0, "exit %d, expected 0" % code
    ck = open(os.path.join(d, "out", "check.md"), encoding="utf-8").read()
    assert "proven: 2 of 2 quotes found" in ck, ck
    fmd = open(os.path.join(d, "out", "findings.md"), encoding="utf-8").read()
    assert "REFUSED" not in fmd, fmd
    assert fmd.count("VERIFIED") == 2, fmd

# (u) the findings and the check go to stdout as well as the files (card 6.1c)
def test_u():
    code, out, _d, stdout = run_whole_capture(lambda prompt, model, **kw: (honest_whole_reply(), None))
    assert code == 0, "exit %d, expected 0" % code
    for chunk in ("# findings", "kind: UNMET", "VERIFIED", "# whole-run check",
                  "proven: 6 of 6 headings listed", rh.HONESTY_LINE):
        assert chunk in stdout, "stdout missing %r\nstdout was:\n%s" % (chunk, stdout)

# (v) every run prints the handover facts and appends one run-log line (card 6.1d)
def test_v():
    old_log = rh.LOG_PATH
    try:
        d = tempfile.mkdtemp(prefix="rh_log_")
        rh.LOG_PATH = os.path.join(d, "run", "read_harness.log")
        code, out, _d, stdout = run_whole_capture(
            lambda prompt, model, **kw: (honest_whole_reply(), None))
        assert code == 0, "exit %d, expected 0" % code
        for part in ("model=medium", "files=2", "lines=", "seconds=", "tokens", "untested-size=no"):
            assert part in stdout, stdout
        with open(rh.LOG_PATH, encoding="utf-8") as fh:
            lines = fh.read().rstrip("\n").split("\n")
        assert len(lines) == 1, "expected exactly one log line, got %d" % len(lines)
        for part in ("mode=whole", "model=medium", "files=2", "seconds=", "tokens in=", "untested-size=no"):
            assert part in lines[0], lines[0]
        # a second run appends, never overwrites
        run_whole(lambda prompt, model, **kw: (honest_whole_reply(), None))
        with open(rh.LOG_PATH, encoding="utf-8") as fh:
            lines = fh.read().rstrip("\n").split("\n")
        assert len(lines) == 2, "expected two log lines, got %d" % len(lines)
    finally:
        rh.LOG_PATH = old_log

# (w) a run larger than the tested size (2,664 lines over 8 files) is flagged untested size
def test_w():
    old_log = rh.LOG_PATH
    try:
        d, plan, doc, task = make_whole_env()
        big_doc = os.path.join(d, "big.md")
        big = "# Big Doc\n## Only Heading\n" + \
            "\n".join("filler line %d" % i for i in range(2700)) + "\n"
        open(big_doc, "w", encoding="utf-8").write(big)
        out = os.path.join(d, "out")
        rh.LOG_PATH = os.path.join(d, "run", "read_harness.log")
        led = "".join("LEDGER | planA.md | %d | %s\n" % (ln, hl.lstrip("#").strip())
                      for ln, hl in rh.real_headings(WHOLE_PLAN))
        rh.call_model = lambda prompt, model, **kw: (
            led + "LEDGER | big.md | 1 | Big Doc\nLEDGER | big.md | 2 | Only Heading\nNO-FINDINGS\n", None)
        code, stdout = run_main(["--whole", "--plans", plan, "--docs", big_doc, "--task", task,
                                 "--model", "medium", "--out", out])
        assert code == 0, "exit %d, expected 0" % code
        assert "untested-size=yes" in stdout, stdout
        assert "UNTESTED SIZE" in read_file(out, "check.md"), "check.md lacks the untested-size flag"
        with open(rh.LOG_PATH, encoding="utf-8") as fh:
            line = fh.read().strip()
        assert "untested-size=yes" in line, line
    finally:
        rh.LOG_PATH = old_log

check("t", "real whole-run case: quotes of bolded text verify with or without the ** markers", test_t)
check("u", "findings and check printed on stdout as well as written", test_u)
check("v", "handover facts printed and one run-log line appended per run", test_v)
check("w", "run over the tested size is flagged untested size", test_w)

# ---- card 6.2: the small-model pointer ----

def set_pointer_env(path):
    os.environ["LIFEHACK_SMALL_MODEL_CMD_FILE"] = path

def clear_pointer_env():
    os.environ.pop("LIFEHACK_SMALL_MODEL_CMD_FILE", None)

# (x) no pointer: the pointer file is missing, so small is the plugin's own; the run prints
#     route=plugin and the small tier reaches the call
def test_x():
    d = tempfile.mkdtemp(prefix="rh_ptr_")
    set_pointer_env(os.path.join(d, "no-such-pointer-file"))
    old_route, old_log = rh.LAST_ROUTE, rh.LOG_PATH
    rh.LOG_PATH = os.path.join(d, "run", "log")
    try:
        cmd, err = rh.resolve_small_pointer()
        assert err is None and cmd is None, (cmd, err)
        seen = {}
        def fake(prompt, model, **kw):
            seen["model"] = model
            return honest_whole_reply(), None
        code, _out, _d2, stdout = run_whole_capture(fake, model="small")
        assert code == 0, "exit %d, expected 0" % code
        assert seen.get("model") == "small", seen
        assert "route=plugin" in stdout, stdout
    finally:
        clear_pointer_env()
        rh.LAST_ROUTE, rh.LOG_PATH = old_route, old_log

# (y) a working pointer: the command is called <command> <model-id> <prompt-file> <out-file>
#     and its reply file is the reply; the route is printed as pointer
def test_y():
    d = tempfile.mkdtemp(prefix="rh_ptr_")
    stub = os.path.join(d, "stub-model.sh")
    with open(stub, "w", encoding="utf-8") as fh:
        fh.write('#!/bin/sh\n'
                 '# <command> <model-id> <prompt-file> <out-file>\n'
                 'printf \'TIER=%s\\nPROMPT-CHARS=%s\\nSMALL-STUB-REPLY\' "$1" "$(wc -c < "$2" | tr -d \' \')" > "$3"\n')
    os.chmod(stub, 0o755)
    ptr = os.path.join(d, "pointer")
    with open(ptr, "w", encoding="utf-8") as fh:
        fh.write(stub + "\n")
    set_pointer_env(ptr)
    old_route, old_cmd, old_call = rh.LAST_ROUTE, rh.SMALL_MODEL_CMD, rh.call_model
    try:
        cmd, err = rh.resolve_small_pointer()
        assert err is None and cmd == stub, (cmd, err)
        rh.SMALL_MODEL_CMD = cmd
        rh.call_model = REAL_CALL_MODEL  # the real function, against the stub command
        usage = {}
        reply, cerr = rh.call_model("a short prompt for the small model", "small",
                                    usage_out=usage)
        assert cerr is None, cerr
        assert "SMALL-STUB-REPLY" in reply, reply
        assert "TIER=%s" % rh.model_id("small") in reply, reply
        assert rh.LAST_ROUTE == "pointer", rh.LAST_ROUTE
        rh.LAST_ROUTE = "pointer"
        line = rh.route_line()
        assert "route=pointer" in line, line
    finally:
        clear_pointer_env()
        rh.LAST_ROUTE, rh.SMALL_MODEL_CMD, rh.call_model = old_route, old_cmd, old_call

# (z) a broken pointer: the pointer names a command that does not exist -- exit 4, said
#     loudly, no call made, no fallback
def test_z():
    d = tempfile.mkdtemp(prefix="rh_ptr_")
    ptr = os.path.join(d, "pointer")
    with open(ptr, "w", encoding="utf-8") as fh:
        fh.write(os.path.join(d, "command-that-does-not-exist") + "\n")
    set_pointer_env(ptr)
    old_route = rh.LAST_ROUTE
    try:
        cmd, err = rh.resolve_small_pointer()
        assert cmd is None and err and "missing or not executable" in err, (cmd, err)
        d2, plan, doc, task = make_whole_env()
        def forbidden(prompt, model, **kw):
            raise AssertionError("no model call may happen with a broken pointer")
        rh.call_model = forbidden
        code, stdout = run_main(["--whole", "--plans", plan, "--docs", doc, "--task", task,
                                 "--model", "small", "--out", os.path.join(d2, "out")])
        assert code == 4, "exit %d, expected 4" % code
        assert "missing or not executable" in stdout, stdout
    finally:
        clear_pointer_env()
        rh.LAST_ROUTE = old_route

check("x", "no pointer: small is the plugin's own, route=plugin printed", test_x)
check("y", "working pointer: called with model-id, prompt-file, out-file; route=pointer", test_y)
check("z", "broken pointer: exit 4, named loudly, no call, no fallback", test_z)

# (aa) labels written without the extension point at the one file they name; a label naming no
#      file in the run is refused as unparseable, never a crash (found by card 8.2's read job)
def test_aa():
    d = tempfile.mkdtemp(prefix="rh_stem_")
    plan = os.path.join(d, "planX.md"); open(plan, "w", encoding="utf-8").write(BOLD_PLAN)
    doc = os.path.join(d, "docY.md"); open(doc, "w", encoding="utf-8").write(BOLD_DOC)
    task = os.path.join(d, "task.txt")
    open(task, "w", encoding="utf-8").write("Read these files whole and report problems.\n")
    reply = ("LEDGER | planX | 1 | Plan Chi\n"
             "LEDGER | planX | 2 | Step one\n"
             "LEDGER | docY | 1 | Doc Delta\n"
             "LEDGER | docY | 2 | Scope\n"
             "FINDING | 1 | TENSION | the rulebook breadth is contested.\n"
             "PLAN | 1 | planX | 3 | The weekly skill gets the FULL rulebook, not the small version.\n")
    rh.call_model = lambda prompt, model, **kw: (reply, None)
    code, stdout = run_main(["--whole", "--plans", plan, "--docs", doc, "--task", task,
                             "--model", "medium", "--out", os.path.join(d, "out")])
    assert code == 0, "stem labels: exit %d, expected 0\n%s" % (code, stdout)
    stray = reply.replace("LEDGER | docY | 2 | Scope", "LEDGER | nowhere | 2 | Scope")
    rh.call_model = lambda prompt, model, **kw: (stray, None)
    code, stdout = run_main(["--whole", "--plans", plan, "--docs", doc, "--task", task,
                             "--model", "medium", "--out", os.path.join(d, "out2")])
    assert code == 1, "stray label: exit %d, expected 1" % code
    assert "nowhere" in stdout, stdout

check("aa", "labels without extension accepted; a stray label refused, never a crash", test_aa)

sys.exit(0 if all(RESULTS) else 1)
