#!/usr/bin/env python3
"""disk_preflight.py — THE disk-low preflight: refuse to START a rig/exam run or the full test suite on a nearly full disk.

WHY (2026-11-01): leaked test temp dirs filled the Mac's disk overnight; a rig run or a full suite started on a nearly full
volume then fails half-way in confusing ways (and adds to the pile). Every runner that spawns sessions or suites asks here
first, so the check and its wording live in ONE place.

Rule: refuse when free space on the volume holding $TMPDIR, or on any extra path the caller names (its scratch/output
dir), is below the minimum. Minimum = 5 GB, overridable with LH_DISK_MIN_GB (tests force it high or low). A volume that
cannot be measured is a refusal too (fail closed): a preflight that passes when it cannot see is no preflight.

Library:
    sys.path.insert(0, "<repo>/shared"); import disk_preflight
    disk_preflight.require(extra_paths)        # prints the REFUSED line to stderr and exits 3 when low
    msg = disk_preflight.check(extra_paths)    # None when fine, else the REFUSED line

CLI (for shell runners):
    python3 shared/disk_preflight.py [path ...]   # exit 0 = fine, 3 = REFUSED (message on stderr)
"""
import os
import sys
import tempfile

DEFAULT_MIN_GB = 5.0
REFUSED_RC = 3
GB = 1024 ** 3


def min_gb():
    raw = os.environ.get("LH_DISK_MIN_GB", "").strip()
    if not raw:
        return DEFAULT_MIN_GB
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_MIN_GB


def volume_of(path):
    """The mount point holding path (walks up to the nearest existing ancestor first)."""
    p = os.path.abspath(path)
    while not os.path.exists(p) and os.path.dirname(p) != p:
        p = os.path.dirname(p)
    p = os.path.realpath(p)
    while not os.path.ismount(p) and os.path.dirname(p) != p:
        p = os.path.dirname(p)
    return p


def fmt_need(n):
    return ("%g" % n)


def check(extra_paths=()):
    """None when every volume has enough free space; else the one REFUSED line naming the first short volume."""
    need = min_gb()
    paths = [os.environ.get("TMPDIR") or tempfile.gettempdir()] + [p for p in extra_paths if p]
    seen = set()
    for path in paths:
        vol = volume_of(path)
        if vol in seen:
            continue
        seen.add(vol)
        try:
            st = os.statvfs(vol)
        except OSError as e:
            return "REFUSED: cannot measure free space on %s (%s): free disk space check failed, not starting." % (vol, e)
        free = st.f_bavail * st.f_frsize / GB
        if free < need:
            return "REFUSED: only %.1f GB free on %s (need %s GB): free disk space first." % (free, vol, fmt_need(need))
    return None


def require(extra_paths=()):
    msg = check(extra_paths)
    if msg:
        print(msg, file=sys.stderr)
        sys.exit(REFUSED_RC)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    require(sys.argv[1:])
