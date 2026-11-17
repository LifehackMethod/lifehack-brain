"""Guard: nothing but db.py opens the database. Fails if any .py under shared/grand_central (excluding db.py,
tests/, archive/, migrations/) calls sqlite3.connect (any alias) or does `from sqlite3 import connect`.
Everything else goes through store.py (or db.connect for the migration/backup tooling)."""
import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"tests", "archive", "migrations", "__pycache__", "venv", ".venv"}
SKIP_FILES = {"db.py"}


# Legitimate non-rig.db connect sites. Keyed by (relative path, substring of that exact connect line, reason).
# NOT a file exclusion: any other connect line in these files is still flagged. A stale entry fails the test.
ALLOWLIST = [
    ("backup.py", "sqlite3.connect(str(dst))",
     "destination of the sqlite backup API (a new backup file, not rig.db)"),
    ("backup.py", 'sqlite3.connect("file:%s?mode=ro&immutable=1"',
     "finished backup FILES opened read-only+immutable so verify never creates -wal/-shm beside them"),
    ("migrate.py", 'sqlite3.connect(":memory:"',
     "in-memory database used to build/compare the baseline schema"),
    ("batch_reader.py", "sqlite3.connect(path, timeout=30)",
     "Sentinel's separate dedupe-cache database (not rig.db; own timeout, no WAL)"),
    ("check_personal_values.py", 'sqlite3.connect("file:%s?mode=ro"',
     "the personal-values lock reads the owner's database READ-ONLY (mode=ro) to learn the names that live only there"),
    ("test_check_personal_values.py", "sqlite3.connect(path)",
     "builds a small synthetic database in a temp folder to test the lock's database layer"),
    ("reader/readerd.py", "sqlite3.connect(path)",
     "the MAILROOM's own small register (ids, status, verdict; no text) in the mailroom account's home: "
     "plan B1 'its own small record of what it fetched and scanned'. A separate file the mailroom owns, "
     "not rig.db; the mailroom cannot reach the rig's db.py or the front room, by design"),
]


def scan(root=ROOT):
    """Return [(rel_str, message, line_text)]; line_text is '' for non-line findings."""
    out = []
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root)
        if set(rel.parts[:-1]) & SKIP_DIRS or (len(rel.parts) == 1 and rel.name in SKIP_FILES):
            continue
        try:
            tree = ast.parse(p.read_text(), filename=str(p))
        except SyntaxError as e:
            out.append((str(rel), "%s: unparseable (%s)" % (rel, e), ""))
            continue
        lines = p.read_text().splitlines()
        aliases = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                aliases |= {(a.asname or a.name) for a in n.names if a.name == "sqlite3"}
            elif isinstance(n, ast.ImportFrom) and n.module == "sqlite3":
                for a in n.names:
                    if a.name == "connect":
                        out.append((str(rel), "%s:%d from sqlite3 import connect" % (rel, n.lineno), ""))
        for n in ast.walk(tree):
            f = getattr(n, "func", None)
            if (isinstance(n, ast.Call) and isinstance(f, ast.Attribute) and f.attr == "connect"
                    and isinstance(f.value, ast.Name) and f.value.id in aliases):
                out.append((str(rel), "%s:%d %s.connect()" % (rel, n.lineno, f.value.id), lines[n.lineno - 1]))
    return out


def offenders(root=ROOT, allowlist=()):
    """Flagged sites not covered by the allowlist, plus a message per allowlist entry that matched nothing."""
    used = set()
    bad = []
    for rel, msg, text in scan(root):
        hit = [i for i, (arel, sub, _why) in enumerate(allowlist) if arel == rel and text and sub in text]
        if hit:
            used.update(hit)
        else:
            bad.append(msg)
    for i, (arel, sub, _why) in enumerate(allowlist):
        if i not in used:
            bad.append("stale allowlist entry (matches nothing): %s %r" % (arel, sub))
    return bad


class TestFrontDoor(unittest.TestCase):
    def test_no_direct_sqlite_connect(self):
        bad = offenders(ROOT, ALLOWLIST)
        self.assertEqual(bad, [], "direct sqlite3 connections (use store.py / db.connect):\n  " + "\n  ".join(bad))

    def test_detector_catches_a_plant(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "x.py").write_text("import sqlite3 as s\ns.connect('a')\n")
            (Path(t) / "y.py").write_text("from sqlite3 import connect\n")
            (Path(t) / "ok.py").write_text("import sqlite3\nsqlite3.Row\n")
            got = offenders(Path(t))
        self.assertEqual(len(got), 2, got)

    def test_allowlist_is_exact_and_stale_fails(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "a.py").write_text("import sqlite3\nsqlite3.connect('ok')\nsqlite3.connect('new')\n")
            got = offenders(Path(t), [("a.py", "connect('ok')", "r")])
            self.assertEqual(len(got), 1, got)  # the new connect line is still flagged
            self.assertIn("a.py:3", got[0])
            got = offenders(Path(t), [("a.py", "connect('gone')", "r")])
            self.assertTrue(any("stale allowlist" in g for g in got), got)


if __name__ == "__main__":
    unittest.main()
