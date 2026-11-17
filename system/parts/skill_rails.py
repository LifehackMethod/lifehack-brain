#!/usr/bin/env python3
# not-wired-yet: wired by the rebuilt skill's stage checks (4P.5)
"""skill_rails — the RAILS: a rebuilt planning skill's files must stay off the engine's forbidden surfaces. [Parts Library · Tier A]

WHEN: before a skill that talks to the Grand Central engine is merged (plan 4P.6), and any time
      its files change.
WHAT: scans a skill FOLDER (every non-binary file) and FAILS on written paths that cross the rails:
      (a) direct database access -- the sqlite3 module or CLI, any `*.db` path, SQL keywords in code
          contexts, and the engine's DB path helpers (`rig.db`, `db_file`, `data_root`, `gc_data_root`);
      (b) a diary write by the skill -- a write/append/redirect aimed at a `diary/` path (the daily
          diary job is the one writer);
      (c) an email draft or send call -- gmail drafts/send/compose verbs, `+send`, `drafts.create`,
          `messages.send`;
      (d) a `gc` write command other than the four the skill may use (`answer`, `onboarding answer`,
          `decide`, `backup`).
WHY: nothing in code holds the skill off the database and raw SQL or off Gmail (ledger sweep "Missing" 1,
      plan 4P.6). One writer per diary, email text never reaches a window with tools, and confirmations
      reach the engine only through the door.

THE KNOWN BOUND, STATED HONESTLY (not hidden): this scan DETECTS written paths in files. It CANNOT stop
a query or a path BUILT AT RUN TIME from pieces the files never spell out (a joined string, a variable
holding a filename). That stays on the debt list; the runtime guarantee comes from the engine itself
(the door, the one-writer diary job), not from this scan.

USAGE
  skill_rails.py <skill-folder>
  skill_rails.py --selftest

EXIT CODES (the part contract)
  0 CLEAN -- no rail crossed
  1 REFUSED -- at least one rail crossed; findings printed as `file:line:rule:evidence`
  2 CANNOT EVALUATE -- missing/unreadable folder or file, or an unexpected internal error.
        Fail-closed: an un-evaluable check NEVER reports clean.
"""

import argparse
import os
import re
import sys

CLEAN, REFUSED, CANNOT_EVALUATE = 0, 1, 2

# The four `gc` commands a rebuilt skill may write through (plan 4P.1: the skill uses only
# `answer`, `onboarding answer` for the sheet, and `backup`; `decide` is the read-side decision verb
# the door accepts). Everything else a `gc <verb>` line names is a rail.
GC_WRITE_ALLOWED = {"answer", "onboarding", "decide", "backup"}
# `gc` read commands the skill legitimately calls with --json (plan: Planning-Diary read set).
GC_READS = {"status", "person", "org", "upcoming", "due", "week", "urgent", "help", "version"}

RULES = [
    # (a) direct database access -- written paths only (see the header bound).
    ("db-sqlite", re.compile(r"\bsqlite3\b", re.I)),
    ("db-db-path", re.compile(r"(?<![\w.])[\w-]*\.db\b", re.I)),
    ("db-sql-select", re.compile(r"\bSELECT\s+\S[^;\n]*\s+FROM\b", re.I)),
    ("db-sql-insert", re.compile(r"\bINSERT\s+INTO\b", re.I)),
    ("db-sql-update", re.compile(r"\bUPDATE\s+\w+\s+SET\b", re.I)),
    ("db-sql-delete", re.compile(r"\bDELETE\s+FROM\b", re.I)),
    ("db-sql-create", re.compile(r"\bCREATE\s+TABLE\b", re.I)),
    ("db-engine-helper", re.compile(r"\b(?:db_file|data_root|gc_data_root)\s*\(", re.I)),
    # (b) a diary WRITE: a diary path AND a write/append/redirect on the same line.
    ("diary-write", re.compile(r"diary/", re.I)),
]
DIARY_WRITE_VERB = re.compile(
    r"\bopen\s*\(|\bwrite_text\b|\bwrite\b|>>|\bappend\b|\btee\b|\bshutil\.(?:copy|move)\b", re.I)

# (c) email draft or send.
EMAIL_RULES = [
    ("email-draft", re.compile(r"drafts?\.create|drafts?\s*\(\s*\)\s*\.create|users\.drafts|create_draft", re.I)),
    ("email-send", re.compile(r"messages?\.send|gmail.*\bsend|send_(?:email|mail|message|draft)|\+send\b|gmail_send|compose", re.I)),
]

# (d) `gc <verb>`: allowed writes, known reads; anything else is a rail.
GC_CMD = re.compile(r"(?<![\w.-])gc\s+([a-z_-]+)(?:\s+([a-z_-]+))?", re.I)
# the same call in list form: ["gc", "approve", ...]
GC_CMD_LIST = re.compile(r"[\"']gc[\"']\s*,\s*[\"']([a-z_-]+)[\"'](?:\s*,\s*[\"']([a-z_-]+)[\"'])?", re.I)


def _iter_files(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in {".git", "__pycache__"})
        for fn in sorted(fns):
            yield os.path.join(dp, fn)


