#!/usr/bin/env python3
"""team_skills_root.py — where the TEAM's shared-skills Drive folder lives (approved design
2026-11-01, SIMPLE build: file-system only, a local Drive-for-Desktop mount; no gws, no Drive API).

Not the person's notes (brain_root.py), not their personal code (personal_code_root.py): the one
folder a team picks to share skills through. Same pointer pattern as personal_code_root.py —
a one-line file in the config home, `~` allowed, and a pointer that names a folder that is GONE is
its own outcome and NEVER falls back anywhere: silently switching folders would split a team's
shared skills in two.

Files (all in ~/.config/lifehack/, all optional, all one line):
  team-sharing   "team" or "solo" — the answer to the one setup question (team_skills.py question)
  team-skills    the team folder path (only meaningful when team-sharing is "team")

Usage as a library:
    sys.path.insert(0, "<plugin>/shared"); import team_skills_root
    source, path = team_skills_root.resolve_team_skills_root()   # ("pointer", p) | ("pointer-missing", p) | (None, None)
    mode = team_skills_root.sharing_mode()                       # "team" | "solo" | None
Usage as a CLI:
    python3 shared/team_skills_root.py --shell
      TEAM=<path or empty>  TEAM_STATUS=ok|unset|missing  SHARING=team|solo|unset
"""
import argparse
import os
import sys

POINTER_NAME = "team-skills"
MODE_NAME = "team-sharing"


def _config_home():
    """~/.config/lifehack, computed at call time (so a test can swap HOME)."""
    return os.path.join(os.path.expanduser("~"), ".config", "lifehack")


def pointer_path():
    return os.path.join(_config_home(), POINTER_NAME)


def mode_path():
    return os.path.join(_config_home(), MODE_NAME)


def read_pointer():
    """The raw one-line value in the pointer file, or None (absent, unreadable, or blank)."""
    fp = pointer_path()
    if not os.path.isfile(fp):
        return None
    try:
        with open(fp, encoding="utf-8") as f:
            value = (f.read().splitlines() or [""])[0].strip()
    except OSError:
        return None
    return os.path.expanduser(value) if value else None


def resolve_team_skills_root():
    """(source, path): ("pointer", path) when the pointer names a real directory;
    ("pointer-missing", path) when it names one that is not there; (None, None) when nothing
    names a folder at all. Never guesses, never falls back, never uses the cwd."""
    pointer = read_pointer()
    if pointer:
        if os.path.isdir(pointer):
            return "pointer", pointer
        return "pointer-missing", pointer
    return None, None


def team_status():
    """ok | unset | missing — the closed outcome set person_roots.py uses for every root."""
    source, _ = resolve_team_skills_root()
    if source == "pointer":
        return "ok"
    if source == "pointer-missing":
        return "missing"
    return "unset"


def sharing_mode():
    """"team" | "solo" | None. Anything else in the file is None (asked again, never guessed)."""
    fp = mode_path()
    if not os.path.isfile(fp):
        return None
    try:
        with open(fp, encoding="utf-8") as f:
            value = (f.read().splitlines() or [""])[0].strip().lower()
    except OSError:
        return None
    return value if value in ("team", "solo") else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="resolve the team shared-skills folder")
    ap.add_argument("--shell", action="store_true", help="one line per fact, for shell hooks")
    a = ap.parse_args(argv)
    source, path = resolve_team_skills_root()
    team = path if source == "pointer" else ""
    mode = sharing_mode()
    if not a.shell:
        if source == "pointer-missing":
            print("POINTER-MISSING: %s names\n %s\nbut that folder is not there. Nothing was "
                  "switched to any other folder, on purpose." % (pointer_path(), path))
            return 1
        if source is None:
            print("NOT-SET: no %s. The person has not picked a team folder (or works solo: "
                  "team-sharing says so). Run team_skills.py question, then team_skills.py set." % pointer_path())
            return 1
        print("RESOLVED: %s (source: %s)" % (path, source))
        return 0
    print("TEAM=" + team)
    print("TEAM_STATUS=" + team_status())
    print("SHARING=" + (mode or "unset"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
