import atexit as _ax, os as _o, shutil as _sh, tempfile as _t  # isolation: no test writes outside tmp, standalone or not
if "gc-test-data-" not in _o.environ.get("GC_DATA_ROOT", ""):
    _o.environ["GC_DATA_ROOT"] = _t.mkdtemp(prefix="gc-test-data-"); _ax.register(_sh.rmtree, _o.environ["GC_DATA_ROOT"], True)
    _o.environ["AGE_FRONT_ROOM"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "front-room")
    _o.environ["GC_STATE_ROOT"] = _o.path.join(_o.environ["GC_DATA_ROOT"], "state")
_o.environ.setdefault("GC_SETUP_DIR", _o.path.join(_o.path.dirname(_o.path.abspath(__file__)), "fixtures", "setup"))
import io
import contextlib
import os, re, shutil, sqlite3, sys, tempfile, time, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import gc_settings  # noqa: E402
import db, migrate
HEAD = migrate.list_migrations()[-1][0]


def _real_setup_dir():
    """The person's real setup folder, found the way production finds it, IGNORING the test's GC_SETUP_DIR (the synthetic
    fixture): personal code root -> PERSONAL_SUBDIR. None when this machine has none."""
    root = gc_settings.personal_code_root()
    cand = os.path.join(root, gc_settings.PERSONAL_SUBDIR) if root else ""
    return cand if cand and os.path.isdir(cand) else None


def _real_live_db():
    """The real database: the data root the person's own setup gives (env GC_DATA_ROOT -> that setup's gc.json data_root
    -> the generic default), then rig.db. The test redirections are lifted only for this lookup, and restored. Read-only."""
    setup = _real_setup_dir()
    if not setup:
        return None
    saved = {k: os.environ.get(k) for k in ("GC_SETUP_DIR", "GC_DATA_ROOT")}
    try:
        os.environ["GC_SETUP_DIR"] = setup
        if "gc-test-data-" in (saved["GC_DATA_ROOT"] or "") or not saved["GC_DATA_ROOT"]:
            os.environ.pop("GC_DATA_ROOT", None)
        return gc_settings.db_path()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _real_owner_migrations_dir():
    setup = _real_setup_dir()
    return os.path.join(setup, "migrations") if setup else None


LIVE = _real_live_db()
OWNER_DIR = _real_owner_migrations_dir()


def copy_live(dst):
    """Read-only copy of the real database (the same as `sqlite3 rig.db ".backup dst"`). Never writes the original."""
    src = sqlite3.connect("file:%s?mode=ro" % LIVE, uri=True)
    d = sqlite3.connect(dst)
    src.backup(d)
    d.close(); src.close()


def _strip(sql):
    return " ".join(re.sub(r"--[^\n]*", "", sql or "").split())


def _schema(c):
    """Schema with comments stripped (a scrub changed comments only), minus the owner record table."""
    d = {}
    for t, n, sql in c.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' AND name <> 'owner_migrations'"):
        d[(t, n)] = _strip(sql)
        if t in ("table", "view"):
            d[("cols", n)] = repr([tuple(r[1:]) for r in c.execute("PRAGMA table_xinfo('%s')" % n)])
    return d


# tables whose seed rows carry an id or a time of their own: compared on content, current facts only
_CONTENT = {"thing_keys": "SELECT key,kind,made_from FROM thing_keys",
            "kg_things": "SELECT kind,key,name,legacy_ref,created_by FROM kg_things",
            "kg_facts": "SELECT t.key,f.fact_key,f.value,f.who,f.certainty,f.source_kind,f.source_ref FROM kg_facts f "
                        "JOIN kg_things t ON t.id=f.thing_id WHERE f.replaced_by IS NULL"}


def compare_to_live(fresh, live):
    """Differences between a fresh build and the live copy: schema both ways, then every seeded table of the fresh build
    must be present in the live copy (live may hold more, never less)."""
    out = []
    a, b = _schema(fresh), _schema(live)
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            out.append("schema differs: %s %s" % k)
    tables = [r[0] for r in fresh.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                                          "AND name <> 'owner_migrations'")]
    for t in tables:
        if not fresh.execute('SELECT count(*) FROM "%s"' % t).fetchone()[0]:
            continue
        q = _CONTENT.get(t, 'SELECT * FROM "%s"' % t)
        missing = set(fresh.execute(q).fetchall()) - set(live.execute(q).fetchall())
        if missing:
            out.append("seed rows of %s not in the live copy: %s" % (t, sorted(missing)[:3]))
    return out


