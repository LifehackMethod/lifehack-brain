#!/usr/bin/env python3
"""toolbox.py -- generate the TOOLBOX list (system/register/toolbox.md) FROM the register. Never hand-typed.

v2 plan step 2.2. The toolbox is the shared layer a builder should reach for before writing a new tool:
every non-test file under `shared/`, plus the job runner (`system/tools/job-run.sh` and the `*.lib.sh`
libraries it and the runners share), plus the scheduled jobs.

WHAT IS LISTED: register rows of `type: tool` whose path is under `/shared/` or is the job runner / a
`*.lib.sh`, and `type: scheduled` rows. The register is the only list of WHAT exists; a file on disk with no
register row is not listed (the pre-commit new-tool gate keeps that from happening).

GROUPING IS DERIVED FROM THE PATH (GROUP_RULES below), not stored in the register: schema-v1 is strict and
`shared/` already means "shared layer", so no register field was added.

PURPOSE: the register has no purpose field. It is extracted at generate time from the tool's OWN header:
the Python module docstring, or the leading comment block of a shell script. Order tried: a first line of
the form `name -- description`, else a `WHAT:` line, else a `WHY:` line, else the first paragraph.
Cut at the first sentence end, capped at MAX_PURPOSE characters. To change a purpose, edit the tool's header.

USAGE:
  toolbox.py              rewrite system/register/toolbox.md
  toolbox.py --check      exit 1 if the committed toolbox.md differs from what would be generated
  toolbox.py --stdout     print instead of writing
"""
import argparse
import ast
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REGISTER = os.path.join(HERE, "register.jsonl")
OUT = os.path.join(HERE, "toolbox.md")
MAX_PURPOSE = 140

# (group title, predicate on the register path). First match wins; order matters.
GROUP_RULES = [
    ("Models", lambda p: p in ("/shared/tools/model_ids.py", "/system/tools/model.lib.sh")),
    ("Job runner (internal plumbing, not a shared tool)",
     lambda p: p == "/system/tools/job-run.sh" or p.endswith(".lib.sh")),
    ("Notify", lambda p: p.startswith("/shared/notify/")),
    ("Gate and verdicts",
     lambda p: p.startswith(("/shared/gate/", "/shared/emit/")) or p == "/shared/bounded_input.py"
     or os.path.basename(p).startswith("intake_")),
    ("Email", lambda p: os.path.basename(p).startswith("email_")),
    ("Store and sync",
     lambda p: p.startswith("/shared/tools/")),
    ("Paths and roots", lambda p: p.startswith("/shared/")),
]
OTHER = "Other"


def in_scope(row):
    p = row["path"]
    return p.startswith("/shared/") or p == "/system/tools/job-run.sh" or p.endswith(".lib.sh")


def group_of(path):
    for title, pred in GROUP_RULES:
        if pred(path):
            return title
    return OTHER


def _paragraphs(lines):
    paras, cur = [], []
    for ln in lines:
        if ln.strip():
            cur.append(ln.strip())
        elif cur:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    return paras


