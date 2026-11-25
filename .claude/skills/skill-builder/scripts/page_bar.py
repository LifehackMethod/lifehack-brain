#!/usr/bin/env python3
"""page_bar.py — Caller: step prompts 3 (the walk-through) and 5 (the findings, six at a time): wherever the
house style's Screen A shows the PAGE BAR, `Walk-through · page 2 of 4   ✅ ▶ ⬜ ⬜`, at the top of the screen and
again under the "# QUESTIONS" heading.
Sub-step: draws the page bar BY CODE from the skill's OWN page file, never by the AI (SB-12). A page gets its ✅
only when the person's played-back yes is saved here; the bar is read straight from that file.

THE PAGE FILE: `<workdir>/pages.json`, in the packet folder. It is this script's file alone. The runner's
`record.jsonl` is never read or written here (only the runner writes that), and a page never moves the run:
this script does not call `advance` or `back`, and the status line stays the step counter.

Usage:
    page_bar.py init    --workdir D --section S --label "Walk-through" --total N [--reset]
    page_bar.py current --workdir D --section S --page N        (the page now on screen)
    page_bar.py done    --workdir D --section S --page N --said "<the person's yes, in their words>"
    page_bar.py bar     --workdir D --section S                 (prints the bar line, nothing else)

The bar (cells in page order; ✅ done · ▶ the current page, not yet done · ⬜ not yet):
    <label> · page <current> of <total>   <cells>               e.g.  Walk-through · page 2 of 4   ✅ ▶ ⬜ ⬜
    the current page is already done  →   <label> · page 1 of 4 · done   ✅ ⬜ ⬜ ⬜
    every page done                   →   <label> · all 4 pages done   ✅ ✅ ✅ ✅

Exit codes (distinct, documented):
    0 PASS — the command was done; `bar` printed the line.
    1 FAIL — refused, loudly: page out of range, `done` with no words said, `init` on a section that already
             exists (add --reset to start it over), unknown section.
    2 COULD-NOT-CHECK — bad args, unreadable or corrupt page file, or the timeout fired.

Writes ONLY `<workdir>/pages.json` (a temp file beside it, then a rename); the `bar` command writes nothing.
"""

import argparse
import json
import os
import signal
import sys
import tempfile
import time

DEFAULT_TIMEOUT = 20  # seconds
FILE_NAME = "pages.json"
DONE, HERE, TODO = "✅", "▶", "⬜"


def die(code, why, fix=None):
    print("page_bar.py: %s" % why, file=sys.stderr)
    if fix:
        print("  to fix: %s" % fix, file=sys.stderr)
    sys.exit(code)


def on_timeout(signum, frame):
    die(2, "timed out", "run it again; nothing was changed")


def load(workdir):
    path = os.path.join(workdir, FILE_NAME)
    if not os.path.exists(path):
        return path, {"sections": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        die(2, "cannot read %s: %s" % (path, e), "do not hand-edit it; ask the person before starting the pages over")
    if not isinstance(data, dict) or not isinstance(data.get("sections"), dict):
        die(2, "%s is not a page file (no `sections`)" % path, "ask the person before starting the pages over")
    return path, data


def save(path, data):
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".pages-", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, path)
    except OSError as e:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        die(2, "cannot write %s: %s" % (path, e))


def section_or_die(data, name):
    sec = data["sections"].get(name)
    if not isinstance(sec, dict) or not isinstance(sec.get("total"), int) or sec["total"] < 1:
        die(1, "no section '%s' in the page file" % name,
            "run `page_bar.py init --section %s --label ... --total N` first" % name)
    return sec


def page_or_die(sec, page):
    if page < 1 or page > sec["total"]:
        die(1, "page %d is outside 1..%d" % (page, sec["total"]), "pages run from 1 to %d" % sec["total"])


def render(sec):
    total = sec["total"]
    done = set(int(k) for k in sec.get("done", {}))
    label = sec.get("label", "Pages")
    if len(done & set(range(1, total + 1))) == total:
        return "%s · all %d pages done   %s" % (label, total, " ".join([DONE] * total))
    cur = int(sec.get("current", 1))
    cells = []
    for p in range(1, total + 1):
        if p in done:
            cells.append(DONE)
        elif p == cur:
            cells.append(HERE)
        else:
            cells.append(TODO)
    tail = " · done" if cur in done else ""
    return "%s · page %d of %d%s   %s" % (label, cur, total, tail, " ".join(cells))


def main():
    ap = argparse.ArgumentParser(description="Draw the skill builder's page bar from its own page file.")
    ap.add_argument("cmd", choices=["init", "current", "done", "bar"])
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--section", required=True)
    ap.add_argument("--label")
    ap.add_argument("--total", type=int)
    ap.add_argument("--page", type=int)
    ap.add_argument("--said")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    try:
        a = ap.parse_args()
    except SystemExit as e:
        sys.exit(2 if e.code not in (0, None) else 0)
    signal.signal(signal.SIGALRM, on_timeout)
    signal.alarm(max(1, a.timeout))
    if not os.path.isdir(a.workdir):
        die(2, "workdir is not a folder: %s" % a.workdir)

    path, data = load(a.workdir)
    if a.cmd == "init":
        if not a.label or a.total is None or a.total < 1:
            die(2, "init needs --label and --total (1 or more)")
        if a.section in data["sections"] and not a.reset:
            die(1, "section '%s' already exists" % a.section,
                "to start it over (the person changed the pages), add --reset")
        data["sections"][a.section] = {"label": a.label, "total": a.total, "current": 1, "done": {}}
        save(path, data)
        print(render(data["sections"][a.section]))
    elif a.cmd == "current":
        sec = section_or_die(data, a.section)
        if a.page is None:
            die(2, "current needs --page")
        page_or_die(sec, a.page)
        sec["current"] = a.page
        save(path, data)
        print(render(sec))
    elif a.cmd == "done":
        sec = section_or_die(data, a.section)
        if a.page is None:
            die(2, "done needs --page and --said")
        page_or_die(sec, a.page)
        if not a.said or not a.said.strip():
            die(1, "no words said: a page gets its ✅ only on the person's played-back yes",
                "pass --said with their yes, in their own words")
        sec.setdefault("done", {})[str(a.page)] = {"said": a.said.strip(), "at": int(time.time())}
        save(path, data)
        print(render(sec))
    else:  # bar
        sec = section_or_die(data, a.section)
        print(render(sec))
    sys.exit(0)


if __name__ == "__main__":
    main()
