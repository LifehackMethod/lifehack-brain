"""migrate.py: apply the migrations to rig.db. Dry run by default.

Two series, each with its own version record:
  plugin  migrations/NNN_name.sql (this folder; the same for everyone)        recorded in PRAGMA user_version
  owner   <setup>/migrations/NNN_name.sql (the person's own seed rows, from   recorded in the table owner_migrations
          gc_settings.setup_dir(); none = nothing to do)                       (version, name, applied_at)
The plugin series runs first, then the owner series. Each file runs in one transaction and is recorded in that same
transaction; the first error stops the run (rolled back). The numbers never collide: plugin 029 and owner 003 are
different series with different records.

An existing database that has no owner record yet (made before the owner series existed) is never given the owner
series blindly: the run refuses until it is told how far the owner series is already in it, with --owner-baseline N
(records owner versions 1..N as applied WITHOUT running them; only on an empty owner record).

  python3 migrate.py [--db PATH]                                           # dry run: report what would happen
  python3 migrate.py --apply --backup-ok FILE [--db PATH] [--owner-baseline N]   # act; FILE must exist and be < 10 min old
"""
import argparse
import glob
import os
import re
import sqlite3
import sys
import tempfile
import time

import db

HERE = os.path.dirname(os.path.abspath(__file__))
MIG_DIR = os.path.join(HERE, "migrations")
BASELINE = 1
OWNER_TABLE = ("CREATE TABLE IF NOT EXISTS owner_migrations(version INTEGER PRIMARY KEY, name TEXT NOT NULL, "
               "applied_at TEXT NOT NULL)")


def owner_dir():
    """<setup>/migrations. No setup folder at all (a student install) = no owner series: returns None. May not exist."""
    import gc_settings
    try:
        return os.path.join(gc_settings.setup_dir(), "migrations")
    except gc_settings.SettingsError:
        return None


def list_owner_migrations(d=None):
    d = owner_dir() if d is None else d
    return list_migrations(d) if d and os.path.isdir(d) else []