def _header_lines(path):
    """The tool's own header text as plain lines (docstring for .py, leading comment block otherwise)."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    if path.endswith(".py"):
        try:
            doc = ast.get_docstring(ast.parse(src))
        except SyntaxError:
            doc = None
        if doc:
            return doc.split("\n")
    out = []
    for ln in src.split("\n"):
        if ln.startswith("#!"):
            continue
        if ln.startswith("#"):
            t = ln.lstrip("#").strip()
            if re.fullmatch(r"[\W_]*(LLM CONTEXT)?[\W_]*", t):
                t = ""  # rule lines of box-drawing characters
            out.append(t)
        elif ln.strip() == "" and not out:
            continue
        else:
            break
    return out


def _labelled(lines, label):
    """Text of a `LABEL: ...` block (continuation lines until a blank line or the next LABEL:)."""
    got, on = [], False
    for ln in lines:
        m = re.match(r"^([A-Z]{3,}):\s*(.*)$", ln)
        if m:
            if on:
                break
            on = m.group(1) == label
            if on:
                got.append(m.group(2))
        elif on:
            if not ln.strip():
                break
            got.append(ln.strip())
    return " ".join(got).strip()


def _trim(text):
    text = re.sub(r"\s+", " ", text).strip()
    # first sentence; if that is a stub (under 40 chars), keep going to the next one
    for m in re.finditer(r"(?<!\be\.g)(?<!\bi\.e)(?<=[.!?])\s+(?=[A-Z`(])", text):
        if m.start() >= 40:
            text = text[:m.start()]
            break
    text = text.rstrip(".").replace("|", "/")
    if len(text) > MAX_PURPOSE:
        text = text[:MAX_PURPOSE - 1].rsplit(" ", 1)[0].rstrip(",;:- ") + "…"
    return text


def purpose_of(path):
    lines = _header_lines(path)
    paras = _paragraphs(lines)
    if paras:
        m = re.match(r"^\S+\s+(?:—|--|-)\s+(.*)$", paras[0])
        if m:
            return _trim(m.group(1))
    for label in ("WHAT", "WHY"):
        t = _labelled(lines, label)
        if t:
            return _trim(t)
    return _trim(paras[0]) if paras else "(no header: add a docstring or header comment)"


def _every(seconds):
    s = int(seconds)
    for unit, n in (("d", 86400), ("h", 3600), ("min", 60)):
        if s % n == 0:
            return f"every {s // n}{unit}"
    return f"every {s}s"


def load_rows(register=REGISTER):
    with open(register, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def generate(root=ROOT, rows=None):
    rows = load_rows() if rows is None else rows
    groups, seen = {}, set()
    for r in sorted(rows, key=lambda r: r["path"]):
        if r["type"] != "tool" or not in_scope(r) or r["path"] in seen:
            continue
        full = os.path.join(root, r["path"].lstrip("/"))
        if not os.path.isfile(full):
            continue
        seen.add(r["path"])
        groups.setdefault(group_of(r["path"]), []).append((r["path"], purpose_of(full)))
    order = [t for t, _ in GROUP_RULES] + [OTHER]
    out = [
        "# Toolbox",
        "",
        "GENERATED by `system/register/toolbox.py` from `register.jsonl` and each tool's own header. Do not edit by",
        "hand: change the tool's header, then run `python3 system/register/toolbox.py`. "
        "`--check` fails when this file is stale.",
        "",
        "Shared layer = everything under `shared/`. Look here before writing a new tool.",
    ]
    for title in order:
        if title in groups:
            out += ["", f"## {title}", ""]
            out += [f"- `{p}` · {d}" for p, d in groups[title]]
    jobs = sorted((r for r in rows if r["type"] == "scheduled"), key=lambda r: r["schedule_name"])
    if jobs:
        out += ["", "## Scheduled jobs", "", "Defined in `system/jobs.md`, run through `system/tools/job-run.sh`.", ""]
        for r in jobs:
            found = re.findall(r"([\w.-]+\.(?:sh|py))", r.get("command", ""))  # LAST script is the job
            runs = f" \u00b7 runs `{found[-1]}`" if found else ""
            out.append(f"- `{r['schedule_name']}` · {_every(r['interval_seconds'])} · enabled: {r['enabled']}{runs}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if toolbox.md is stale")
    ap.add_argument("--stdout", action="store_true")
    a = ap.parse_args(argv)
    text = generate()
    if a.stdout:
        sys.stdout.write(text)
        return 0
    if a.check:
        try:
            with open(OUT, encoding="utf-8") as fh:
                cur = fh.read()
        except FileNotFoundError:
            cur = None
        if cur != text:
            print("toolbox.md is STALE (or missing). Run: python3 system/register/toolbox.py", file=sys.stderr)
            return 1
        print("toolbox.md is current.")
        return 0
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
