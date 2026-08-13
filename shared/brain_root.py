#!/usr/bin/env python3
"""brain_root.py — THE one root variable. Every data path in this system resolves through here.

THE RESIDENCY RULE: the brain is the git repo. The data is OUTSIDE it, one directory level above,
wherever the person says. This module is the only thing that knows where that data root is.

LIFTED, NOT INVENTED (migration T0.1, 2026-08-11): this is the resolver that has been running inside
`system/tools/cowork-ingest/pipeline.py` since 2026-08-08 — moved out verbatim so that every tool,
not just the ingest pipeline, resolves the data root the same way. `pipeline.py` now imports it, so
there is exactly one implementation and it is this one.

Usage as a library:
    import sys, os
    sys.path.insert(0, "<repo>/shared")
    import brain_root
    source, path = brain_root.resolve_brain_root()
    if path is None: ...stop and name the fix; NEVER guess...

Usage as a CLI:
    python3 shared/brain_root.py                      # print RESOLVED: <path>  (source: ...)
    python3 shared/brain_root.py --quiet              # print just the path; exit 1 if NOT-SET
    python3 shared/brain_root.py --set <path>         # remember it, forever
    python3 shared/brain_root.py --set <path> --create
"""

import argparse
import os
import sys

# ── THE BRAIN ROOT: asked once, remembered forever (the author 2026-08-08) ─────────────────────────
# "It's got to be pointed at a specific folder at the very beginning… that needs to be recorded inside
# the skill, and remembered into the future. So when it gets used on an ongoing basis, it's not throwing
# all the files that come out of it in some random place." Before this, the drivers GUESSED the root by
# globbing a cloud-drive path — fine for its original author, wrong for
# anyone on Dropbox, OneDrive, or a plain local folder. This is a REMEMBERED DECISION, not a parameter.
#
# Resolution order, exactly: (1) $LIFEHACK_ROOT, if set and a real directory. (2) the persisted file
# ~/.config/lifehack/brain-root — this system's EXISTING config home (sentinel-paused-sources and
# claude-oauth-token already live there; this is not a second location). (3) the legacy Drive glob —
# BACK-COMPAT ONLY, set via INGEST_LEGACY_ROOT_GLOB, so an existing corpus keeps resolving. (4) otherwise
# NOT-SET. Closed outcome set {RESOLVED, NOT-SET}; NOT-SET is the no-outcome member and must NEVER fall
# through to a guess, a default, or the cwd — every caller checks for it and stops, naming the fix.
BRAIN_ROOT_ENV = "LIFEHACK_ROOT"
BRAIN_ROOT_CONFIG = os.path.expanduser("~/.config/lifehack/brain-root")
# Step (3), back-compat only, and DELIBERATELY not hardcoded: the original owner exports
# INGEST_LEGACY_ROOT_GLOB so an existing corpus keeps resolving where it always did. Unset on
# every other machine, which makes step (3) a no-op rather than a stranger's path. Empty is
# skipped entirely in resolve_brain_root below.
BRAIN_ROOT_LEGACY_GLOB = os.path.expanduser(os.environ.get("INGEST_LEGACY_ROOT_GLOB", ""))


def resolve_brain_root():
    """The one resolver every caller (skill drivers, tests, this CLI) goes through. Returns
    (source, path) with source in {"env", "persisted", "legacy-glob"} and path a real directory, OR
    (None, None) for NOT-SET. Never guesses, never defaults to cwd, never invents a path."""
    env = os.environ.get(BRAIN_ROOT_ENV)
    if env and os.path.isdir(env):
        return "env", env
    if os.path.isfile(BRAIN_ROOT_CONFIG):
        try:
            persisted = open(BRAIN_ROOT_CONFIG).read().strip()
        except OSError:
            persisted = ""
        if persisted and os.path.isdir(persisted):
            return "persisted", persisted
    if BRAIN_ROOT_LEGACY_GLOB:          # unset on a fresh install -> step (3) is a no-op, never a guess
        import glob as _glob
        for hit in sorted(_glob.glob(BRAIN_ROOT_LEGACY_GLOB)):
            if os.path.isdir(hit):
                return "legacy-glob", hit
    return None, None


def set_brain_root(path, create=False):
    """`brain-root --set <path>`. REFUSES a nonexistent path unless create=True (then makes it, parents
    included). REFUSES a path that exists but is a FILE (never silently picks its parent dir). Persists
    the resolved absolute path to BRAIN_ROOT_CONFIG, creating ~/.config/lifehack/ if needed. Returns
    (ok, message-or-path)."""
    resolved = os.path.abspath(os.path.expanduser(path))
    if os.path.exists(resolved):
        if not os.path.isdir(resolved):
            return False, f"REFUSED: '{resolved}' exists and is a FILE, not a directory"
    else:
        if not create:
            return False, f"REFUSED: '{resolved}' does not exist — pass --create to make it"
        os.makedirs(resolved, exist_ok=True)
    os.makedirs(os.path.dirname(BRAIN_ROOT_CONFIG), exist_ok=True)
    with open(BRAIN_ROOT_CONFIG, "w") as f:
        f.write(resolved + "\n")
    return True, resolved


NOT_SET_MESSAGE = ("NOT-SET — no $" + BRAIN_ROOT_ENV + ", no persisted " + BRAIN_ROOT_CONFIG +
                   ", and no legacy Drive folder found. Fix: brain_root.py --set <path> "
                   "(add --create for a new folder).")


def main(argv=None):
    """The same contract as `pipeline.py brain-root`, reachable without the ingest pipeline —
    because the data root is the whole system's variable, not the ingest chain's."""
    ap = argparse.ArgumentParser(description="resolve / persist the one data root everything writes under")
    ap.add_argument("--set", dest="set_path", metavar="PATH",
                    help="record this path as the brain root (persists to " + BRAIN_ROOT_CONFIG + ")")
    ap.add_argument("--create", action="store_true", help="with --set: create the folder if missing")
    ap.add_argument("--quiet", action="store_true", help="print only the path; exit 1 if NOT-SET")
    a = ap.parse_args(argv)
    if a.set_path:
        ok, res = set_brain_root(a.set_path, create=a.create)
        if not ok:
            print(res)
            return 1
        verb = "created + " if a.create else ""
        print(f"RESOLVED: {res}  (source: persisted — just {verb}set via --set)")
        return 0
    source, path = resolve_brain_root()
    if path is None:
        if not a.quiet:
            print(NOT_SET_MESSAGE)
        return 1
    print(path if a.quiet else f"RESOLVED: {path}  (source: {source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
