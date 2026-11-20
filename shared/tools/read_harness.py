#!/usr/bin/env python3
# not-wired-yet: wiring into autoplan and skills is a separate decision after the measured runs (plan standalone-code-plus-reading-harness)
"""read_harness.py -- the Code+ reading harness (plan standalone-code-plus-reading-harness, cards 2.1 and 4.1).

WHY: a model told to "read this document" can skim and say it read. Code puts a seam on the input:
each document is cut into sections, each section is read by ONE sealed model call with one narrow
question, and code checks every answer's shape and every quote word for word before anything is
recorded. A made-up quote, an off-list verdict or a failed call can never enter the record as a
legal answer. Card 4.1 splits the jobs: the cheap readers only EXTRACT (a section answer may carry
a LIST of quotes, one per requirement), and one strong CAPTAIN (Opus) does all the judging against
the plans, answering every quoted requirement exactly once.

USAGE:
  read_harness.py --docs FILE... --question FILE --out FOLDER
        [--section-model glm] [--final-model opus] [--no-final] [--workers 4]
  read_harness.py --check-record RESULTS.tsv [--docs FILE...]
        re-read a finished record; exit 0 only if every section of those docs has at least one
        row, every verdict is on the list, all rows of one section carry the same verdict, and
        every APPLIES/CONTRADICTS quote is re-found in its section. Without --docs the quote
        re-check is skipped and the output says so.
  read_harness.py --captain RESULTS.tsv --plans FILE... --docs FILE... --out FOLDER
        [--final-model opus]
        build the numbered requirement list from results.tsv (req_id, section_id, verdict, quote)
        and call the strong model ONCE -- allowed to Read files and nothing else -- to judge every
        requirement against the plans: one line per requirement, `R001 | VERDICT | reason`, with
        VERDICT one of MET/UNMET/CONFLICT/STALE/NOT-A-REQUIREMENT/NO-OUTCOME. Over 250
        requirements the list is split by document, one call per document (said on stdout).
  read_harness.py --whole --plans FILE... --docs FILE... --task FILE plus the model flag naming the reader: glm, sonnet or opus (ids come from model_ids.py tiers)
        --out FOLDER        (card 5.1)
        ONE call with every file printed in full (line-numbered) in the prompt, no tools, one
        fixed reply shape (heading ledger + findings with CANON/PLAN quotes); code checks the
        ledger against the real headings and every quote against its file; one retry naming what
        was missing. Writes reply.raw.txt, findings.tsv, findings.md, check.md.

OUTPUT: <out>/replies/<section_id>.txt (raw reply, written before the record is touched),
  <out>/results.tsv (tab-separated, header run_id, ts, section_id, verdict, quote_ok, model, ccv,
  quote, req_id, quotes_dropped; one row per KEPT quote for APPLIES/CONTRADICTS, req_id numbered
  R001, R002, ... in document order across the whole run; a section with no quotes keeps its
  single row; quotes_dropped counts the quotes refused for that section; written via temp file +
  os.replace; only the main thread writes it),
  <out>/coverage.md (sections examined, counts per verdict, total requirements, total quotes
  dropped, per document its APPLIES count, every document with zero APPLIES),
  <out>/final.md (the strong model's findings, refused citations marked).
  Captain mode writes <out>/captain.raw.txt (the reply, written before anything else),
  <out>/captain.tsv (req_id, section_id, verdict, reason, quote; an unmet requirement is
  recorded UNANSWERED) and <out>/findings.md (every UNMET, CONFLICT and STALE row, counts per
  verdict, the UNANSWERED count and any REFUSED lines).
  Appending to an existing results.tsv refuses (exit 4) unless its last byte is a newline.

EXIT: 0 complete · 1 incomplete (any OFF-LIST or NO-OUTCOME section verdict, a check-record
  failure, or in captain mode any UNANSWERED or NO-OUTCOME requirement) · 2 usage · 4 could not
  read an input (message printed on stdout AND stderr).

GUARDS: answer contract is {"verdict": one of APPLIES/DOES-NOT-APPLY/CONTRADICTS/NO-OUTCOME,
  "quote": exact words from the section, OR "quotes": [exact words, ...]}; APPLIES and
  CONTRADICTS need at least one quote found word for word in the section (whitespace collapsed);
  quotes that are found are KEPT, quotes that are not found are DROPPED and counted; if NO quote
  survives the answer is bad (one retry, then OFF-LIST). The final reader must answer
  `FINDING: <text> | ROWS: <sid>, ...` lines or the single line NO-FINDINGS; a finding citing a
  section_id absent from results.tsv is written under REFUSED. The captain must answer exactly
  one line per requirement; a requirement with no line, more than one line, or an off-list
  verdict is recorded UNANSWERED; lines naming a req_id that does not exist are listed as
  REFUSED.

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
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from emit.verdicts import CANNOT_READ, read_text, print_cannot_read  # noqa: E402
from model_ids import model_id  # noqa: E402

VERDICTS = ("APPLIES", "DOES-NOT-APPLY", "CONTRADICTS", "NO-OUTCOME")
QUOTE_VERDICTS = ("APPLIES", "CONTRADICTS")
CAPTAIN_VERDICTS = ("MET", "UNMET", "CONFLICT", "STALE", "NOT-A-REQUIREMENT", "NO-OUTCOME")
CAPTAIN_FINDING_VERDICTS = ("UNMET", "CONFLICT", "STALE")
HEAD_RE = re.compile(r"^#{1,6}\s+\S")
MAX_SECTION_LINES = 150
MAX_REQS_ONE_CALL = 250
CALL_TIMEOUT_SECS = 600
RESULTS_HEADER = "run_id\tts\tsection_id\tverdict\tquote_ok\tmodel\tccv\tquote\treq_id\tquotes_dropped"
CAPTAIN_HEADER = "req_id\tsection_id\tverdict\treason\tquote"
GLM_LAUNCHER = os.path.join(os.path.expanduser("~"), ".claude-cheap", "bin", "glm-window.sh")
# The folder handed to glm-window.sh (its working folder): this repo's root.
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

def norm(s):
    """Collapse whitespace, and drop markdown line prefixes (blockquote `>`, list bullets) at line starts.
    A quote that spans two lines of a blockquote is real; without this it was refused as made up
    (nibble run 2026-11-17: 2 of 55 honest answers refused; a checker refusing the truth).
    Markdown emphasis asterisks are dropped too: a quote of bolded text copied WITHOUT the **
    markers is real (whole/glm-1, 2026-11-19: 3 honest quotes refused for exactly this; a
    checker refusing the truth)."""
    s = re.sub(r"(?m)^[ \t]*(?:>[ \t]?)+", "", s or "")
    s = re.sub(r"(?m)^[ \t]*[-*+][ \t]+", "", s)
    s = re.sub(r"\*", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- model call

def _run_command(cmd, input_text=None, timeout_secs=None):
    """Run one external command. stdin from /dev/null, unless input_text is given (the
    whole-document prompt is far too large for argv, so it goes on stdin). stderr is captured,
    never silenced. Returns (stdout_text, None) or (None, error_message_with_stderr_tail)."""
    timeout = timeout_secs or CALL_TIMEOUT_SECS
    try:
        p = subprocess.run(cmd,
                           input=input_text if input_text is not None else subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "call timed out after %ss" % timeout
    except Exception as e:  # launcher missing, spawn failure, ...
        return None, "call could not run (%s: %s)" % (e.__class__.__name__, e)
    err_tail = norm((p.stderr or "")[-300:])
    if p.returncode != 0:
        return None, "call exited %d; stderr tail: %s" % (p.returncode, err_tail or "(none)")
    return p.stdout, None


def call_model(prompt, model, allow_read=False, timeout_secs=None, stdin_prompt=False,
               no_tools=False, usage_out=None):
    """ONE sealed model call, behind one function so tests replace it with a stub.
    allow_read=True hands the model the Read tool and nothing else (the captain).
    no_tools=True allows nothing at all (the whole-document read). stdin_prompt=True sends the
    prompt on stdin instead of argv (it is far too large for argv). usage_out, if given a dict,
    receives the call's usage counts. Returns (reply_text, None) or (None, error_message)."""
    if model == "glm":
        cmd = [GLM_LAUNCHER, REPO_ROOT, "--", "-p"]
        if not stdin_prompt:
            cmd += [prompt]
        cmd += ["--output-format", "json"]
        if allow_read:
            cmd += ["--allowedTools", "Read"]
        elif no_tools:
            cmd += ["--allowedTools", ""]
    elif model in ("opus", "sonnet"):
        # "opus"/"sonnet" are the plan's names for the strong models; the ids come from the tier table.
        cmd = ["claude", "-p"]
        if not stdin_prompt:
            cmd += [prompt]
        cmd += ["--model", model_id("large" if model == "opus" else "medium"),
                "--output-format", "json"]
        if allow_read:
            cmd += ["--allowedTools", "Read"]
        elif no_tools:
            cmd += ["--allowedTools", ""]
    else:
        return None, "unknown model: %s" % model
    out, err = _run_command(cmd, input_text=prompt if stdin_prompt else None,
                            timeout_secs=timeout_secs)
    if err:
        return None, err
    try:
        d = json.loads(out)
    except Exception:
        return None, "stdout was not JSON (%s...)" % (out or "")[:120]
    if usage_out is not None and isinstance(d.get("usage"), dict):
        usage_out.update(d["usage"])
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

