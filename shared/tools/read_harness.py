#!/usr/bin/env python3
# not-wired-yet: wiring into autoplan and skills is a separate decision after the measured runs (plan standalone-code-plus-reading-harness)
"""read_harness.py -- the Code+ reading harness (plan standalone-code-plus-reading-harness, card 2.1).

WHY: a model told to "read this document" can skim and say it read. Code puts a seam on the input:
each document is cut into sections, each section is read by ONE sealed model call with one narrow
question, and code checks every answer's shape and every quote word for word before anything is
recorded. A made-up quote, an off-list verdict or a failed call can never enter the record as a
legal answer.

USAGE:
  read_harness.py --docs FILE... --question FILE --out FOLDER
        [--section-model glm] [--final-model opus] [--no-final] [--workers 4]
  read_harness.py --check-record RESULTS.tsv [--docs FILE...]
        re-read a finished record; exit 0 only if every section of those docs has exactly one row,
        every verdict is on the list, and every APPLIES/CONTRADICTS quote is re-found in its
        section. Without --docs the quote re-check is skipped (one-row + legal-verdict checks only)
        and the output says so.

OUTPUT: <out>/replies/<section_id>.txt (raw reply, written before the record is touched),
  <out>/results.tsv (tab-separated, header run_id, ts, section_id, verdict, quote_ok, model, ccv,
  quote; written via temp file + os.replace; only the main thread writes it),
  <out>/coverage.md (sections examined, counts per verdict, per document its APPLIES count, every
  document with zero APPLIES), <out>/final.md (the strong model's findings, refused citations
  marked). Appending to an existing results.tsv refuses (exit 4) unless its last byte is a newline.

EXIT: 0 complete · 1 incomplete (any OFF-LIST or NO-OUTCOME section verdict, or a check-record
  failure) · 2 usage · 4 could not read an input (message printed on stdout AND stderr).

GUARDS: answer contract is {"verdict": one of APPLIES/DOES-NOT-APPLY/CONTRADICTS/NO-OUTCOME,
  "quote": exact words from the section}; APPLIES and CONTRADICTS quotes must be found in the
  section after collapsing whitespace; one retry on a bad answer or failed call, then OFF-LIST.
  The final reader must answer `FINDING: <text> | ROWS: <sid>, ...` lines or the single line
  NO-FINDINGS; a finding citing a section_id absent from results.tsv is written under REFUSED.

FAIL_POSTURE: a failed call, a timeout, a non-JSON stdout, is_error=true or an empty reply is
  never a legal answer. stderr of any external command is captured, never silenced, and its tail
  lands in the error message. The model call sits behind one function (call_model) so tests
  replace it with a stub; no test ever calls a real model.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from emit.verdicts import CANNOT_READ, read_text, print_cannot_read  # noqa: E402
from model_ids import model_id  # noqa: E402

VERDICTS = ("APPLIES", "DOES-NOT-APPLY", "CONTRADICTS", "NO-OUTCOME")
QUOTE_VERDICTS = ("APPLIES", "CONTRADICTS")
HEAD_RE = re.compile(r"^#{1,6}\s+\S")
MAX_SECTION_LINES = 150
CALL_TIMEOUT_SECS = 600
RESULTS_HEADER = "run_id\tts\tsection_id\tverdict\tquote_ok\tmodel\tccv\tquote"
GLM_LAUNCHER = os.path.join(os.path.expanduser("~"), ".claude-cheap", "bin", "glm-window.sh")
# The folder handed to glm-window.sh (its working folder): this repo's root.
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

def norm(s):
    """Collapse whitespace, and drop markdown line prefixes (blockquote `>`, list bullets) at line starts.
    A quote that spans two lines of a blockquote is real; without this it was refused as made up
    (nibble run 2026-11-17: 2 of 55 honest answers refused; a checker refusing the truth)."""
    s = re.sub(r"(?m)^[ \t]*(?:>[ \t]?)+", "", s or "")
    s = re.sub(r"(?m)^[ \t]*[-*+][ \t]+", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- model call

def _run_command(cmd):
    """Run one external command with stdin from /dev/null. stderr is captured, never silenced.
    Returns (stdout_text, None) or (None, error_message_with_stderr_tail)."""
    try:
        p = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=CALL_TIMEOUT_SECS)
    except subprocess.TimeoutExpired:
        return None, "call timed out after %ss" % CALL_TIMEOUT_SECS
    except Exception as e:  # launcher missing, spawn failure, ...
        return None, "call could not run (%s: %s)" % (e.__class__.__name__, e)
    err_tail = norm((p.stderr or "")[-300:])
    if p.returncode != 0:
        return None, "call exited %d; stderr tail: %s" % (p.returncode, err_tail or "(none)")
    return p.stdout, None


def call_model(prompt, model):
    """ONE sealed model call, behind one function so tests replace it with a stub.
    Returns (reply_text, None) or (None, error_message)."""
    if model == "glm":
        cmd = [GLM_LAUNCHER, REPO_ROOT, "--", "-p", prompt, "--output-format", "json"]
    elif model == "opus":
        # "opus" is the plan's name for the strong model; the id itself comes from the tier table.
        cmd = ["claude", "-p", prompt, "--model", model_id("large"), "--output-format", "json"]
    else:
        return None, "unknown model: %s" % model
    out, err = _run_command(cmd)
    if err:
        return None, err
    try:
        d = json.loads(out)
    except Exception:
        return None, "stdout was not JSON (%s...)" % (out or "")[:120]
    if d.get("is_error"):
        return None, "is_error=true (%s)" % str(d.get("result", ""))[:200]
    reply = d.get("result")
    if not isinstance(reply, str) or not reply.strip():
        return None, "empty reply"
    return reply, None


def claude_version():
    """`claude --version` output, or the string UNKNOWN if that call itself fails."""
    out, err = _run_command(["claude", "--version"])
    text = norm(out)
    return text if out is not None and text else "UNKNOWN"


# ------------------------------------------------------------------ splitting

def split_document(basename, text):
    """-> [(section_id, section_text)] for one document. Headings are lines matching
    ^#{1,6}\\s+\\S outside ``` fences. Text before the first heading is its own section. A
    section over MAX_SECTION_LINES lines is cut at blank lines into parts of at most
    MAX_SECTION_LINES lines. section_id = <basename>:<first>-<last>:<sha256[:8]>."""
    lines = text.split("\n")
    heads, in_fence = [], False
    for i, l in enumerate(lines):
        if l.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and HEAD_RE.match(l):
            heads.append(i)
    if heads and heads[0] == 0:
        starts = list(heads)
    elif heads:
        starts = [0] + list(heads)
    else:
        starts = [0]
    ends = starts[1:] + [len(lines)]
    out = []
    for s, e in zip(starts, ends):
        chunk = lines[s:e]
        for part, offs in cut_long_section(chunk):
            body = "\n".join(part)
            first = s + offs + 1
            last = s + offs + len(part)
            sid = "%s:%d-%d:%s" % (basename, first, last, hashlib.sha256(body.encode("utf-8")).hexdigest()[:8])
            out.append((sid, body))
    return out


def cut_long_section(lines):
    """Cut a chunk of lines at blank lines into parts of at most MAX_SECTION_LINES lines.
    -> [(part_lines, offset_within_chunk)]. A part with no blank line to cut at is cut at the
    hard limit, so the function always makes progress and every part is <= the limit."""
    if len(lines) <= MAX_SECTION_LINES:
        return [(lines, 0)]
    parts, cur, off = [], [], 0
    for l in lines:
        cur.append(l)
        if len(cur) >= MAX_SECTION_LINES:
            cut = next((i for i in range(len(cur) - 1, 0, -1) if not cur[i].strip()), None)
            if cut:
                parts.append((cur[:cut], off))
                cur = cur[cut:]
                off += cut
            else:
                parts.append((cur, off))
                cur, off = [], off + len(cur)
    if cur:
        parts.append((cur, off))
    return parts


# ------------------------------------------------------------------- grading

def parse_section_answer(reply, section_text):
    """Check one reply against the answer contract. -> (verdict, quote, ok, reason).
    ok=False means a bad answer (retryable); a failed CALL never reaches here."""
    m = re.search(r"\{.*\}", reply or "", re.S)
    if not m:
        return "", "", False, "no JSON object in reply"
    try:
        d = json.loads(m.group(0))
    except Exception as e:
        return "", "", False, "unparseable JSON (%s)" % e
    v, q = d.get("verdict"), d.get("quote") or ""
    if not isinstance(v, str) or v not in VERDICTS:
        return str(v)[:40], str(q)[:200], False, "verdict not on the list"
    if v in QUOTE_VERDICTS:
        if not norm(q):
            return v, "", False, "%s without a quote" % v
        if norm(q) not in norm(section_text):
            return v, str(q)[:200], False, "quote not found word for word in the section"
    return v, q, True, ""


def parse_final_reply(reply, known_sids):
    """Check the final reader's reply against its contract. -> (findings, refused, unparsed)
    findings: (text, [sids]) kept only when EVERY cited sid exists in results.tsv."""
    findings, refused, unparsed = [], [], []
    if norm(reply) == "NO-FINDINGS":
        return findings, refused, unparsed
    kept_any = False
    for line in (reply or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^FINDING:\s*(.+)\s*\|\s*ROWS:\s*(.+)$", line)
        if not m:
            unparsed.append(line)
            continue
        kept_any = True
        sids = [s.strip() for s in m.group(2).split(",") if s.strip()]
        if sids and all(s in known_sids for s in sids):
            findings.append((m.group(1).strip(), sids))
        else:
            refused.append(line)
    return findings, refused, unparsed


# ------------------------------------------------------------------ prompts

def section_prompt(question, section_text):
    return ("You are given ONE section of a document and ONE question. Use no tools. Answer with "
            "exactly one line of JSON and nothing else: {\"verdict\": \"APPLIES\" | "
            "\"DOES-NOT-APPLY\" | \"CONTRADICTS\" | \"NO-OUTCOME\", \"quote\": \"<exact words "
            "copied from the section, or empty>\"}. APPLIES and CONTRADICTS need a quote copied "
            "word for word from the section.\n\nQUESTION: %s\n\nSECTION:\n%s" % (question, section_text))


def final_prompt(question, rows):
    lines = ["You are given the APPLIES and CONTRADICTS rows from a section-by-section reading of "
             "documents against one question. Produce findings: each finding on exactly one line "
             "of the form", "FINDING: <text> | ROWS: <section_id>, <section_id>",
             "citing the row IDs it rests on. If nothing rises to a finding, answer with the "
             "single line NO-FINDINGS. Use no tools.",
             "Treat a CONTRADICTS row as a claim to confirm, not a fact. Then go through EVERY "
             "APPLIES row as well: each quotes a requirement, and the section reader is weak at "
             "noticing what is missing, so check whether the question's material actually meets "
             "that requirement and report a finding where something required is left undone, "
             "unnamed or unowned.", "",
             "QUESTION: %s" % question, "", "ROWS:"]
    for sid, verdict, quote in rows:
        lines.append("%s\t%s\t%s" % (sid, verdict, quote))
    return "\n".join(lines)


# ------------------------------------------------------------------- writing

def read_record(path):
    """-> (rows, None) or (None, message). rows exclude the header; malformed rows are errors."""
    if not os.path.exists(path):
        return None, "results file does not exist: %s" % path
    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
    except Exception as e:
        return None, "results file unreadable (%s: %s): %s" % (e.__class__.__name__, e, path)
    if not content.strip():
        return None, "results file is empty: %s" % path
    lines = content.rstrip("\n").split("\n")
    rows = []
    for i, ln in enumerate(lines[1:], start=2):
        f = ln.split("\t")
        if len(f) != 8:
            return None, "results file line %d has %d fields, expected 8" % (i, len(f))
        rows.append(dict(run_id=f[0], ts=f[1], section_id=f[2], verdict=f[3],
                         quote_ok=f[4], model=f[5], ccv=f[6], quote=f[7]))
    return rows, None


def write_results(path, content):
    """All-or-nothing write: temp file in the same folder, then os.replace."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_text_file(path, content):
    write_results(path, content)  # same all-or-nothing mechanism


