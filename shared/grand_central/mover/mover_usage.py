#!/usr/bin/env python3
# origin: 92a9739:mover/mover_usage.py
"""mover_usage.py - total the script's logged usage per day, compare to Google's ceilings (limits.py), write a status tile.
Tracker only: it alerts at >=50% of any Google ceiling; it never throttles anything.
  python3 mover_usage.py --tile /path/to/mover-usage.json [<mover_dir>/result.json]   (--tile defaults to <NOTES>/state/status/gc-mover.json)
Also WARNs if the timer has been silent for over 1h (permission expiry).
"""
import argparse, collections, datetime, json, os, sys
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import limits as L  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # shared/grand_central: the one settings loader
import gc_settings  # noqa: E402
import local_first  # noqa: E402


def mover_dir():
    """The Drive folder the mover script owns (request.json / result.json live there): setup gc.json mover_dir."""
    return str(gc_settings.gc("mover_dir"))


def tile_path():
    """<notes>/state/status/gc-mover.json, the notes folder from the one settings loader."""
    return os.path.join(gc_settings.notes_root(), "state", "status", "gc-mover.json")


STALE_AFTER_S = 3600   # the timer runs every 15 min; an hour of silence means it stopped
QUOTA_TZ = "America/Los_Angeles"   # Google's daily quotas reset at midnight Pacific


def per_day(usage, tz=QUOTA_TZ):
    z = ZoneInfo(tz)
    days = collections.OrderedDict()
    for u in sorted(usage, key=lambda u: u["ts"]):
        ts = datetime.datetime.fromisoformat(u["ts"].replace("Z", "+00:00")).astimezone(z)
        d = days.setdefault(ts.date().isoformat(), {"runs": 0, "runtime_ms": 0, "max_run_ms": 0, "gmail_calls": 0,
                                                     "ids_modified": 0, "drive_ops": 0, "properties_ops": 0})
        d["runs"] += 1
        d["runtime_ms"] += u.get("runtime_ms", 0)
        d["max_run_ms"] = max(d["max_run_ms"], u.get("runtime_ms", 0))
        for k in ("gmail_calls", "ids_modified", "drive_ops", "properties_ops"):
            d[k] += u.get(k, 0)
    return days


def measures(day):
    """name -> value in the ceiling's own unit."""
    return {"runtime_min_per_day": day["runtime_ms"] / 60000.0,
            "runtime_min_per_run": day["max_run_ms"] / 60000.0,
            "gmail_ops_per_day": day["ids_modified"],     # each id modified counted as 1 (worst-case mapping)
            "properties_ops_per_day": day["properties_ops"]}


