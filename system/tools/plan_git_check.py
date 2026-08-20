#!/usr/bin/env python3
"""plan_git_check — does an OPEN plan box lie about being open?

WHY: 2026-08-08, W11.2/W11.3/W11.4 sat `- [ ] **id**` in the live plan while
commit cf911a6 and others had shipped them hours earlier. A blind audit read
the stale plan and recommended DELETING all three as never-built — the plan
lied to the auditor hired to check it. This catches that lie first.

WHAT: for each `~/.claude/plans/*.plan.md` (or one via --plan), find every
`- [ ] **<id>**` line, then check the git log (default 14 days) for a commit
SUBJECT containing that id — evidence the task shipped even though unticked.

⛔ REPORT ONLY, no write path exists here — a commit tag is evidence a task
shipped, NOT proof its Verify passed. A human adjudicates.

⛔ Anchored to the checkbox LINE, not the whole plan. An id in prose
("superseded by W11.2") is discussion, not an open task — never reported.

CLOSED VERDICT SET (house style, see board_check.py):
    PLAN-GIT-CLEAN   rc 0  every open box's id is absent from the git window
    STALE-BOX <n>    rc 2  n open box(es) whose id appears in a commit subject
    CANNOT-READ <why> rc 4 THE NO-OUTCOME MEMBER — git failure, unreadable or
                           missing plan, or nothing to scan. NEVER clean.
"""
# ⚖ SHIPPED WITH NO CALLER AT ALL (D7, 2026-08-11). A repo-wide grep finds nothing that
# invokes this — not a skill, not a hook, not another tool. It ships because the ruling is
# migrate-as-is; it is recorded here rather than discovered later. If nothing claims it by
# the end of the migration, that is the finding.

import argparse
import glob
import os
import re
import subprocess
import sys

# ⛔ IMPORT the no-outcome member, never re-type it (2026-08-08). `verdicts.py` was built THIS DAY
# because this convention lived as prose in an SOP and had been hand-copied into SEVEN tools, one of
# which (`pad_archive.py`) got it wrong and could not tell "cannot read your brief" from "bad
# heading" — on the tool guarding an APPEND-ONLY write.
# ⭐ THIS FILE RE-TYPED IT ANYWAY, HOURS AFTER THE FIX SHIPPED — the eighth instance, caught by the
# lead re-running the helper's work rather than reading its report. That is the whole argument for
# the shared module: the rule is only obeyed when it cannot be forgotten.
# ⛔ This added `system/tools/` — the directory THIS file sits in — while `verdicts.py`
# lives at `shared/emit/`. Every invocation, `--help` included, died on
# ModuleNotFoundError. The shared module only stops the rule being forgotten if the
# path to it is right.
_REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "shared", "emit"))
from verdicts import CANNOT_READ

# Id shape this repo writes: W11.3, T27.1, F3.1, 15.2, T8.1b (0-2 leading caps,
# digits, dot, digits, optional trailing letter). \b makes a bracket group like
# [W11.5/W11.6] split for free on "/", ",", whitespace — no separate split step.
ID = r'[A-Za-z]{0,2}\d{1,3}\.\d{1,2}[a-z]?'
COMMIT_ID_RE = re.compile(r'\b' + ID + r'\b')
CHECKBOX_RE = re.compile(r'^- \[ \] \*\*(' + ID + r')\*\*')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def cannot_read(why):
    print(f"CANNOT-READ\n  {why}")
    sys.exit(CANNOT_READ)

def git_commits(days):
    try:
        out = subprocess.run(
            ["git", "-C", REPO_ROOT, "log", f"--since={days} days ago", "--pretty=format:%h\x1f%s"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        cannot_read(f"git log failed to run ({e.__class__.__name__}: {e})")
    if out.returncode != 0:
        cannot_read(f"git log exited {out.returncode}: {out.stderr.strip()}")
    commits = []
    for line in out.stdout.splitlines():
        if "\x1f" not in line:
            continue
        h, subj = line.split("\x1f", 1)
        commits.append((h, subj))
    return commits

def open_boxes(path):
    if not os.path.exists(path):
        cannot_read(f"plan does not exist: {path}")
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
    except Exception as e:
        cannot_read(f"plan unreadable ({e.__class__.__name__}: {e}): {path}")
    boxes = []
    for i, l in enumerate(lines):
        m = CHECKBOX_RE.match(l)
        if m:
            boxes.append((i + 1, m.group(1), l.strip()))
    return boxes

def main():
    ap = argparse.ArgumentParser(description="Do open plan boxes contradict git history?")
    ap.add_argument("--plan", help="one plan file; default scans ~/.claude/plans/*.plan.md")
    ap.add_argument("--days", type=int, default=14, help="git log window (default 14)")
    a = ap.parse_args()

    if a.plan:
        plans = [os.path.expanduser(a.plan)]
    else:
        # CLAUDE_CONFIG_DIR moves the whole harness folder. Same pattern as agent_output.py:59-60.
        _cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
        _pattern = os.path.join(_cfg, "plans", "*.plan.md")
        plans = sorted(glob.glob(_pattern))
        if not plans:
            cannot_read("no plan files matched %s" % _pattern)

    commits = git_commits(a.days)
    ids_to_commits = {}
    for h, subj in commits:
        for cid in COMMIT_ID_RE.findall(subj):
            ids_to_commits.setdefault(cid, []).append((h, subj))

    stale = []
    for path in plans:
        for line_no, tid, text in open_boxes(path):
            hits = ids_to_commits.get(tid)
            if hits:
                stale.append((path, line_no, tid, text, hits[0]))

    print(f"  plans scanned: {len(plans)}")
    print(f"  commits in window ({a.days}d): {len(commits)}")

    if not stale:
        print("PLAN-GIT-CLEAN")
        sys.exit(0)

    print(f"STALE-BOX {len(stale)}")
    for path, line_no, tid, text, (h, subj) in stale:
        print(f"  {path}:{line_no} open `{tid}`")
        print(f"    {text}")
        print(f"    shipped in {h} — {subj}")
    sys.exit(2)

if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()
