#!/usr/bin/env python3
"""Backups for rig.db. Always the sqlite3 backup API, never a file copy (safe under WAL).

  backup.py local                      consistent copy -> <backups>/rig-<UTCts>.db, keep last 30, prints path
  backup.py snapshot                   local backup, then -> <NOTES>/<state folder>/snapshots/rig-<YYYYMMDD>.db
                                       (one per UTC day, same-day replaced, keep newest 14). Refuses if any
                                       body-like column holds data (email text must never reach Drive).
  backup.py settings                   copy setup/*.json -> <NOTES>/<state folder>/snapshots/settings-<YYYYMMDD>/
                                       (newest 14 kept), then check every source file is there and identical.
                                       Separate from `snapshot` on purpose: a settings problem must never stop
                                       the database snapshot. The nightly runner calls it AFTER the db proof.
  backup.py verify-settings [DIR]      check a settings snapshot (default: newest) against setup/*.json; exit 1 if
                                       any file is missing or differs
  backup.py restore <file> --to <new>  restore into a NEW path, then integrity_check + row counts vs the source
  backup.py verify <file>              integrity_check + per-table row counts

Env (for tests): AGE_RIG_DB, AGE_BACKUP_DIR, AGE_NOTES_ROOT, AGE_SETTINGS_DIR.
"""
import argparse, datetime as dt, hashlib, os, re, shutil, sqlite3, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gc_settings  # noqa: E402

KEEP_LOCAL = 30
KEEP_SNAPSHOTS = 14
# column names that would mean message body text lives in the db
BODY_COL = re.compile(r"body|text_?plain|plain_?text|html|snippet", re.I)


def rig_db():
    return Path(os.environ.get("AGE_RIG_DB") or gc_settings.db_path())


def backup_dir():
    return Path(os.environ.get("AGE_BACKUP_DIR") or os.path.join(gc_settings.data_root(), "backups"))


def snapshot_dir():
    notes = gc_settings.notes_root()      # AGE_NOTES_ROOT, else gc.json notes_root
    return Path(notes) / gc_settings.state_subdir() / "snapshots"


def settings_dir():
    """The person's own settings: AGE_SETTINGS_DIR, else the setup folder gc_settings finds (setup/*.json)."""
    return Path(os.environ.get("AGE_SETTINGS_DIR") or gc_settings.setup_dir())


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_settings(snap, src=None):
    """Compare a settings snapshot dir to the source. Returns problems (empty = good).
    An empty source is itself a problem: a snapshot of nothing must never look like success."""
    src, snap = Path(src) if src else settings_dir(), Path(snap)
    want = sorted(src.glob("*.json")) if src.is_dir() else []
    if not want:
        return [f"no settings files found in {src}"]
    probs = []
    for f in want:
        g = snap / f.name
        if not g.is_file():
            probs.append(f"missing from snapshot: {f.name}")
        elif _sha(g) != _sha(f):
            probs.append(f"differs from source: {f.name}")
    return probs


def settings_snapshot(src=None):
    """Copy setup/*.json into a dated folder beside the db snapshots, check it, keep newest 14."""
    src = Path(src) if src else settings_dir()
    d = snapshot_dir()
    d.mkdir(parents=True, exist_ok=True)
    final = d / f"settings-{_utcnow().strftime('%Y%m%d')}"
    tmp = d / f".{final.name}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    for f in sorted(src.glob("*.json")):
        shutil.copyfile(f, tmp / f.name)
    probs = check_settings(tmp, src)
    if probs:
        shutil.rmtree(tmp, ignore_errors=True)
        raise SystemExit("settings snapshot failed: " + "; ".join(probs))
    shutil.rmtree(final, ignore_errors=True)  # same-day replaced
    os.replace(tmp, final)
    for old in sorted(p for p in d.iterdir() if re.fullmatch(r"settings-\d{8}", p.name))[:-KEEP_SNAPSHOTS]:
        shutil.rmtree(old)
    return final


def _ro(path, immutable=False):
    """Read-only. immutable=True is for finished backup FILES only (never the live db): it opens with no
    locking and no -wal/-shm, so nothing is ever created next to the file."""
    if immutable:
        p = os.path.abspath(os.path.expanduser(str(path))).replace("?", "%3f").replace("#", "%23")
        return sqlite3.connect("file:%s?mode=ro&immutable=1" % p, uri=True)
    import db as rigdb
    return rigdb.connect(path, readonly=True)


def copy_db(src, dst):
    """Online-consistent copy via the backup API. src opened read-only."""
    s = _ro(src)
    d = sqlite3.connect(str(dst))
    try:
        s.backup(d)
        # backup copies the source's WAL flag; a backup must be ONE self-contained file
        d.execute("PRAGMA journal_mode=DELETE")
    finally:
        d.close()
        s.close()
    os.chmod(dst, 0o600)


def _tables(con):
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]


def row_counts(path, immutable=False):
    con = _ro(path, immutable)
    try:
        return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in _tables(con)}
    finally:
        con.close()


def integrity(path):
    con = _ro(path, True)
    try:
        return [r[0] for r in con.execute("PRAGMA integrity_check")]
    finally:
        con.close()