def build_tile(result, now=None, tz=QUOTA_TZ, result_mtime=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    today = now.astimezone(ZoneInfo(tz)).date().isoformat()
    days = per_day(result.get("usage", []), tz)
    day = days.get(today) or {"runs": 0, "runtime_ms": 0, "max_run_ms": 0, "gmail_calls": 0, "ids_modified": 0,
                              "drive_ops": 0, "properties_ops": 0}
    kpis, warn = [], []
    for name, val in measures(day).items():
        ceiling, unit, label = L.CEILINGS[name]
        frac = val / ceiling
        kpis.append({"key": name, "label": label, "value": round(val, 2), "sub": "%.0f%% of %s %s" % (frac * 100, ceiling, unit)})
        if frac >= L.WARN_FRACTION:
            warn.append({"title": label, "detail": "%.2f of %s %s (%.0f%%)" % (val, ceiling, unit, frac * 100)})
    usage = result.get("usage", [])
    if usage:
        last = max(datetime.datetime.fromisoformat(u["ts"].replace("Z", "+00:00")) for u in usage)
    elif result_mtime is not None:
        last = datetime.datetime.fromtimestamp(result_mtime, datetime.timezone.utc)   # no runs logged: file age since setup
    else:
        last = None
    if last is not None and (now - last).total_seconds() > STALE_AFTER_S:
        hrs = int((now - last).total_seconds() // 3600)
        warn.insert(0, {"title": "Mover timer stale",
                        "detail": "mover timer has not run for %dh — Google may have expired its permission (7-day testing expiry); "
                                  "fix = link a standard Cloud project set to In production" % hrs})
    status = "WARN" if warn else "OK"
    summary = "%s: %d runs today (%s PT), %.1f min runtime, %d ids modified" % (
        status, day["runs"], today, day["runtime_ms"] / 60000.0, day["ids_modified"])
    return {"desk": gc_settings.pulse_desk(), "schema_version": 2, "pulse_job": "mover-usage", "emit_mode": "pulse",
            "stale_after_s": 43200, "last_run": now.astimezone().isoformat(timespec="seconds"), "rc": 0,
            "status": status, "summary": summary, "kpis": kpis, "items": warn}


def allow_materialize():
    """A job started by the scheduler may be barred from downloading a Google Drive file that has not been opened locally
    yet (macOS: IOPOL_MATERIALIZE_DATALESS_FILES off), and then every read fails with errno 11, "Resource deadlock avoided".
    Turn the download permission back ON for this process only. No-op off macOS."""
    try:
        import ctypes
        ctypes.CDLL(None).setiopolicy_np(3, 0, 2)    # type=MATERIALIZE_DATALESS_FILES, scope=PROCESS, value=ON
    except (OSError, AttributeError):
        pass


def read_result_ex(path, tries=4, wait=3.0):
    """Read result.json -> (dict, stale_note or None). local_first retries a Drive-busy error (EDEADLK/EAGAIN) `tries` times
    (`wait` seconds apart) even when a local copy exists; if Drive still fails the local copy is returned WITH a stale note;
    with no local copy it fails loudly (OSError naming both paths)."""
    import errno
    try:
        data, stale = local_first.read_ex(path, retries=tries, backoff=wait)
    except local_first.DriveReadError as e:
        raise OSError(errno.EDEADLK, str(e)) from e
    return json.loads(data.decode("utf-8")), stale


def read_result(path, tries=4, wait=3.0):
    return read_result_ex(path, tries, wait)[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--result", default=None, help="result.json (default: <gc.json mover_dir>/result.json)")
    ap.add_argument("--tile", default=None)
    a = ap.parse_args(argv)
    a.result = a.result or os.path.join(mover_dir(), "result.json")
    a.tile = a.tile or tile_path()
    allow_materialize()
    try:
        result, stale = read_result_ex(a.result)
        # a stale result must not be paired with Drive's newer mtime: the age is the age of the copy we actually read
        tile = build_tile(result, result_mtime=(local_first.local_mtime(a.result) if stale else local_first.mtime(a.result)))
        if stale:
            tile["items"] = [{"title": "result.json is stale", "detail": stale}] + list(tile.get("items") or [])
            tile["status"] = "WARN"
            tile["summary"] = "WARN (STALE result.json, Drive unreadable; older local copy used): " + tile["summary"].split(": ", 1)[-1]
    except (OSError, ValueError, KeyError, local_first.DriveReadError) as e:
        now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        tile = {"desk": gc_settings.pulse_desk(), "schema_version": 2, "pulse_job": "mover-usage", "emit_mode": "pulse",
                "stale_after_s": 43200, "last_run": now, "rc": 1, "status": "ERROR",
                "summary": "cannot read result.json: %s" % e}
    # through the plugin's one writer (it rejects any status word it does not allow; WARN is written as NEEDS_REVIEW).
    # The summary line keeps the word WARN, which the job wrapper reads.
    from status_lights import write_tile   # shared/grand_central/status_lights.py (on the path through gc_settings above)
    write_tile(a.tile, tile)
    print(tile["summary"])
    return tile["rc"]


if __name__ == "__main__":
    sys.exit(main())