# the live copy is taken at import, before anything else here can move the data root
_COPY_DIR = tempfile.mkdtemp(prefix="gc-live-copy-")
import atexit as _ax2, shutil as _sh2  # noqa: E402
_ax2.register(_sh2.rmtree, _COPY_DIR, True)
LIVE_COPY = os.path.join(_COPY_DIR, "live-copy.db")
if LIVE and os.path.exists(LIVE):
    copy_live(LIVE_COPY)


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.tmp.name, "rig.db")
        if os.path.exists(LIVE_COPY):
            shutil.copy(LIVE_COPY, self.p)
        else:   # no live database on this machine: a fresh head build stands in for it
            c = migrate.fresh_build(HEAD); d = sqlite3.connect(self.p); c.backup(d); d.close()
    def tearDown(self):
        self.tmp.cleanup()

    def set_version(self, v):
        c = sqlite3.connect(self.p); c.execute("PRAGMA user_version=%d" % v); c.commit(); c.close()

    def _fresh_with_owner(self):
        return migrate.fresh_build(10**6, owner_migs=migrate.list_owner_migrations(OWNER_DIR))

    @unittest.skipUnless(os.path.exists(LIVE_COPY) and OWNER_DIR and os.path.isdir(OWNER_DIR),
                         "needs the owner's real rig.db and his own owner migrations folder; neither is on this machine")
    def test_fresh_equals_live(self):
        # a fresh build (plugin series, then the owner's own series from his setup) equals a copy of the live database
        # taken before anything is migrated: same schema (comments aside), every seed row present
        fresh = self._fresh_with_owner()
        live = sqlite3.connect(self.p)
        self.assertEqual(db.current_version(fresh), HEAD)
        self.assertGreater(len(_schema(fresh)), 100)
        self.assertIn(("table", "events"), _schema(fresh))
        self.assertEqual(compare_to_live(fresh, live), [])

    @unittest.skipUnless(os.path.exists(LIVE_COPY) and OWNER_DIR and os.path.isdir(OWNER_DIR), "needs the owner's real rig.db")
    def test_fresh_equals_live_sees_a_planted_difference(self):
        # the comparison must fail on a planted difference, in the schema and in a seed row
        fresh = self._fresh_with_owner()
        live = sqlite3.connect(self.p)
        live.execute("ALTER TABLE events ADD COLUMN planted TEXT")
        self.assertTrue(any("events" in l for l in compare_to_live(fresh, live)))
        live.close(); shutil.copy(LIVE_COPY, self.p)
        live = sqlite3.connect(self.p)
        live.execute("DELETE FROM kg_vocab WHERE rowid=(SELECT min(rowid) FROM kg_vocab)")
        self.assertTrue(any("kg_vocab" in l for l in compare_to_live(fresh, live)))

    def test_fresh_build_reaches_head(self):
        self.assertEqual(db.current_version(migrate.fresh_build(HEAD)), HEAD)

    def test_already_at_head_is_noop(self):
        p = os.path.join(self.tmp.name, "head.db")
        c = migrate.fresh_build(HEAD); d = sqlite3.connect(p); c.backup(d); d.close()
        out = []
        self.assertEqual(migrate.run(p, apply=False, out=out.append), 0)
        self.assertTrue(any("up to date" in l for l in out))
        self.assertEqual(migrate.run(p, apply=True, backup_ok=self._bk(), out=out.append), 0)
        self.assertEqual(db.current_version(sqlite3.connect(p)), HEAD)

    def _bk(self):
        bk = os.path.join(self.tmp.name, "bk.db"); open(bk, "w", encoding="utf-8").close(); return bk

    def test_stamp_only(self):
        # an unstamped DB whose schema equals 001 (the live DB has since moved past 001): fresh 001 build, one row, version 0
        os.remove(self.p)
        c = migrate.fresh_build(1); d = sqlite3.connect(self.p); c.backup(d); d.close()
        d = sqlite3.connect(self.p); d.execute("insert into messages(id) values ('m1')"); d.commit(); d.close()
        self.set_version(0)
        before = sqlite3.connect(self.p).execute("select count(*) from messages").fetchone()
        bk = os.path.join(self.tmp.name, "bk.db"); open(bk, "w", encoding="utf-8").close()
        out = []
        self.assertEqual(migrate.run(self.p, apply=False, out=out.append), 0)
        self.assertEqual(db.current_version(sqlite3.connect(self.p)), 0)   # dry run changes nothing
        self.assertEqual(migrate.run(self.p, apply=True, backup_ok=bk, out=out.append), 0)
        c = sqlite3.connect(self.p)
        self.assertEqual(db.current_version(c), HEAD)   # stamped at 1, then the rest applied in order
        self.assertEqual(c.execute("select count(*) from messages").fetchone(), before)
        self.assertTrue(any("no DDL" in l for l in out))
        dos = [l for l in out if l.startswith("DO: apply")]
        self.assertEqual(dos, ["DO: apply %s" % os.path.basename(p) for n, p in migrate.list_migrations() if n > 1])

    def test_refuse_on_drift(self):
        self.set_version(0)
        c = sqlite3.connect(self.p); c.execute("ALTER TABLE events ADD COLUMN x TEXT"); c.commit(); c.close()
        bk = os.path.join(self.tmp.name, "bk.db"); open(bk, "w", encoding="utf-8").close()
        out = []
        self.assertEqual(migrate.run(self.p, apply=True, backup_ok=bk, out=out.append), 1)
        self.assertEqual(db.current_version(sqlite3.connect(self.p)), 0)
        self.assertTrue(any("events" in l for l in out))

    def test_backup_required(self):
        with self.assertRaises(SystemExit):
            migrate.check_backup(os.path.join(self.tmp.name, "nope"))
        old = os.path.join(self.tmp.name, "old"); open(old, "w", encoding="utf-8").close()
        t = time.time() - 700; os.utime(old, (t, t))
        with self.assertRaises(SystemExit):
            migrate.check_backup(old)

    def test_empty_db_builds(self):
        p = os.path.join(self.tmp.name, "new.db")
        bk = os.path.join(self.tmp.name, "bk"); open(bk, "w", encoding="utf-8").close()
        self.assertEqual(migrate.run(p, apply=True, backup_ok=bk, out=lambda s: None), 0)
        self.assertEqual(db.current_version(sqlite3.connect(p)), HEAD)

    def test_connect_pragmas(self):
        self.set_version(0)
        c = db.connect(self.p)
        self.assertEqual(c.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(c.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertEqual(c.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
        c.close()
        r = db.connect(self.p, readonly=True)
        self.assertEqual(r.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        with self.assertRaises(sqlite3.OperationalError):
            r.execute("create table z(a)")
        self.assertEqual(db.current_version(r), 0)

class TestTargetDb(unittest.TestCase):
    """2026-11-13 incident: AGE_RIG_DB was ignored and a scratch-aimed --apply hit the live rig.db."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.live = os.path.join(self.tmp.name, "live.db")
        self.scratch = os.path.join(self.tmp.name, "scratch.db")
        for p in (self.live, self.scratch):
            c = sqlite3.connect(p, isolation_level=None)
            migrate.apply_file(c, migrate.list_migrations()[0][1], 1)
            c.close()
        self.bak = os.path.join(self.tmp.name, "bak.db")
        open(self.bak, "w", encoding="utf-8").close()
        self._def, self._env = migrate.db.DEFAULT_PATH, os.environ.get("AGE_RIG_DB")
        migrate.db.DEFAULT_PATH = self.live  # stand-in for the live rig.db

    def tearDown(self):
        migrate.db.DEFAULT_PATH = self._def
        if self._env is None:
            os.environ.pop("AGE_RIG_DB", None)
        else:
            os.environ["AGE_RIG_DB"] = self._env
        self.tmp.cleanup()

    def ver(self, p):
        c = sqlite3.connect(p); v = c.execute("PRAGMA user_version").fetchone()[0]; c.close(); return v

    def run_main(self, argv):
        with contextlib.redirect_stdout(io.StringIO()):
            return migrate.main(argv)

    def test_env_aimed_run_leaves_live_untouched(self):
        os.environ["AGE_RIG_DB"] = self.scratch
        before = (os.path.getmtime(self.live), os.path.getsize(self.live))
        self.run_main(["--apply", "--backup-ok", self.bak])
        self.assertEqual(self.ver(self.live), 1, "live must not be migrated")
        self.assertEqual((os.path.getmtime(self.live), os.path.getsize(self.live)), before)
        self.assertEqual(self.ver(self.scratch), migrate.list_migrations()[-1][0])

    def test_db_flag_aimed_run_leaves_live_untouched(self):
        os.environ.pop("AGE_RIG_DB", None)
        self.run_main(["--db", self.scratch, "--apply", "--backup-ok", self.bak])
        self.assertEqual(self.ver(self.live), 1)
        self.assertEqual(self.ver(self.scratch), migrate.list_migrations()[-1][0])

    def test_conflicting_targets_refused(self):
        os.environ["AGE_RIG_DB"] = self.scratch
        with self.assertRaises(SystemExit):
            self.run_main(["--db", self.live, "--apply", "--backup-ok", self.bak])
        self.assertEqual((self.ver(self.live), self.ver(self.scratch)), (1, 1))


if __name__ == "__main__":
    unittest.main()
