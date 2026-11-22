#!/usr/bin/env python3
"""feeds.py (4P.0b): which of Grand Central's three feeds are set up, connected or failing,
derived ONLY from what the engine already records. No network, no login check, no guessing.

A feed is one of email, calendar, tasks. Its state is one of:
  not_set_up  the settings that name the feed do not exist (never configured);
  connected   configured, and its last recorded successful pull is inside its freshness interval;
  failing     configured, but the last recorded pull is missing (never succeeded), or stale beyond
              the interval (a pull that errored is never recorded as a success -- pull.py marks a
              source fresh only when it added no new error rows, so "stale/absent" covers "errored").

What the engine records, and what each feed's signal is:
  - the setup files, through the ONE settings loader (gc_settings). Calendar and tasks have no
    per-feed setup key: pull.py serves both whenever the setup resolves and gc.json loads, so their
    "configured" signal IS that setup. Email's signal is gc.json mailroom_user (env AGE_MAILROOM_USER
    kept, as gc_settings.mailroom_user() reads it).
  - the source_state table: pull.py writes calendar/tasks rows only on an error-free pull; the email
    notion is source_state 'gmail' (what store.freshness() reads); 'daily' and 'labels' are other
    machinery and are not feeds.

Intervals mirror the engine's own: calendar/tasks 18h (pull.FRESH_HOURS, not imported here -- pull.py
pulls in rig_env and is not safe to import for a constant), email 25h (store.DEFAULT_STALE_MIN, with
env AGE_STALE_MIN honored, exactly as store.freshness() reads it).

The gate (read_gate): None when at least one feed is connected (reads answer from the model as
before, output unchanged); otherwise a named payload {"state": ..., "feeds": {...}} the gc reads
return INSTEAD of data, exit 0 -- "no_feed_connected" when every feed is not_set_up, "feed_failing"
when something is configured but nothing is connected (including a missing or empty database).
Python 3.9 compatible."""
import datetime
import os

import gc_settings

FEEDS = ("email", "calendar", "tasks")
SOURCE = {"email": "gmail", "calendar": "calendar", "tasks": "tasks"}
# calendar/tasks: pull.FRESH_HOURS (kept in step here; pull.py imports rig_env, not importable for a constant)
FRESH_HOURS_FEEDS = 18


def _setup_doc():
    """gc.json through the one settings loader, or None when there is no setup (never raises)."""
    try:
        return gc_settings.load("gc.json")
    except gc_settings.SettingsError:
        return None


def _configured(name, doc):
    if not isinstance(doc, dict):
        return False
    if name == "email":
        if os.environ.get("AGE_MAILROOM_USER"):
            return True
        return bool(doc.get("mailroom_user"))
    return True  # calendar/tasks: the setup itself is their configuration (see module docstring)


def _rows():
    """source_state rows by source, or {} when the database is missing/unreadable (never creates one)."""
    try:
        import store
        with store._read() as con:
            return dict((r["source"], dict(r)) for r in con.execute(
                "SELECT source, last_success_at, rows FROM source_state").fetchall())
    except Exception:  # noqa: BLE001 (no database, empty file, old schema: no pull has ever been recorded)
        return {}


def _age_min(last, now):
    t = datetime.datetime.fromisoformat(str(last).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return (now - t).total_seconds() / 60.0


def _interval_min(name):
    if name == "email":
        return float(os.environ.get("AGE_STALE_MIN") or 25 * 60)  # store.DEFAULT_STALE_MIN / AGE_STALE_MIN
    return FRESH_HOURS_FEEDS * 60.0


def feed_state(name, doc, rows, now):
    """One feed's state dict (a consumer renders it; this module never formats for a person)."""
    out = {"feed": name, "state": "not_set_up", "configured": False, "last_success_at": None, "detail": None}
    if not _configured(name, doc):
        out["detail"] = "not configured in the setup files"
        return out
    out["configured"] = True
    src = SOURCE[name]
    row = rows.get(src)
    if name == "email":  # build window review: today the envelope pull records as 'daily' (gc-daily), not 'gmail'
        cands = [r for r in (rows.get("gmail"), rows.get("daily")) if r and r.get("last_success_at")]
        row = max(cands, key=lambda r: str(r["last_success_at"])) if cands else None
    last = row.get("last_success_at") if row else None
    out["source"] = src
    if not last:
        out["state"] = "failing"
        out["detail"] = "configured; no successful %s pull recorded in source_state" % src
        return out
    out["last_success_at"] = last
    try:
        age = _age_min(last, now)
    except (ValueError, TypeError):
        out["state"] = "failing"
        out["detail"] = "configured; source_state[%s] last_success_at is not a timestamp" % src
        return out
    out["age_min"] = round(age, 1)
    if age > _interval_min(name):
        out["state"] = "failing"
        out["detail"] = "configured; last %s pull %.0f min ago, over the %.0f min interval" % (src, age, _interval_min(name))
        return out
    out["state"] = "connected"
    out["detail"] = "ok"
    return out


def feed_states(now=None):
    """All three feeds' states. Used by the gate AND by `gc status --json` (which prints them even when connected)."""
    import clock
    doc = _setup_doc()
    rows = _rows()
    now = now or clock.now()
    return dict((n, feed_state(n, doc, rows, now)) for n in FEEDS)


def _has_model_data():
    """True when the model holds at least one person, organization, project or event besides the owner. The
    migrations seed person:me, world:world and a topic, so a freshly migrated database still reads as having
    nothing to show. Never creates a database."""
    try:
        import store
        with store._read() as con:
            return con.execute("SELECT 1 FROM kg_things WHERE kind IN ('person', 'organization', 'company', 'project', 'event') "
                               "AND key <> 'person:me' AND retired_at IS NULL LIMIT 1").fetchone() is not None
    except Exception:  # noqa: BLE001 (no database, empty file, schema not migrated)
        return False


def read_gate(now=None):
    """None when a feed is connected (the reads answer from the model, output unchanged); otherwise the named
    payload every gc read returns instead of data, exit 0 (4P.0b: never an sqlite error, never 'broken')."""
    feeds = feed_states(now)
    states = [f["state"] for f in feeds.values()]
    if "connected" in states or _has_model_data():
        # Build window review (4P.0b): a stale or failing feed never hides data already in the model -- the
        # person's PRM stays readable; `gc status --json` reports each feed's state. The named payload
        # replaces output only when there is nothing to show (no database, an empty file, no things).
        return None
    overall = "no_feed_connected" if all(s == "not_set_up" for s in states) else "feed_failing"
    return {"state": overall, "feeds": feeds}


def text_line(payload):
    """The one plain line the non-JSON reads print for a gate payload."""
    parts = "; ".join("%s %s" % (n, f["state"]) for n, f in sorted(payload["feeds"].items()))
    return "%s (%s)" % (payload["state"].replace("_", " "), parts)