def check_file(path):
    """-> list of (line_no, rule_id, evidence). Raises OSError on an unreadable file."""
    hits = []
    with open(path, "rb") as f:
        data = f.read()
    if b"\0" in data[:4096]:
        return hits  # binary
    for i, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
        for rid, rx in RULES:
            if rx.search(line):
                if rid == "diary-write" and not DIARY_WRITE_VERB.search(line):
                    continue  # a diary READ is fine; only a write is the rail
                hits.append((i, rid, line.strip()[:160]))
        for rid, rx in EMAIL_RULES:
            if rx.search(line):
                hits.append((i, rid, line.strip()[:160]))
        m = GC_CMD.search(line) or GC_CMD_LIST.search(line)
        if m:
            verb = (m.group(1) or "").lower()
            second = (m.group(2) or "").lower()
            if verb == "onboarding":
                ok = second == "answer"
            else:
                ok = verb in GC_WRITE_ALLOWED or verb in GC_READS
            if not ok:
                hits.append((i, "gc-write", line.strip()[:160]))
    return hits


def scan_folder(root):
    """-> list of (relpath, line_no, rule_id, evidence). Raises OSError."""
    if not os.path.isdir(root):
        raise OSError("not a folder: %s" % root)
    out = []
    for path in _iter_files(root):
        out += [(os.path.relpath(path, root), i, rid, ev) for i, rid, ev in check_file(path)]
    return out


# ---------------------------------------------------------------- self-test

_BAD_LINES = {
    "db-sqlite": 'import sqlite3; con = sqlite3.connect("rig.db")',
    "db-db-path": 'db = "/some/where/rig.db"',
    "db-sql-select": 'q = "SELECT name FROM kg_things WHERE kind=\'person\'"',
    "db-sql-insert": 'sql = "INSERT INTO kg_things (name) VALUES (?)"',
    "db-sql-update": 'sql = "UPDATE kg_things SET name = ?"',
    "db-sql-delete": 'sql = "DELETE FROM kg_things WHERE key = ?"',
    "db-sql-create": 'sql = "CREATE TABLE scratch (id integer)"',
    "db-engine-helper": 'root = data_root()',
    "diary-write": 'with open("diary/2026/11/17.md", "a") as f: f.write(entry)',
    "email-draft": 'svc.users().drafts().create(userId="me", body={...}).execute()',
    "email-send": 'gmail_send(to=addr, subject=sub, body=text)',
    "gc-write": 'subprocess.run(["gc", "approve", snap_id])',
}
# a diary READ (no write verb) and a clean `gc answer` line must NOT fire.
_GOOD_LINES = [
    'entries = gc("week", "--json")  # read only',
    'listing = sorted(os.listdir("diary/2026/11"))  # reading the diary is allowed',
    'subprocess.run(["gc", "answer", aid, words])',
    'subprocess.run(["gc", "onboarding", "answer", row, val])',
    'subprocess.run(["gc", "backup", "--out", path])',
    'subprocess.run(["gc", "decide", "--json"])',
    'print("week", upcoming, due, urgent)',
]


def selftest():
    ok = True

    def report(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f" [{'PASS' if passed else 'FAIL'}] {label}{(' -- ' + detail) if detail else ''}")

    print("skill_rails --selftest")
    for rid, line in _BAD_LINES.items():
        got = {r for _, r, _ in check_lines_helper(line)}
        report(f"catches {rid}", rid in got, f"got {sorted(got)}")
    for line in _GOOD_LINES:
        got = check_lines_helper(line)
        report(f"no false positive on {line[:52]!r}", got == [], f"{got}")

    # end-to-end: a planted bad file fails, a clean file passes, a missing folder is exit 2
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        bad = os.path.join(td, "bad-skill")
        os.makedirs(bad)
        with open(os.path.join(bad, "step.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(_BAD_LINES.values()) + "\n")
        rc = _cli(bad)
        report("folder with every planted rail -> exit 1", rc == REFUSED, f"got {rc}")

        good = os.path.join(td, "good-skill")
        os.makedirs(good)
        with open(os.path.join(good, "step.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(_GOOD_LINES) + "\n")
        rc = _cli(good)
        report("clean folder -> exit 0", rc == CLEAN, f"got {rc}")

        rc = _cli(os.path.join(td, "missing"))
        report("missing folder -> exit 2 (fail-closed)", rc == CANNOT_EVALUATE, f"got {rc}")

    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def check_lines_helper(line):
    """Check one line through the same machinery as a file (test seam)."""
    import tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        p = os.path.join(td, "l.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(line + "\n")
        return check_file(p)


def _cli(folder):
    import subprocess
    return subprocess.run([sys.executable, os.path.abspath(__file__), folder],
                          capture_output=True, text=True).returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description="skill_rails -- the rails a rebuilt skill's files must hold")
    ap.add_argument("folder", nargs="?", help="the skill folder to scan")
    ap.add_argument("--selftest", action="store_true", help="run the two-sided self-test")
    a = ap.parse_args(argv)

    if a.selftest:
        sys.exit(selftest())
    if not a.folder:
        print("CANNOT EVALUATE: a skill folder is required (or --selftest)", file=sys.stderr)
        sys.exit(CANNOT_EVALUATE)
    try:
        hits = scan_folder(a.folder)
    except OSError as e:
        print("CANNOT EVALUATE: %s" % e, file=sys.stderr)
        sys.exit(CANNOT_EVALUATE)
    except Exception as e:  # fail closed
        print("CANNOT EVALUATE: unexpected %s" % type(e).__name__, file=sys.stderr)
        sys.exit(CANNOT_EVALUATE)

    for rel, i, rid, ev in hits:
        print("%s:%d:%s:%s" % (rel, i, rid, ev))
    print("skill rails: %d finding(s) in %s" % (len(hits), a.folder))
    sys.exit(REFUSED if hits else CLEAN)


if __name__ == "__main__":
    main()