def real_headings(text):
    """[(1-based line number, heading line)] for lines matching ^#{1,6}\\s+\\S outside ```
    fences. ONE heading rule for the whole tool: the splitter and the --whole ledger check
    both come here."""
    heads, in_fence = [], False
    for i, l in enumerate(text.split("\n")):
        if l.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and HEAD_RE.match(l):
            heads.append((i + 1, l))
    return heads

def split_document(basename, text):
    """-> [(section_id, section_text)] for one document. Headings are lines matching
    ^#{1,6}\\s+\\S outside ``` fences. Text before the first heading is its own section. A
    section over MAX_SECTION_LINES lines is cut at blank lines into parts of at most
    MAX_SECTION_LINES lines. section_id = <basename>:<first>-<last>:<sha256[:8]>."""
    lines = text.split("\n")
    heads = [ln - 1 for ln, _l in real_headings(text)]
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
    """Check one reply against the answer contract. -> (verdict, kept_quotes, dropped, ok, reason).
    kept_quotes: the quotes found word for word in the section, in the order given. dropped: the
    number of quotes refused. ok=False means a bad answer (retryable); a failed CALL never
    reaches here."""
    m = re.search(r"\{.*\}", reply or "", re.S)
    if not m:
        return "", [], 0, False, "no JSON object in reply"
    try:
        d = json.loads(m.group(0))
    except Exception as e:
        return "", [], 0, False, "unparseable JSON (%s)" % e
    v = d.get("verdict")
    if not isinstance(v, str) or v not in VERDICTS:
        q_disp = d.get("quote") or (d.get("quotes") if isinstance(d.get("quotes"), list) else "")
        return str(v)[:40], [], 0, False, "verdict not on the list"
    if "quotes" in d:
        qs = d.get("quotes")
        if not isinstance(qs, list) or any(not isinstance(x, str) for x in qs):
            return v, [], 0, False, '"quotes" must be a list of strings'
        candidates = qs
    else:
        q = d.get("quote") or ""
        if not isinstance(q, str):
            return v, [], 0, False, '"quote" must be a string'
        candidates = [q] if norm(q) else []
    if v in QUOTE_VERDICTS:
        if not candidates:
            return v, [], 0, False, "%s without a quote" % v
        kept, dropped = [], 0
        for q in candidates:
            if norm(q) and norm(q) in norm(section_text):
                kept.append(q)
            else:
                dropped += 1
        if not kept:
            return v, [], dropped, False, (
                "no quote survived: %d quote(s) not found word for word in the section" % dropped)
        return v, kept, dropped, True, ""
    return v, [], 0, True, ""


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


