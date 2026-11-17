"""Fixture helper for tests/test_step3_front_room.py. It lives under tests/ (not engine/) because the engine's static
check forbids sqlite3 imports anywhere under engine/. Builds a TEMP, synthetic database from the repo migrations; never
touches the live rig.db."""
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import migrate  # noqa: E402
import gc_settings  # noqa: E402


def seed_domain_vocab(con):
    """The migrations' allowed-word list for a part of life (v:domain) is not the synthetic setup's parts: add the fixture
    setup's domain names (gc.json domains) so a test can record a fact about them."""
    for d in gc_settings.domain_names():
        con.execute("INSERT OR IGNORE INTO kg_vocab(list,value,note) VALUES('v:domain',?,'test setup')", (d,))
    con.commit()


def new_db(path):
    """apply every migration to a fresh file at `path` (must be a temp path) and return an open connection to it"""
    assert os.path.abspath(path) != os.path.abspath(gc_settings.db_path())
    c = sqlite3.connect(path, isolation_level=None)
    for n, p in migrate.list_migrations():
        migrate.apply_file(c, p, n)
    seed_domain_vocab(c)
    c.close()
    return sqlite3.connect(path)


def rw(path):
    """open a read-write connection to a TEMP test database. Engine tests call this instead of importing sqlite3 or db
    themselves (the engine's static check forbids both anywhere under engine/, tests included)."""
    assert os.path.abspath(path) != os.path.abspath(gc_settings.db_path())
    return sqlite3.connect(path)
