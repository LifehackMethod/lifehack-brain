"""db.py: the one connect() for rig.db. Pragmas live here and nowhere else."""
import os
import sqlite3

from rig_env import RIG_HOME

DEFAULT_PATH = os.path.join(RIG_HOME, "rig.db")


def connect(path=None, readonly=False):
    path = os.path.abspath(os.path.expanduser(path or DEFAULT_PATH))
    if readonly:
        conn = sqlite3.connect("file:%s?mode=ro" % path.replace("?", "%3f").replace("#", "%23"), uri=True)
    else:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def current_version(conn):
    return conn.execute("PRAGMA user_version").fetchone()[0]