def verify(path):
    """Returns (ok, counts, problems)."""
    probs = []
    ic = integrity(path)
    if ic != ["ok"]:
        probs.append(f"integrity_check: {ic[:5]}")
    return (not probs), row_counts(path, True), probs


def backup_matches(backup_file, live_db):
    """Replacement for the old byte-identical (cmp) guard, which breaks under WAL:
    the backup passes integrity_check and has the same per-table row counts as the live db right now."""
    ok, counts, _ = verify(backup_file)
    return ok and counts == row_counts(live_db)  # live db: normal read-only (WAL-aware)


def check_no_body(path):
    """Raise if any body-like column holds data (path is a finished backup file)."""
    con = _ro(path, True)
    bad = []
    try:
        for t in _tables(con):
            for c in con.execute(f'PRAGMA table_info("{t}")').fetchall():
                if BODY_COL.search(c[1]):
                    n = con.execute(
                        f'SELECT COUNT(*) FROM "{t}" WHERE "{c[1]}" IS NOT NULL AND "{c[1]}" != \'\'').fetchone()[0]
                    if n:
                        bad.append(f"{t}.{c[1]} ({n} rows)")
    finally:
        con.close()
    if bad:
        raise SystemExit("refused: body-like column(s) hold data: " + ", ".join(bad))


def _utcnow():
    return dt.datetime.now(dt.timezone.utc)


def _prune(d, pattern, keep):
    files = sorted(p for p in d.iterdir() if re.fullmatch(pattern, p.name))
    for p in files[:-keep]:
        p.unlink()


def local_backup(src=None):
    src = Path(src) if src else rig_db()
    d = backup_dir()
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    ts = _utcnow().strftime("%Y%m%dT%H%M%S")
    out, i = d / f"rig-{ts}Z.db", 0
    while out.exists():
        i += 1
        out = d / f"rig-{ts}-{i}Z.db"
    copy_db(src, out)
    ok, _, probs = verify(out)
    if not ok:
        out.unlink()
        raise SystemExit("backup failed verification: " + "; ".join(probs))
    _prune(d, r"rig-\d{8}T\d{6}(-\d+)?Z\.db", KEEP_LOCAL)
    return out


def snapshot(src=None):
    local = local_backup(src)
    check_no_body(local)  # fail before anything touches the notes folder
    d = snapshot_dir()
    d.mkdir(parents=True, exist_ok=True)
    final = d / f"rig-{_utcnow().strftime('%Y%m%d')}.db"
    tmp = d / f".{final.name}.tmp"
    shutil.copyfile(local, tmp)
    os.chmod(tmp, 0o600)
    ok, _, probs = verify(tmp)
    if not ok:
        tmp.unlink()
        raise SystemExit("snapshot failed verification: " + "; ".join(probs))
    os.replace(tmp, final)  # same-day snapshot replaced
    _prune(d, r"rig-\d{8}\.db", KEEP_SNAPSHOTS)
    return final


def restore(src, to):
    src, to = Path(src).expanduser().resolve(), Path(to).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"no such file: {src}")
    if to == rig_db().resolve() or to.exists():
        raise SystemExit(f"refused: --to must be a NEW path (never overwrites): {to}")
    to.parent.mkdir(parents=True, exist_ok=True)
    copy_db(src, to)
    ok, counts, probs = verify(to)
    src_counts = row_counts(src, True)
    if counts != src_counts:
        probs.append("row counts differ: " + str({t: (src_counts.get(t), counts.get(t))
                     for t in set(src_counts) | set(counts) if src_counts.get(t) != counts.get(t)}))
    return (not probs), counts, probs


def _report(ok, counts, probs, label):
    print(f"{label}: {'OK' if ok else 'FAIL'}; integrity_check {'ok' if not any('integrity' in p for p in probs) else 'BAD'}; "
          f"{len(counts)} tables, {sum(counts.values())} rows")
    for t, n in counts.items():
        print(f"  {t}: {n}")
    for p in probs:
        print("  PROBLEM:", p)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("local")
    sub.add_parser("snapshot")
    r = sub.add_parser("restore"); r.add_argument("file"); r.add_argument("--to", required=True)
    sub.add_parser("settings")
    vs = sub.add_parser("verify-settings"); vs.add_argument("dir", nargs="?")
    v = sub.add_parser("verify"); v.add_argument("file")
    a = ap.parse_args(argv)
    if a.cmd == "local":
        print(local_backup())
    elif a.cmd == "snapshot":
        print(snapshot())
    elif a.cmd == "settings":
        print(settings_snapshot())
    elif a.cmd == "verify-settings":
        d = a.dir
        if not d:
            sd = snapshot_dir()
            found = sorted(p for p in sd.glob("settings-*") if p.is_dir()) if sd.is_dir() else []
            if not found:
                print("verify-settings: FAIL; no settings snapshot found in %s" % sd)
                return 1
            d = found[-1]
        probs = check_settings(d)
        print("verify-settings %s: %s" % (d, "OK" if not probs else "FAIL"))
        for p in probs:
            print("  PROBLEM:", p)
        return 0 if not probs else 1
    elif a.cmd == "restore":
        ok, c, p = restore(a.file, a.to)
        _report(ok, c, p, f"restore -> {a.to}")
        return 0 if ok else 1
    else:
        ok, c, p = verify(a.file)
        _report(ok, c, p, f"verify {a.file}")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