def parse_captain_reply(reply, req_ids):
    """Check the captain's reply against its contract. -> (answers, unanswered, refused).
    answers: {req_id: (verdict, reason)} kept only when the req_id exists, appears on exactly
    one line, and the verdict is on the list. unanswered: req_ids with no line, more than one
    line, or an off-list verdict. refused: lines naming a req_id that does not exist (or lines
    not in the answer contract at all)."""
    answers, refused = {}, []
    seen = {}  # req_id -> list of (verdict, reason)
    for line in (reply or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(R\d+)\s*\|\s*(\S+)\s*\|\s*(.*)$", line)
        if not m:
            refused.append(line)
            continue
        rid, v, reason = m.group(1), m.group(2), m.group(3).strip()
        if rid not in req_ids:
            refused.append(line)
            continue
        seen.setdefault(rid, []).append((v, reason))
    for rid in req_ids:
        lines = seen.get(rid, [])
        if len(lines) == 1 and lines[0][0] in CAPTAIN_VERDICTS:
            answers[rid] = (lines[0][0], lines[0][1])
        else:
            # no line, more than one line, or an off-list verdict
            pass
    unanswered = [rid for rid in req_ids if rid not in answers]
    return answers, unanswered, refused


# ------------------------------------------------------------------ prompts

def section_prompt(question, section_text):
    return ("You are given ONE section of a document and ONE question. Use no tools. Answer with "
            "exactly one line of JSON and nothing else: {\"verdict\": \"APPLIES\" | "
            "\"DOES-NOT-APPLY\" | \"CONTRADICTS\" | \"NO-OUTCOME\", \"quote\": \"<exact words "
            "copied from the section, or empty>\"}. BOTH quote forms are legal: the single form "
            "{\"verdict\": ..., \"quote\": \"...\"} for one statement, or the list form "
            "{\"verdict\": ..., \"quotes\": [\"...\", \"...\"]} when the section holds several "
            "statements -- one statement per quote, each copied word for word from the section, "
            "never merged or reworded. APPLIES and CONTRADICTS need at least one quote copied "
            "word for word from the section; quotes not found in the section are dropped.\n\n"
            "QUESTION: %s\n\nSECTION:\n%s" % (question, section_text))


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


def captain_prompt(plan_paths, doc_paths, reqs):
    """The captain's brief. plan_paths/doc_paths: absolute paths. reqs: [(req_id, section_id,
    verdict, quote)] in list order. The verdict meanings are the plan's seam declaration,
    word for word."""
    lines = [
        "You are the captain. You are given a numbered list of requirements -- statements quoted "
        "word for word from sections of documents -- and a set of plan files. Read EVERY plan "
        "file in full first. You may then open any document section by its line range, which is "
        "inside each section_id (format <basename>:<first>-<last>:<hash>). Use the Read tool and "
        "nothing else.",
        "",
        "Judge EVERY requirement against the plans and answer with exactly one line per "
        "requirement, in this form and nothing else:",
        "R001 | VERDICT | <the plan step that meets it, or one sentence of reason>",
        "VERDICT is one of: MET (names the plan step) - UNMET (nothing in the plans does it) - "
        "CONFLICT (a plan goes against it) - STALE (the plans replace what this text describes "
        "and no step updates it) - NOT-A-REQUIREMENT (the quote binds nothing here) - NO-OUTCOME "
        "(could not decide).",
        "",
        "PLAN FILES:"]
    for p in plan_paths:
        lines.append(p)
    lines += ["", "DOCUMENT FILES (open sections by the line range inside the section_id):"]
    for p in doc_paths:
        lines.append(p)
    lines += ["", "REQUIREMENTS:"]
    for rid, sid, verdict, quote in reqs:
        lines.append("%s\t%s\t%s\t%s" % (rid, sid, verdict, quote))
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
        if len(f) != 10:
            return None, "results file line %d has %d fields, expected 10" % (i, len(f))
        rows.append(dict(run_id=f[0], ts=f[1], section_id=f[2], verdict=f[3],
                         quote_ok=f[4], model=f[5], ccv=f[6], quote=f[7],
                         req_id=f[8], quotes_dropped=f[9]))
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
        verdict, kept, dropped = "OFF-LIST", [], 0
        quote_ok = False
        detail = ""
        for attempt in (1, 2):  # one retry on a bad answer or failed call
            reply, err = call_model(prompt, section_model)
            if err:
                detail = "call failed: %s" % err
                dropped = 0
                continue
            try:
                with open(os.path.join(out, "replies", safe_name(sid)), "w", encoding="utf-8") as fh:
                    fh.write(reply)
            except OSError as e:
                detail = "reply file unwritable (%s)" % e
                continue
            v, k, dp, ok, reason = parse_section_answer(reply, body)
            if ok:
                return sid, v, k, dp, True, ""
            detail = "bad answer (attempt %d): %s" % (attempt, reason)
            verdict, kept, dropped = v or "OFF-LIST", k, dp
        return sid, "OFF-LIST", kept, dropped, False, detail

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        answered = list(ex.map(read_section, sections))

    # Only the main thread touches results.tsv. One row per KEPT quote; req_id numbered in
    # document order across the whole run, only on APPLIES and CONTRADICTS rows.
    new_rows = []
    req_counter = 0
    total_dropped = 0
    for sid, verdict, kept, dropped, quote_ok, _detail in answered:
        total_dropped += dropped
        if verdict in QUOTE_VERDICTS and quote_ok and kept:
            for q in kept:
                req_counter += 1
                new_rows.append("\t".join([run_id, ts(), sid, verdict,
                                           "true" if quote_ok else "false", section_model, ccv,
                                           norm(q), "R%03d" % req_counter, str(dropped)]))
        else:
            last_quote = norm(kept[-1]) if kept else ""
            new_rows.append("\t".join([run_id, ts(), sid, verdict,
                                       "true" if quote_ok else "false", section_model, ccv,
                                       last_quote, "", str(dropped)]))
    header_needed = not existing.strip()
    content = existing + "".join(
        ([RESULTS_HEADER + "\n"] if header_needed else []) + [r + "\n" for r in new_rows])
    try:
        write_results(results_path, content)
    except Exception as e:
        msg = "could not write results.tsv (%s: %s)" % (e.__class__.__name__, e)
        print(msg); print(msg, file=sys.stderr)
        return CANNOT_READ

    # coverage.md -- sections are counted, not rows.
    counts = {v: 0 for v in VERDICTS}
    counts["OFF-LIST"] = 0
    applies_by_doc = {b: 0 for b, _ in docs}
    for sid, verdict, _k, _dp, _ok, _d in answered:
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
           "total requirements: %d" % req_counter,
           "quotes dropped: %d" % total_dropped, "",
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
    incomplete = any(v in ("OFF-LIST", "NO-OUTCOME") for _sid, v, _k, _dp, _ok, _d in answered)
    if final_on:
        rows = [(sid, v, norm(q)) for sid, v, kept, _dp, ok, _d in answered
                if ok and v in QUOTE_VERDICTS for q in kept]
        known = {sid for sid, _v, _k, _dp, _ok, _d in answered}
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
            sum(1 for _sid, v, _k, _dp, _ok, _d in answered if v in ("OFF-LIST", "NO-OUTCOME")),
            len(answered)))
        return 1
    print("COMPLETE: %d sections, all answered on-list" % len(answered))
    return 0