# ------------------------------------------------------------------ run mode

def run_once(docs, question, out, section_model, final_model, workers, final_on=True):
    """One run. docs: [(basename, text)]. Returns exit code int."""
    os.makedirs(os.path.join(out, "replies"), exist_ok=True)
    results_path = os.path.join(out, "results.tsv")

    existing = ""
    if os.path.exists(results_path):
        try:
            with open(results_path, "rb") as fh:
                blob = fh.read()
        except Exception as e:
            msg = "results.tsv unreadable (%s: %s): %s" % (e.__class__.__name__, e, results_path)
            print(msg); print(msg, file=sys.stderr)
            return CANNOT_READ
        if blob and not blob.endswith(b"\n"):
            msg = ("REFUSED: %s is cut off (last byte is not a newline); not appending a run "
                   "to a truncated record" % results_path)
            print(msg); print(msg, file=sys.stderr)
            return CANNOT_READ
        existing = blob.decode("utf-8", "replace")

    # Sections, in document order.
    sections = []  # (sid, text, basename)
    for basename, text in docs:
        for sid, body in split_document(basename, text):
            sections.append((sid, body, basename))

    ccv = claude_version()
    run_id = "rh-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ts = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_name = lambda sid: re.sub(r"[^A-Za-z0-9._:-]+", "_", sid) + ".txt"

    def read_section(item):
        sid, body, _basename = item
        prompt = section_prompt(question, body)
        verdict, quote, quote_ok = "OFF-LIST", "", False
        detail = ""
        for attempt in (1, 2):  # one retry on a bad answer or failed call
            reply, err = call_model(prompt, section_model)
            if err:
                detail = "call failed: %s" % err
                continue
            try:
                with open(os.path.join(out, "replies", safe_name(sid)), "w", encoding="utf-8") as fh:
                    fh.write(reply)
            except OSError as e:
                detail = "reply file unwritable (%s)" % e
                continue
            v, q, ok, reason = parse_section_answer(reply, body)
            if ok:
                return sid, v, q, True, ""
            detail = "bad answer (attempt %d): %s" % (attempt, reason)
            verdict, quote = v or "OFF-LIST", q
        return sid, "OFF-LIST", quote, False, detail

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        answered = list(ex.map(read_section, sections))

    # Only the main thread touches results.tsv.
    new_rows = []
    for sid, verdict, quote, quote_ok, detail in answered:
        new_rows.append("\t".join([run_id, ts(), sid, verdict,
                                   "true" if quote_ok else "false", section_model, ccv,
                                   norm(quote)]))
    header_needed = not existing.strip()
    content = existing + "".join(
        ([RESULTS_HEADER + "\n"] if header_needed else []) + [r + "\n" for r in new_rows])
    try:
        write_results(results_path, content)
    except Exception as e:
        msg = "could not write results.tsv (%s: %s)" % (e.__class__.__name__, e)
        print(msg); print(msg, file=sys.stderr)
        return CANNOT_READ

    # coverage.md
    counts = {v: 0 for v in VERDICTS}
    counts["OFF-LIST"] = 0
    applies_by_doc = {b: 0 for b, _ in docs}
    for sid, verdict, _q, _ok, _d in answered:
        if verdict in counts:
            counts[verdict] += 1
        else:
            counts["OFF-LIST"] += 1
        if verdict == "APPLIES":
            base = sid.rsplit(":", 2)[0]
            if base in applies_by_doc:
                applies_by_doc[base] += 1
    cov = ["# coverage", "", "sections examined: %d" % len(answered),
           "counts per verdict: " + ", ".join("%s=%d" % (v, counts[v]) for v in VERDICTS),
           "OFF-LIST count: %d" % counts["OFF-LIST"], "",
           "APPLIES per input document:"]
    zero = []
    for b, _ in docs:
        cov.append("- %s: %d" % (b, applies_by_doc.get(b, 0)))
        if applies_by_doc.get(b, 0) == 0:
            zero.append(b)
    if zero:
        cov.append("")
        cov.append("documents with zero APPLIES: " + ", ".join(zero))
    else:
        cov.append("")
        cov.append("documents with zero APPLIES: (none)")
    write_text_file(os.path.join(out, "coverage.md"), "\n".join(cov) + "\n")

    # Final read.
    final_lines = []
    incomplete = any(v in ("OFF-LIST", "NO-OUTCOME") for _, v, _, _, _ in answered)
    if final_on:
        rows = [(sid, v, q) for sid, v, q, ok, _d in answered if ok and v in QUOTE_VERDICTS]
        known = {sid for sid, _v, _q, _ok, _d in answered}
        reply, err = call_model(final_prompt(question, rows), final_model)
        if err:
            final_lines = ["# final read", "", "NO-OUTCOME: the final-read call failed: %s" % err]
            incomplete = True
        else:
            findings, refused, unparsed = parse_final_reply(reply, known)
            final_lines = ["# final read", ""]
            if not findings and not refused and not unparsed:
                final_lines.append("NO-FINDINGS")
            for text, sids in findings:
                final_lines.append("FINDING: %s | ROWS: %s" % (text, ", ".join(sids)))
            if refused:
                final_lines += ["", "REFUSED (cited a row that does not exist):"]
                final_lines += ["- " + l for l in refused]
            if unparsed:
                final_lines += ["", "UNPARSED (not in the answer contract):"]
                final_lines += ["- " + l for l in unparsed]
        write_text_file(os.path.join(out, "final.md"), "\n".join(final_lines) + "\n")

    if incomplete:
        print("INCOMPLETE: %d of %d sections are OFF-LIST or NO-OUTCOME" % (
            sum(1 for _, v, _, _, _ in answered if v in ("OFF-LIST", "NO-OUTCOME")), len(answered)))
        return 1
    print("COMPLETE: %d sections, all answered on-list" % len(answered))
    return 0


