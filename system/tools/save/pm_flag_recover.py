#!/usr/bin/env python3
"""
pm_flag_recover.py — recover a dropped project-manager flag from the durable arm-events logbook.

WHY: the PM flag (~/.claude/run/pm/pm-sess-<id>.flag) has a TTL (36h) and self-deletes on `status`
past expiry (system/hooks/pm_flag.sh). On a long/multi-day session it can vanish mid-session, after
which `/save` sees `none` and would SILENTLY skip the brief sync (Step 7d).

SOURCE OF TRUTH = the LOGBOOK, not the chat transcript. Every real `pm_flag.sh arm`/`clear` appends a
TSV line to ~/.claude/run/pm/arm-events.log:
    <ts>\t<arm|clear>\t<doc_path>\t<slug>\t<desk>\t<session>
Only genuinely-EXECUTED arms ever land there — so example/test/documentation commands in a transcript
can never trip a false recovery (the bug the old transcript-scraping version had), and a path with
spaces survives (TSV, one field per column). We recover the LAST event for the CURRENT session only.

Called by skills/save/SKILL.md Step 0.4 when `pm_flag.sh status` returns `none`.

Output (stdout, one line):
  NONE                                 — no arm/clear event for this session → nothing to recover
  CLEAR                                — last event was an intentional `clear` → respect the stop
  ARM<TAB>doc_path<TAB>slug<TAB>desk   — flag dropped after an arm → recover + confirm-before-sync

Usage:
  python3 pm_flag_recover.py [logbook_path] [session_id]   # both optional; default to the live log + $CLAUDE_CODE_SESSION_ID
"""
import os, sys

LOG = os.path.expanduser("~/.claude/run/pm/arm-events.log")
path = sys.argv[1] if len(sys.argv) > 1 else LOG
sess = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("CLAUDE_CODE_SESSION_ID", "")

last = None  # (event, doc, slug, desk)
try:
    with open(path, errors="ignore") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            _ts, event, doc, slug, desk, session = parts[:6]
            # Recover only THIS session's events — never bleed in another window's project.
            if sess and session != sess:
                continue
            # Only the two known verbs are recoverable. Anything else (a future verb, a
            # corrupted line, a refusal breadcrumb that ever lands here by mistake) is
            # IGNORED rather than falling through the `!= "clear"` branch below and being
            # reported as a recoverable ARM. 2026-08-06: pm_flag.sh gained refusal logging
            # for the immutable-project lock; those go to arm-denied.log precisely so this
            # file never sees them, and this check is the second line of that defence.
            if event not in ("arm", "clear"):
                continue
            last = (event, doc, slug, desk)
except FileNotFoundError:
    print("NONE"); sys.exit(0)

if last is None:
    print("NONE")
elif last[0] == "clear":
    print("CLEAR")
else:
    print(f"ARM\t{last[1]}\t{last[2]}\t{last[3]}")