# ------------------------------------------------------------ check-record

def check_record(results_path, docs):
    """-> exit code. Every section of docs must have at least one row, all its rows the same
    verdict; verdicts legal; every APPLIES/CONTRADICTS quote re-found in the section (only when
    --docs was given). Sections are counted, not rows."""
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
    for sid in sorted(by_sid):
        verdicts = {r["verdict"] for _i, r in by_sid[sid]}
        if len(verdicts) > 1:
            problems.append("%s: rows carry different verdicts (%s)" % (
                sid, ", ".join(sorted(verdicts))))
    if docs:
        sections = []
        for basename, text in docs:
            sections.extend((sid, body) for sid, body in split_document(basename, text))
        doc_sids = {sid for sid, _ in sections}
        text_by_sid = dict(sections)
        for sid in sorted(doc_sids):
            n = len(by_sid.get(sid, []))
            if n < 1:
                problems.append("%s: no row in the record, expected at least 1" % sid)
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
        note = "no --docs given: at-least-one-row, same-verdict and legal-verdict checks only, quotes NOT re-checked"
    if problems:
        print("CHECK-RECORD FAILED: %d problem(s)" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("CHECK-RECORD OK: %d rows, %d sections, all legal%s" % (
        len(rows), len(by_sid), ("; " + note) if note else ""))
    return 0


# ------------------------------------------------------------------ captain

def captain_run(captain_path, plan_paths, doc_paths, out, model):
    """Judge every requirement in a finished results.tsv against the plans. Returns exit code."""
    rows, err = read_record(captain_path)
    if rows is None:
        print(err); print(err, file=sys.stderr)
        return CANNOT_READ
    problems = []
    plans = []
    for p in plan_paths:
        text, perr = read_text(p, "plan file")
        if perr:
            problems.append(perr)
        else:
            plans.append(p)
    docs = []
    for p in doc_paths:
        text, derr = read_text(p, "input document")
        if derr:
            problems.append(derr)
        else:
            docs.append(p)
    if problems:
        for m in problems:
            print(m); print(m, file=sys.stderr)
        return CANNOT_READ

    reqs = [(r["req_id"], r["section_id"], r["verdict"], r["quote"])
            for r in rows if r["req_id"]]
    req_ids = [rid for rid, _s, _v, _q in reqs]
    if len(req_ids) != len(set(req_ids)):
        msg = "REFUSED: results.tsv carries a duplicate req_id; the record is malformed"
        print(msg); print(msg, file=sys.stderr)
        return CANNOT_READ

    os.makedirs(out, exist_ok=True)
    if len(reqs) > MAX_REQS_ONE_CALL:
        print("requirement list is %d requirements (over %d): splitting by document, one "
              "captain call per document" % (len(reqs), MAX_REQS_ONE_CALL))
        by_doc = {}
        for req in reqs:
            by_doc.setdefault(req[1].rsplit(":", 2)[0], []).append(req)
        reply_parts = []
        for base in by_doc:
            prompt = captain_prompt(plans, docs, by_doc[base])
            reply, cerr = call_model(prompt, model, allow_read=True)
            if cerr:
                reply_parts.append("")
                print("captain call for %s failed: %s" % (base, cerr), file=sys.stderr)
            else:
                reply_parts.append(reply)
        reply = "\n".join(reply_parts)
    else:
        reply, cerr = call_model(captain_prompt(plans, docs, reqs), model, allow_read=True)
        if cerr:
            msg = "the captain call failed: %s" % cerr
            print(msg); print(msg, file=sys.stderr)
            reply = ""
    # The raw reply is written before anything else, failed or not.
    try:
        write_text_file(os.path.join(out, "captain.raw.txt"), (reply or "") + "\n")
    except Exception as e:
        msg = "could not write captain.raw.txt (%s: %s)" % (e.__class__.__name__, e)
        print(msg); print(msg, file=sys.stderr)
        return CANNOT_READ
    if not reply:
        print("the captain reply is empty; every requirement is recorded UNANSWERED")

    answers, unanswered, refused = parse_captain_reply(reply, req_ids)
    quote_by_rid = {rid: q for rid, _s, _v, q in reqs}
    sid_by_rid = {rid: s for rid, s, _v, _q in reqs}
    cap_rows = []
    for rid in req_ids:
        if rid in answers:
            v, reason = answers[rid]
        else:
            v, reason = "UNANSWERED", ""
        cap_rows.append("\t".join([rid, sid_by_rid[rid], v, reason, quote_by_rid[rid]]))
    try:
        write_results(os.path.join(out, "captain.tsv"),
                      CAPTAIN_HEADER + "\n" + "".join(r + "\n" for r in cap_rows))
    except Exception as e:
        msg = "could not write captain.tsv (%s: %s)" % (e.__class__.__name__, e)
        print(msg); print(msg, file=sys.stderr)
        return CANNOT_READ

    # findings.md
    counts = {v: 0 for v in CAPTAIN_VERDICTS}
    counts["UNANSWERED"] = 0
    for rid in req_ids:
        v = answers[rid][0] if rid in answers else "UNANSWERED"
        counts[v] = counts.get(v, 0) + 1
    lines = ["# captain findings", ""]
    finding_rows = [(rid, answers[rid]) for rid in req_ids
                    if rid in answers and answers[rid][0] in CAPTAIN_FINDING_VERDICTS]
    if finding_rows:
        lines.append("UNMET, CONFLICT and STALE requirements:")
        lines.append("")
        for rid, (v, reason) in finding_rows:
            lines.append("- %s | %s | %s" % (rid, sid_by_rid[rid], v))
            lines.append("  quote: %s" % quote_by_rid[rid])
            lines.append("  reason: %s" % reason)
        lines.append("")
    else:
        lines.append("UNMET, CONFLICT and STALE requirements: (none)")
        lines.append("")
    lines.append("counts per verdict: " + ", ".join("%s=%d" % (v, counts[v]) for v in CAPTAIN_VERDICTS))
    lines.append("UNANSWERED count: %d" % counts["UNANSWERED"])
    if refused:
        lines += ["", "REFUSED (named a req_id that does not exist, or not in the answer contract):"]
        lines += ["- " + l for l in refused]
    try:
        write_text_file(os.path.join(out, "findings.md"), "\n".join(lines) + "\n")
    except Exception as e:
        msg = "could not write findings.md (%s: %s)" % (e.__class__.__name__, e)
        print(msg); print(msg, file=sys.stderr)
        return CANNOT_READ

    if counts["UNANSWERED"] or counts["NO-OUTCOME"]:
        print("INCOMPLETE: %d requirement(s) UNANSWERED, %d NO-OUTCOME" % (
            counts["UNANSWERED"], counts["NO-OUTCOME"]))
        return 1
    print("COMPLETE: %d requirements, all answered on-list" % len(req_ids))
    return 0


# ------------------------------------------------------------------- whole

def append_run_log(mode, model, n_files, n_lines, seconds, usage, outcome):
    """Append ONE line for this run to the run log (LOG_PATH, under ~/.claude/run, never inside
    a repo). A log failure warns on stderr and never fails the run. Returns the line written."""
    untested = n_files > TESTED_MAX_FILES or n_lines > TESTED_MAX_LINES
    line = ("%s | mode=%s | model=%s | files=%d | lines=%d | seconds=%.1f | "
        "tokens in=%s out=%s | untested-size=%s | %s" % (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), mode, model,
        n_files, n_lines, seconds,
        usage.get("input_tokens", "unknown"), usage.get("output_tokens", "unknown"),
        "yes" if untested else "no", outcome))
    try:
        d = os.path.dirname(LOG_PATH)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception as e:
        print("run log not written (%s: %s): %s" % (e.__class__.__name__, e, LOG_PATH),
            file=sys.stderr)
    return line