def owner_version(conn):
    """Highest recorded owner version; None when the database has no owner record at all."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='owner_migrations'").fetchone():
        return None
    return conn.execute("SELECT coalesce(max(version), 0) FROM owner_migrations").fetchone()[0]


def apply_owner_file(conn, path, version):
    """Run one owner migration in one transaction and record it in owner_migrations. conn must be isolation_level=None."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(OWNER_TABLE)
        with open(path, encoding="utf-8") as f:
            for st in statements(f.read()):
                conn.execute(st)
        conn.execute("INSERT INTO owner_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                     (version, os.path.basename(path), time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def seed_domain_vocab(conn):
    """The person's own parts of life (gc.json domains) are allowed v:domain words, seeded from their setup, not only by an
    owner migration. Inserts only the missing ones, so a database that already has them (the owner's, via owner migration
    002) is unchanged. No setup folder or no domains = nothing to seed. Runs inside the caller's connection, outside a
    transaction (isolation_level=None)."""
    import gc_settings
    try:
        names = gc_settings.domain_names()
    except gc_settings.SettingsError:
        return 0
    n = 0
    for name in names:
        if not conn.execute("SELECT 1 FROM kg_vocab WHERE list='v:domain' AND value=?", (name,)).fetchone():
            conn.execute("INSERT INTO kg_vocab(list, value, note) VALUES ('v:domain', ?, 'from setup gc.json domains')", (name,))
            n += 1
    return n


def mark_owner_baseline(conn, upto, owner_migs):
    """Record owner versions 1..upto as already in the database, without running them (one transaction)."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(OWNER_TABLE)
        for n, p in owner_migs:
            if n <= upto:
                conn.execute("INSERT INTO owner_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                             (n, os.path.basename(p) + " (baseline: already in the database)",
                              time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def list_migrations(mig_dir=MIG_DIR):
    out = []
    for p in sorted(glob.glob(os.path.join(mig_dir, "*.sql"))):
        m = re.match(r"(\d{3})_.+\.sql$", os.path.basename(p))
        if not m:
            raise SystemExit("bad migration name: %s" % p)
        out.append((int(m.group(1)), p))
    nums = [n for n, _ in out]
    if nums != list(range(1, len(nums) + 1)):
        raise SystemExit("migrations not contiguous from 001: %s" % nums)
    return out


def statements(sql):
    buf = ""
    for line in sql.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            if buf.strip():
                yield buf.strip()
            buf = ""
    if buf.strip():
        raise ValueError("trailing incomplete statement: %r" % buf[:80])


def apply_file(conn, path, version):
    """Run one migration in one transaction and bump user_version. conn must be isolation_level=None."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        with open(path, encoding="utf-8") as f:
            for st in statements(f.read()):
                conn.execute(st)
        conn.execute("PRAGMA user_version=%d" % version)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def schema_dump(conn):
    """Comparable picture of a schema: sqlite_master rows plus column order of every table/view."""
    d = {}
    for t, n, tbl, sql in conn.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"):
        d[(t, n)] = " ".join((sql or "").split())
        if t in ("table", "view"):
            cols = conn.execute("PRAGMA table_xinfo('%s')" % n).fetchall()
            d[("columns", n)] = repr([(c[1], c[2], c[3], c[4], c[5], c[6]) for c in cols])
    return d


def schema_diff(a, b):
    lines = []
    for k in sorted(set(a) | set(b)):
        if k not in a:
            lines.append("only in expected: %s %s" % k)
        elif k not in b:
            lines.append("only in database: %s %s" % k)
        elif a[k] != b[k]:
            lines.append("differs: %s %s\n    database: %s\n    expected: %s" % (k + (a[k], b[k])))
    return lines


def fresh_build(upto, mig_dir=MIG_DIR, owner_migs=()):
    """Build an in-memory db from plugin migrations 1..upto, then the given owner migrations; return it."""
    c = sqlite3.connect(":memory:", isolation_level=None)
    for n, p in list_migrations(mig_dir):
        if n <= upto:
            apply_file(c, p, n)
    for n, p in owner_migs:
        apply_owner_file(c, p, n)
    return c


def resolve_db(arg=None, env=None):
    """Which file to act on, the same order the front door uses: --db > env AGE_RIG_DB > the live default.
    (2026-11-13: this used to ignore AGE_RIG_DB, so a run meant for a scratch copy migrated the live rig.db.)
    --db and AGE_RIG_DB naming two different files is refused rather than guessed. Returns (abs path, why) or
    (None, reason)."""
    env = os.environ.get("AGE_RIG_DB") if env is None else env
    ab = lambda p: os.path.abspath(os.path.expanduser(p))  # noqa: E731
    if arg and env and ab(arg) != ab(env):
        return None, "--db %s and AGE_RIG_DB %s name different files; pick one" % (ab(arg), ab(env))
    if arg:
        return ab(arg), "--db"
    if env:
        return ab(env), "AGE_RIG_DB"
    return ab(db.DEFAULT_PATH), "default (the LIVE rig.db)"


def check_backup(path):
    if not path or not os.path.isfile(path):
        raise SystemExit("--backup-ok: file does not exist: %s" % path)
    age = time.time() - os.path.getmtime(path)
    if age > 600:
        raise SystemExit("--backup-ok: backup is %.0f min old (limit 10): %s" % (age / 60, path))


def run(db_path, apply=False, backup_ok=None, mig_dir=MIG_DIR, out=print, owner_migs=None, owner_baseline=None):
    """Returns 0 ok, 1 refused/failed. owner_migs: the owner series (default: the person's setup/migrations)."""
    migs = list_migrations(mig_dir)
    owner_migs = list_owner_migrations() if owner_migs is None else owner_migs
    conn = db.connect(db_path, readonly=not apply)
    conn.isolation_level = None
    ver = db.current_version(conn)
    head = migs[-1][0] if migs else 0
    out("database at user_version %d, migrations head %d" % (ver, head))
    if ver > head:
        out("REFUSE: database is newer than the migrations")
        return 1
    existing = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchone()[0] > 0
    plan = []
    if ver == 0 and existing:
        diff = schema_diff(schema_dump(conn), schema_dump(fresh_build(BASELINE, mig_dir)))
        if diff:
            out("REFUSE: existing database at version 0 does not match 001_baseline:")
            for l in diff:
                out("  " + l)
            return 1
        plan.append("stamp user_version=1 (schema equals 001, no DDL)")
        ver = 1
    was_empty = ver == 0 and not existing
    plan += ["apply %s" % os.path.basename(p) for n, p in migs if n > ver]
    ov = owner_version(conn)
    owner_head = owner_migs[-1][0] if owner_migs else 0
    if owner_baseline is not None:
        if ov or owner_baseline > owner_head or owner_baseline < 0:
            out("REFUSE: --owner-baseline %d needs an empty owner record and at most the owner head %d" % (owner_baseline, owner_head))
            return 1
        plan.append("record owner versions 1..%d as already applied (baseline, nothing run)" % owner_baseline)
        ov = owner_baseline
    elif ov is None and owner_migs and not was_empty:
        out("REFUSE: this database has no owner record and the setup has %d owner migration(s); say how far they are "
            "already in it with --owner-baseline N (on a fresh backup)" % len(owner_migs))
        return 1
    ov = ov or 0
    if ov > owner_head:
        out("REFUSE: database owner version %d is newer than the owner migrations (head %d)" % (ov, owner_head))
        return 1
    plan += ["apply owner %s" % os.path.basename(p) for n, p in owner_migs if n > ov]
    out("owner series: recorded %s, head %d" % ("none" if owner_version(conn) is None else owner_version(conn), owner_head))
    if not plan:
        out("up to date")
        return 0
    for p in plan:
        out(("WOULD: " if not apply else "DO: ") + p)
    if not apply:
        out("dry run; use --apply --backup-ok FILE to act")
        return 0
    check_backup(backup_ok)
    if db.current_version(conn) == 0 and existing:
        conn.execute("PRAGMA user_version=1")
    for n, p in migs:
        if n > max(db.current_version(conn), 0):
            apply_file(conn, p, n)
    if owner_baseline is not None:
        mark_owner_baseline(conn, owner_baseline, owner_migs)
    for n, p in owner_migs:
        if n > (owner_version(conn) or 0):
            apply_owner_file(conn, p, n)
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='kg_vocab'").fetchone():
        seed_domain_vocab(conn)
    out("now at user_version %d, owner version %s" % (db.current_version(conn), owner_version(conn)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="default; accepted for readability")
    ap.add_argument("--backup-ok", default=None, metavar="FILE")
    ap.add_argument("--owner-baseline", type=int, default=None, metavar="N",
                    help="record owner migrations 1..N as already in this database (an existing database, once)")
    a = ap.parse_args(argv)
    if a.apply and a.dry_run:
        ap.error("--apply and --dry-run conflict")
    if a.apply:
        check_backup(a.backup_ok)
    target, why = resolve_db(a.db)
    if target is None:
        raise SystemExit("REFUSE: " + why)
    print("target database: %s (%s)" % (target, why))
    return run(target, apply=a.apply, backup_ok=a.backup_ok, owner_baseline=a.owner_baseline)


if __name__ == "__main__":
    sys.exit(main())