# ------------------------------------------------------------ check-record

def check_record(results_path, docs):
    """-> exit code. Every section of docs must have exactly one row; verdicts legal; quotes
    re-found in the section (only when --docs was given)."""
    rows, err = read_record(results_path)
    if rows is None:
        print(err); print(err, file=sys.stderr)
        return CANNOT_READ
    problems = []
    by_sid = {}
    for i, r in enumerate(rows):
        by_sid.setdefault(r["section_id"], []).append((i, r))
        if r["verdict"] not in VERDICTS and r["verdict"] != "OFF-LIST":
            problems.append("row %d (%s): verdict %r is not one of %s" % (
                i + 2, r["section_id"], r["verdict"], ", ".join(VERDICTS + ("OFF-LIST",))))
    if docs:
        sections = []
        for basename, text in docs:
            sections.extend((sid, body) for sid, body in split_document(basename, text))
        doc_sids = {sid for sid, _ in sections}
        text_by_sid = dict(sections)
        for sid in sorted(doc_sids):
            n = len(by_sid.get(sid, []))
            if n != 1:
                problems.append("%s: %d rows in the record, expected exactly 1" % (sid, n))
        extra = sorted(set(by_sid) - doc_sids)
        for sid in extra:
            problems.append("%s: row in the record but not a section of the given documents" % sid)
        for sid, _t in sections:
            for _i, r in by_sid.get(sid, []):
                if r["verdict"] in QUOTE_VERDICTS:
                    if norm(r["quote"]) not in norm(text_by_sid[sid]):
                        problems.append("%s: %s quote not found word for word in the section" % (
                            sid, r["verdict"]))
                elif r["verdict"] in ("DOES-NOT-APPLY", "NO-OUTCOME"):
                    pass
        note = ""
    else:
        note = "no --docs given: one-row and legal-verdict checks only, quotes NOT re-checked"
    if problems:
        print("CHECK-RECORD FAILED: %d problem(s)" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("CHECK-RECORD OK: %d rows, %d sections, all legal%s" % (
        len(rows), len(by_sid), ("; " + note) if note else ""))
    return 0


# --------------------------------------------------------------------- main

def load_docs(paths):
    """-> (docs, problems). docs: [(basename, text)] for every readable, non-empty file."""
    docs, problems = [], []
    for p in paths:
        text, err = read_text(p, "input document")
        if err:
            problems.append(err)
        else:
            docs.append((os.path.basename(p), text))
    return docs, problems


def main(argv):
    ap = argparse.ArgumentParser(prog="read_harness.py", add_help=True)
    ap.add_argument("--docs", nargs="*", default=None)
    ap.add_argument("--question")
    ap.add_argument("--out")
    ap.add_argument("--section-model", default="glm")
    ap.add_argument("--final-model", default="opus")
    ap.add_argument("--no-final", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--check-record")
    args = ap.parse_args(argv)

    if args.check_record:
        docs, problems = load_docs(args.docs or [])
        if problems:
            for m in problems:
                print(m); print(m, file=sys.stderr)
            return CANNOT_READ
        return check_record(args.check_record, docs)

    missing = [f for f, v in (("--docs", args.docs), ("--question", args.question),
                              ("--out", args.out)) if v is None]
    if missing:
        print("usage: %s requires %s" % (ap.prog, ", ".join(missing)), file=sys.stderr)
        return 2
    if not args.docs:
        print("usage: --docs needs at least one file", file=sys.stderr)
        return 2
    question, err = read_text(args.question, "question file")
    if err:
        print(err); print(err, file=sys.stderr)
        return CANNOT_READ
    question = question.strip()
    docs, problems = load_docs(args.docs)
    if problems:
        for m in problems:
            print(m); print(m, file=sys.stderr)
        return CANNOT_READ
    return run_once(docs, question, args.out, args.section_model, args.final_model,
                    args.workers, final_on=not args.no_final)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