WHOLE_KINDS = ("CONFLICT", "UNMET", "STALE", "TENSION")
WHOLE_MODELS = ("glm", "sonnet", "opus")
WHOLE_TIMEOUT_SECS = 1800
# Plan card 6.1(b): this line is carried verbatim in every whole-run check.
HONESTY_LINE = "No model reliably notices what a plan leaves out; a result with no problems found is not proof that nothing is missing."
# Plan card 6.1(d): the tested size, and the run log (NEVER inside a repo).
TESTED_MAX_LINES = 2664
TESTED_MAX_FILES = 8
LOG_PATH = os.path.join(os.path.expanduser("~"), ".claude", "run", "read_harness.log")
WHOLE_RULES = (
    "REPLY RULES -- plain text lines only, one item per line, nothing else:\n"
    "LEDGER | <file label> | <line number> | <heading text>\n"
    "FINDING | <n> | <CONFLICT|UNMET|STALE|TENSION> | <one or two plain sentences>\n"
    "CANON | <n> | <file label> | <line number> | <words quoted from that file>\n"
    "PLAN | <n> | <file label> | <line number> | <words quoted from that file>\n"
    "First the ledger: one LEDGER line for EVERY markdown heading (a line starting with 1-6 "
    "'#' then a space, outside ``` code fences) of EVERY file, in order, with its line number. "
    "Then the findings, numbered 1, 2, 3, ... Every FINDING carries at least one CANON or PLAN "
    "line with the same <n> (a TENSION between two plans may carry two PLAN lines and no CANON "
    "line); quotes are copied word for word from the named file. If you find no problems: the "
    "ledger, then the single line NO-FINDINGS. Use no tools; everything you need is in this "
    "prompt.")

