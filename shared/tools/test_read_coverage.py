#!/usr/bin/env python3
"""test_read_coverage.py -- Run: python3 shared/tools/test_read_coverage.py (stdlib only; temp
folder fixtures; placeholder paths only -- no personal paths, no emails). Prints one PASS/FAIL line
per planted case (a) to (f); exits 0 only if all pass. ALLOW cases first.

Cases:
  (a) full read        — every line opened with Read → FULL, exit 0
  (b) partial read     — offset skips the tail → PARTIAL with gaps, exit 1
  (c) failed read      — the only Read call errored → counts as nothing, exit 1
  (d) shell read       — file read via cat in Bash → "read through the shell, not counted", exit 1
  (e) broken record    — garbage lines counted and reported; unreadable record → exit 4,
                         COULD NOT READ TRANSCRIPT
  (f) --documents-only — a .py file in the list is skipped, only the .md is examined
  (g) wc-only shell touch is NOT a shell read: `wc -l f | tail -3` counts, never reads
  (h) transcript-only mode — no FILE args; the file is discovered from the record
        (h1) full read → FULL, exit 0
        (h2) partial read → PARTIAL, exit 1
        (h3) --documents-only skips a .py the record shows being read"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "read_coverage.py")

DOC = "\n".join(f"doc line {i}" for i in range(1, 31)) + "\n"          # 30 lines
CODE = "\n".join(f"code_line_{i} = {i}" for i in range(1, 21)) + "\n"  # 20 lines


def run_tool(tmp, transcript_lines, files=None, extra=None):
    tr = os.path.join(tmp, "record.jsonl")
    with open(tr, "w", encoding="utf-8") as fh:
        for l in transcript_lines:
            fh.write(l + "\n")
    cmd = [sys.executable, TOOL] + (extra or []) + [tr] + (files or [])
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout


def read_call(uid, path, offset=None, limit=None):
    inp = {"file_path": path}
    if offset:
        inp["offset"] = offset
    if limit:
        inp["limit"] = limit
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": uid, "name": "Read", "input": inp}]}}


def result_line(uid, err=False):
    return json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": uid, "is_error": err,
         "content": "error" if err else "ok"}]}})


def bash_call(uid, text):
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": uid, "name": "Bash",
         "input": {"command": f"cat {text}"}}]}})


def main():
    failures = []
    results = []

    def check(name, cond, detail=""):
        results.append(name)
        if cond:
            print(f"PASS {name}")
        else:
            failures.append(name)
            print(f"FAIL {name} {detail}")

    tmp = tempfile.mkdtemp(prefix="test_read_coverage_")
    doc = os.path.join(tmp, "doc.md")
    code = os.path.join(tmp, "script.py")
    open(doc, "w", encoding="utf-8").write(DOC)
    open(code, "w", encoding="utf-8").write(CODE)
    doc_r = os.path.realpath(doc)

    # (a) full read
    rc, out = run_tool(tmp, [json.dumps(read_call("r1", doc)), result_line("r1")], [doc])
    check("full", rc == 0 and "FULL 30/30" in out and "EXAMINED 1 files" in out, out)

    # (b) partial read: offset 10 → lines 10-30 opened, 1-9 are gaps
    rc, out = run_tool(tmp, [json.dumps(read_call("r1", doc, offset=10)), result_line("r1")], [doc])
    check("partial", rc == 1 and "PARTIAL 21/30" in out and "gaps: 1-9" in out, out)

    # (c) failed read: the only Read errored → counts as nothing, all 30 lines are gaps
    rc, out = run_tool(tmp, [json.dumps(read_call("r1", doc)), result_line("r1", err=True)], [doc])
    check("failed", rc == 1 and "PARTIAL 0/30" in out and "gaps: 1-30" in out, out)

    # (d) shell read: cat in a Bash call names the file
    rc, out = run_tool(tmp, [bash_call("b1", doc_r)], [doc])
    check("shell", rc == 1 and "read through the shell, not counted" in out
          and "FULL" not in out.splitlines()[0].split(" errors")[0], out)

    # (e) broken record: garbage lines reported; and an unreadable record exits 4
    garbage = ["this is not json", "{also bad"]
    rc, out = run_tool(tmp, garbage + [json.dumps(read_call("r1", doc)), result_line("r1")], [doc])
    check("broken-lines", rc == 0 and "WARNING: 2 transcript line(s)" in out, out)
    bad_tr = os.path.join(tmp, "broken.jsonl")
    open(bad_tr, "w", encoding="utf-8").write("not json at all\n{still not\n")
    p = subprocess.run([sys.executable, TOOL, bad_tr, doc], capture_output=True, text=True)
    check("unreadable", p.returncode == 4 and "COULD NOT READ TRANSCRIPT" in p.stdout, p.stdout)
    p = subprocess.run([sys.executable, TOOL, os.path.join(tmp, "missing.jsonl"), doc],
                       capture_output=True, text=True)
    check("missing-record", p.returncode == 4 and "COULD NOT READ TRANSCRIPT" in p.stdout, p.stdout)

    # (f) --documents-only skips the .py file
    lines = [json.dumps(read_call("r1", doc, offset=5)), result_line("r1"),
             json.dumps(read_call("r2", code)), result_line("r2")]
    rc, out = run_tool(tmp, lines, [doc, code], extra=["--documents-only"])
    check("documents-only", rc == 1 and "EXAMINED 1 files" in out
          and "doc.md" in out and "script.py" not in out, out)

    # (g) wc-only shell touch is NOT a shell read: `wc -l f | tail -3` counts, never reads
    wc_call = json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "w1", "name": "Bash",
         "input": {"command": f"wc -l {doc_r} | tail -3"}}]}})
    rc, out = run_tool(tmp, [wc_call], [doc])
    check("wc-not-a-read", rc == 1 and "read through the shell" not in out
          and "PARTIAL 0/30" in out, out)

    # (h) transcript-only mode: the file list comes from the record itself
    # (h1) full read
    rc, out = run_tool(tmp, [json.dumps(read_call("r1", doc)), result_line("r1")])
    check("transcript-only-full", rc == 0 and "FULL 30/30" in out
        and "EXAMINED 1 files" in out, out)

    # (h2) partial read: offset 10 → lines 1-9 are gaps
    rc, out = run_tool(tmp, [json.dumps(read_call("r1", doc, offset=10)), result_line("r1")])
    check("transcript-only-partial", rc == 1 and "PARTIAL 21/30" in out
        and "gaps: 1-9" in out, out)

    # (h3) --documents-only: the record shows a .py read too, but only the .md is examined
    lines = [json.dumps(read_call("r1", doc, offset=5)), result_line("r1"),
        json.dumps(read_call("r2", code)), result_line("r2")]
    rc, out = run_tool(tmp, lines, extra=["--documents-only"])
    check("transcript-only-documents-only", rc == 1 and "EXAMINED 1 files" in out
        and "doc.md" in out and "script.py" not in out, out)

    print(f"\n{len(results) - len(failures)}/{len(results)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