def whole_prompt(task_text, files):
    """ONE prompt: the task's text, the reply rules, then every file printed in full, each
    between BEGIN/END markers, every line prefixed with its 1-based line number and a tab."""
    parts = [task_text.strip(), "", WHOLE_RULES, ""]
    for label, text in files:
        lines = text.split("\n")
        parts.append("===== FILE %s BEGINS (%d lines) =====" % (label, len(lines)))
        for i, l in enumerate(lines, 1):
            parts.append("%d\t%s" % (i, l))
        parts.append("===== FILE %s ENDS =====" % label)
        parts.append("")
    return "\n".join(parts)

def parse_whole_reply(reply):
    """Check the reply's SHAPE only. -> dict(ledger, findings, no_findings, stray).
    ledger: [(label, line, text)]. findings: [{"n", "kind", "text", "quotes": [(type, label,
    line, quote)]}] in reply order; a CANON/PLAN line whose <n> names no FINDING is stray.
    stray: lines not in the contract at all."""
    ledger, findings, stray = [], [], []
    no_findings = False
    by_n = {}
    for raw in (reply or "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line == "NO-FINDINGS":
            no_findings = True
            continue
        m = re.match(r"^LEDGER\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*(.*)$", line)
        if m:
            ledger.append((m.group(1), int(m.group(2)), m.group(3)))
            continue
        m = re.match(r"^FINDING\s*\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(.*)$", line)
        if m:
            f = {"n": int(m.group(1)), "kind": m.group(2),
                 "text": m.group(3).strip(), "quotes": []}
            findings.append(f)
            by_n[f["n"]] = f
            continue
        m = re.match(r"^(CANON|PLAN)\s*\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*(.*)$",
                     line)
        if m:
            f = by_n.get(int(m.group(2)))
            if f is None:
                stray.append(line)
            else:
                f["quotes"].append((m.group(1), m.group(3), int(m.group(4)), m.group(5)))
            continue
        stray.append(line)
    return {"ledger": ledger, "findings": findings, "no_findings": no_findings,
            "stray": stray}

def judge_whole_reply(reply, files):
    """Code's check of one whole reply against the real files.
    -> dict(per_file=[(label, found, total)], missing=[(label, line, heading text)],
    overall_found, overall_total, findings_rows=[(n, kind, text, verified, refused, supported)],
    quotes_verified, quotes_total, parsed, unparseable, reason).
    A real heading counts as FOUND if some LEDGER line for that file has a line number within 3
    of the real one AND the text matches after lowercasing, OR the text matches exactly at any
    line number. A quote is VERIFIED if norm(quote) is found in norm(the whole named file)."""
    parsed = parse_whole_reply(reply)
    text_by_label = dict(files)
    labels = set(text_by_label)
    ledger = [l for l in parsed["ledger"] if l[0] in labels]
    stray_labels = [l for l in parsed["ledger"] if l[0] not in labels]
    per_file, missing = [], []
    overall_found = overall_total = 0
    for label, text in files:
        heads = real_headings(text)
        lg = [l for l in ledger if l[0] == label]
        found = 0
        for ln, hl in heads:
            h = norm(re.sub(r"^#+\s*", "", hl))
            hit = False
            for _lab, lline, ltext in lg:
                if abs(lline - ln) <= 3 and norm(ltext).lower() == h.lower():
                    hit = True
                    break
                if norm(ltext) == h:  # exact text at any line number
                    hit = True
                    break
            if hit:
                found += 1
            else:
                missing.append((label, ln, h))
        per_file.append((label, found, len(heads)))
        overall_found += found
        overall_total += len(heads)
    findings_rows = []
    quotes_verified = quotes_total = 0
    for f in parsed["findings"]:
        verified = refused = 0
        for _qtype, label, _line, quote in f["quotes"]:
            quotes_total += 1
            if label in labels and norm(quote) and norm(quote) in norm(text_by_label[label]):
                verified += 1
                quotes_verified += 1
            else:
                refused += 1
        findings_rows.append((f["n"], f["kind"], f["text"], verified, refused,
                              "yes" if verified else "no"))
    kinds_ok = all(f["kind"] in WHOLE_KINDS for f in parsed["findings"])
    has_shape = bool(parsed["ledger"]) or parsed["findings"] or parsed["no_findings"]
    unparseable = (not has_shape) or bool(stray_labels) or not kinds_ok
    reasons = []
    if not has_shape:
        reasons.append("no LEDGER and no FINDING/NO-FINDINGS lines at all")
    if stray_labels:
        reasons.append("LEDGER lines name files that are not in the run: %s"
                       % ", ".join(sorted(set(stray_labels))))
    if not kinds_ok:
        reasons.append("FINDING kinds off the list (allowed: %s)" % ", ".join(WHOLE_KINDS))
    return {"per_file": per_file, "missing": missing,
            "overall_found": overall_found, "overall_total": overall_total,
            "findings_rows": findings_rows,
            "quotes_verified": quotes_verified, "quotes_total": quotes_total,
            "parsed": parsed, "unparseable": unparseable,
            "reason": "; ".join(reasons)}

def whole_run(plan_paths, doc_paths, task_path, model, out):
    """The whole-document forced read (plan card 5.1): one call, the whole files in the prompt,
    no tools, code checks the ledger and every quote. Returns exit code."""
    task_text, err = read_text(task_path, "task file")
    if err:
        print(err); print(err, file=sys.stderr)
        return CANNOT_READ
    files, problems = [], []
    for p in list(plan_paths) + list(doc_paths):
        text, rerr = read_text(p, "input file")
        if rerr:
            problems.append(rerr)
        else:
            files.append((os.path.basename(p), text))
    if problems:
        for m in problems:
            print(m); print(m, file=sys.stderr)
        return CANNOT_READ
    labels = [label for label, _t in files]
    if len(labels) != len(set(labels)):
        dupes = sorted({l for l in labels if labels.count(l) > 1})
        print("usage: two files share a basename; labels must be unique: %s" % ", ".join(dupes),
              file=sys.stderr)
        return 2

    os.makedirs(out, exist_ok=True)
    prompt = whole_prompt(task_text, files)

    def write_raw(name, text):
        try:
            write_text_file(os.path.join(out, name), (text or "") + "\n")
            return None
        except Exception as e:
            return "could not write %s (%s: %s)" % (name, e.__class__.__name__, e)

    usage = {}
    t0 = time.monotonic()
    reply, cerr = call_model(prompt, model, timeout_secs=WHOLE_TIMEOUT_SECS,
                             stdin_prompt=True, no_tools=True, usage_out=usage)
    werr = write_raw("reply.raw.txt", reply)
    if werr:
        print(werr); print(werr, file=sys.stderr)
        return CANNOT_READ
    verdict = judge_whole_reply(reply, files) if not cerr else None

    # One retry, only when the reply is unusable: a missing heading or a broken shape.
    retried = False
    if cerr or verdict["missing"] or verdict["unparseable"]:
        retried = True
        if verdict is not None:
            if verdict["missing"]:
                names = "; ".join("%s line %d (%s)" % ml for ml in verdict["missing"])
                note = ("NOTE: your previous reply was not accepted: these headings are missing "
                        "from the ledger: %s. Answer again, following the rules exactly." % names)
            else:
                note = ("NOTE: your previous reply was not accepted: the reply shape was not "
                        "followed (%s). Answer again, following the rules exactly."
                        % verdict["reason"])
            retry_prompt = prompt + "\n\n" + note
        else:
            retry_prompt = prompt  # a failed call, not a bad reply: same prompt
        usage2 = {}
        reply2, cerr2 = call_model(retry_prompt, model, timeout_secs=WHOLE_TIMEOUT_SECS,
                                   stdin_prompt=True, no_tools=True, usage_out=usage2)
        werr = write_raw("reply.retry.raw.txt", reply2)
        if werr:
            print(werr); print(werr, file=sys.stderr)
            return CANNOT_READ
        reply, cerr, usage = (reply2, cerr2, usage2)
        verdict = judge_whole_reply(reply2, files) if not cerr else None
    seconds = time.monotonic() - t0

    parsed = verdict["parsed"] if verdict else None
    # findings.tsv
    tsv = ["n\tkind\ttext\tquotes_verified\tquotes_refused\tsupported"]
    if verdict:
        for n, kind, text, ver, ref, sup in verdict["findings_rows"]:
            tsv.append("%d\t%s\t%s\t%d\t%d\t%s" % (n, kind, text.replace("\t", " "),
                                                   ver, ref, sup))
    write_text_file(os.path.join(out, "findings.tsv"), "\n".join(tsv) + "\n")
    # findings.md -- nothing here names the model, so a judge can read it blind.
    text_by_label = dict(files)
    md = ["# findings", ""]
    if parsed and parsed["no_findings"] and not parsed["findings"]:
        md.append("NO-FINDINGS")
    elif parsed and parsed["findings"]:
        by_n = {f["n"]: f for f in parsed["findings"]}
        for n, kind, text, ver, ref, sup in verdict["findings_rows"]:
            md += ["## finding %d" % n,
                   "kind: %s" % kind,
                   "text: %s" % text,
                   "quotes verified: %d, refused: %d, supported: %s" % (ver, ref, sup)]
            for qtype, label, line, quote in by_n[n]["quotes"]:
                ok = label in text_by_label and norm(quote) and \
                    norm(quote) in norm(text_by_label[label])
                md.append("- %s %s line %d: %s -- %s" % (
                    qtype, label, line, quote, "VERIFIED" if ok else "REFUSED"))
            md.append("")
    else:
        md.append("(no findings in the reply)")
    # check.md
    ck = ["# whole-run check", "",
          "model: %s" % model,
          "claude version: %s" % claude_version(),
          "retried: %s" % ("yes" if retried else "no")]
    if verdict:
        for label, found, total in verdict["per_file"]:
            ck.append("ledger %s: %d/%d" % (label, found, total))
        ck.append("ledger overall: %d/%d" % (verdict["overall_found"], verdict["overall_total"]))
        if verdict["missing"]:
            ck.append("missing headings: " +
                      "; ".join("%s line %d (%s)" % ml for ml in verdict["missing"]))
        ck.append("quotes: %d/%d verified" % (verdict["quotes_verified"], verdict["quotes_total"]))
        ck.append("findings: %d" % len(verdict["findings_rows"]))
        ck.append("unsupported: %d" % sum(1 for r in verdict["findings_rows"] if r[5] == "no"))
    else:
        ck.append("no judged reply: the model call failed (%s)" % (cerr or ""))
    ck.append("seconds: %.1f" % seconds)
    ck.append("tokens: input=%s cache_read=%s cache_creation=%s output=%s" % (
        usage.get("input_tokens", "unknown"), usage.get("cache_read_input_tokens", "unknown"),
        usage.get("cache_creation_input_tokens", "unknown"),
        usage.get("output_tokens", "unknown")))
    # Plan 6.1(b): no bare "complete". The check file states WHAT WAS PROVEN and carries the
    # honesty line verbatim; the outcome line on stdout names the same facts.
    total_lines = sum(t.count("\n") + 1 for _l, t in files)
    untested = len(files) > TESTED_MAX_FILES or total_lines > TESTED_MAX_LINES
    ck.append("files handed to the model: %d (%d lines)" % (len(files), total_lines))
    if untested:
        ck.append("UNTESTED SIZE: %d lines over %d files is larger than the tested size "
                  "(%d lines over %d files)" % (total_lines, len(files),
                                                TESTED_MAX_LINES, TESTED_MAX_FILES))
    if verdict is None:
        ck.append("proven: nothing about the reply; the model call failed (%s)" % (cerr or ""))
        outcome = "UNPARSEABLE: the model call failed (%s)" % (cerr or "")
        exit_code = 1
    elif verdict["unparseable"]:
        ck.append("proven: nothing about the reply; the reply shape was not followed (%s)"
                  % verdict["reason"])
        outcome = "UNPARSEABLE: %s" % verdict["reason"]
        exit_code = 1
    elif verdict["missing"]:
        ck.append("proven: %d of %d headings listed" % (
            verdict["overall_found"], verdict["overall_total"]))
        ck.append("proven: %d of %d quotes found" % (
            verdict["quotes_verified"], verdict["quotes_total"]))
        ck.append("not proven: every heading listed; %d missing (see above)"
                  % len(verdict["missing"]))
        outcome = "INCOMPLETE: %d heading(s) missing from the ledger" % len(verdict["missing"])
        exit_code = 1
    else:
        ck.append("proven: every file was put in front of the model (%d files, %d lines)"
                  % (len(files), total_lines))
        ck.append("proven: %d of %d headings listed" % (
            verdict["overall_found"], verdict["overall_total"]))
        ck.append("proven: %d of %d quotes found" % (
            verdict["quotes_verified"], verdict["quotes_total"]))
        outcome = ("ledger %d/%d, quotes %d/%d verified, %d finding(s)"
                   % (verdict["overall_found"], verdict["overall_total"],
                      verdict["quotes_verified"], verdict["quotes_total"],
                      len(verdict["findings_rows"])))
        exit_code = 0
    ck.append(HONESTY_LINE)
    findings_text = "\n".join(md) + "\n"
    check_text = "\n".join(ck) + "\n"
    write_text_file(os.path.join(out, "findings.md"), findings_text)
    write_text_file(os.path.join(out, "check.md"), check_text)
    # Plan 6.1(c): the findings and the check also go to stdout, for a caller that cannot open files.
    print(findings_text, end="")
    print(check_text, end="")
    # Plan 6.1(d): the run log, one line.
    log_line = append_run_log("whole", model, len(files), total_lines, seconds, usage, outcome)
    print("whole run %s | model=%s files=%d lines=%d seconds=%.1f tokens in=%s out=%s "
          "| untested-size=%s | run log: %s" % (
        outcome, model, len(files), total_lines, seconds,
        usage.get("input_tokens", "unknown"), usage.get("output_tokens", "unknown"),
        log_line.split("untested-size=")[1].split(" |")[0], LOG_PATH))
    return exit_code

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
    ap.add_argument("--captain")
    ap.add_argument("--plans", nargs="*", default=None)
    ap.add_argument("--whole", action="store_true")
    ap.add_argument("--task")
    ap.add_argument("--model")
    args = ap.parse_args(argv)

    if args.whole:
        missing = [f for f, v in (("--plans", args.plans), ("--docs", args.docs),
                                  ("--task", args.task), ("--model", args.model),
                                  ("--out", args.out)) if not v]
        if missing:
            print("usage: --whole requires %s" % ", ".join(missing), file=sys.stderr)
            return 2
        if args.model not in WHOLE_MODELS:
            print("usage: the reader named with the model flag must be one of %s" % ", ".join(WHOLE_MODELS), file=sys.stderr)
            return 2
        return whole_run(args.plans, args.docs, args.task, args.model, args.out)

    if args.captain:
        if not args.plans or not args.docs or not args.out:
            missing = [f for f, v in (("--plans", args.plans), ("--docs", args.docs),
                                      ("--out", args.out)) if not v]
            print("usage: --captain requires %s" % ", ".join(missing), file=sys.stderr)
            return 2
        return captain_run(args.captain, args.plans, args.docs, args.out, args.final_model)

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
